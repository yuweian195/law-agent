"""LangGraph nodes for contract review."""

from __future__ import annotations

import time

from app.db import get_repository
from app.graph.review_state import ReviewState
from app.llm.client import get_llm_client
from app.rag.retriever import get_retriever
from app.schemas import ContractClause, ParsedContract, RiskLevel
from app.tools.contract_parser import parse_contract
from app.tools.risk_rules import overall_risk, risk_score, scan_contract


def _step(node: str, label: str, started: float, summary: str) -> dict:
    return {
        "node": node,
        "label": label,
        "status": "ok",
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "summary": summary,
    }


def parse_contract_node(state: ReviewState) -> dict:
    started = time.perf_counter()
    parsed = parse_contract(state["contract_text"])
    if not parsed.clauses:
        parsed.clauses = [ContractClause(index=1, title="合同全文", text=state["contract_text"])]
    summary = f"识别《{parsed.title}》，拆分 {len(parsed.clauses)} 个条款"
    return {
        "parsed_contract": parsed.model_dump(),
        "trace": [_step("parse_contract", "解析合同", started, summary)],
    }


def scan_rules_node(state: ReviewState) -> dict:
    started = time.perf_counter()
    parsed = ParsedContract(**state["parsed_contract"])
    findings = scan_contract(parsed, state.get("contract_type", "labor"))
    high = sum(1 for item in findings if item.risk_level == RiskLevel.HIGH)
    medium = sum(1 for item in findings if item.risk_level == RiskLevel.MEDIUM)
    summary = f"命中 {len(findings)} 项风险（高 {high} / 中 {medium}）"
    return {
        "findings": [item.model_dump() for item in findings],
        "trace": [_step("scan_rules", "规则扫描", started, summary)],
    }


def retrieve_context_node(state: ReviewState) -> dict:
    started = time.perf_counter()
    retriever = get_retriever()
    verified: list[dict] = []
    checked = 0
    for finding in state["findings"]:
        item = dict(finding)
        basis = []
        seen: set[str] = set()
        for entry in item.get("legal_basis", []):
            if entry["article_id"] in seen:
                continue
            seen.add(entry["article_id"])
            if retriever.get(entry["article_id"]) is None:
                continue
            basis.append(entry)
            checked += 1
        item["legal_basis"] = basis
        verified.append(item)
    summary = f"校验 {checked} 条法条依据，去重后附入审查意见"
    return {
        "findings": verified,
        "trace": [_step("verify_context", "校验法条依据", started, summary)],
    }


def assess_node(state: ReviewState) -> dict:
    started = time.perf_counter()
    from app.schemas import RiskFinding

    findings = [RiskFinding(**item) for item in state["findings"]]
    level = overall_risk(findings)
    score = risk_score(findings)
    level_label = {"high": "高", "medium": "中", "low": "低"}.get(level.value, level.value)

    summary = ""
    llm = get_llm_client()
    if llm.enabled:
        parsed = ParsedContract(**state["parsed_contract"])
        summary = (
            llm.summarize_contract(
                state.get("title") or parsed.title,
                findings,
                level_label,
                score,
            )
            or ""
        )
    if not summary:
        if not findings:
            summary = "未发现明显高风险条款，建议结合业务背景与履行能力进行人工复核。"
        else:
            top = sorted(
                findings,
                key=lambda item: (item.risk_level == RiskLevel.HIGH, item.clause_index),
                reverse=True,
            )[:2]
            priority = "；".join(f"{item.clause_title}：{item.issue}" for item in top)
            summary = (
                f"合同整体风险为{level_label}，共发现 {len(findings)} 项风险，"
                f"风险评分 {score:.0f}/100。优先处理：{priority}"
            )

    return {
        "overall_risk": level.value,
        "risk_score": score,
        "summary": summary,
        "trace": [
            _step("assess", "汇总风险", started, f"整体 {level.value}，评分 {score:.0f}/100")
        ],
    }


def save_review_node(state: ReviewState) -> dict:
    started = time.perf_counter()
    step = _step("save_review", "保存审查报告", started, "审查报告已写入 SQLite")
    trace = list(state.get("trace", [])) + [step]
    parsed = ParsedContract(**state["parsed_contract"])
    payload = {
        "id": state["review_id"],
        "contract_title": state.get("title") or parsed.title,
        "contract_type": state.get("contract_type", "labor"),
        "overall_risk": state["overall_risk"],
        "risk_score": state["risk_score"],
        "findings": state["findings"],
        "clauses": [item.model_dump() for item in parsed.clauses],
        "summary": state["summary"],
        "trace": trace,
        "llm_mode": state.get("llm_mode", "offline"),
        "created_at": state["created_at"],
    }
    repository = state.get("repository") or get_repository()
    repository.save_review(
        {
            "id": payload["id"],
            "contract_title": payload["contract_title"],
            "contract_type": payload["contract_type"],
            "overall_risk": payload["overall_risk"],
            "risk_score": payload["risk_score"],
            "findings_count": len(payload["findings"]),
            "created_at": payload["created_at"],
            "payload": payload,
        }
    )
    return {"trace": [step]}
