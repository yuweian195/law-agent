"""LangGraph nodes for legal Q&A."""

from __future__ import annotations

import time

from app.db import get_repository
from app.graph.qa_state import QAState
from app.llm.client import get_llm_client
from app.rag.retriever import get_retriever
from app.schemas import CompensationResult, LegalCitation
from app.tools.compensation import calculate_compensation
from app.tools.legal_answer import DISCLAIMER, INTENT_LABEL, build_answer
from app.tools.question_parser import QuestionFacts, extract_facts


def _step(node: str, label: str, started: float, summary: str) -> dict:
    return {
        "node": node,
        "label": label,
        "status": "ok",
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "summary": summary,
    }


def analyze_question_node(state: QAState) -> dict:
    started = time.perf_counter()
    facts = extract_facts(state["question"], state.get("context", ""))
    label = INTENT_LABEL.get(facts.intent, facts.intent)
    return {
        "intent": facts.intent,
        "facts": facts.__dict__,
        "trace": [_step("analyze_question", "识别意图与事实", started, f"意图：{label}")],
    }


def retrieve_laws_node(state: QAState) -> dict:
    started = time.perf_counter()
    query = state["question"]
    if state.get("context"):
        query += "\n" + state["context"]
    results = get_retriever().search(query, top_k=5)
    citations = [
        LegalCitation(
            article_id=item.article.id,
            law=item.article.law,
            article=item.article.article,
            title=item.article.title,
            text=item.article.text,
            score=item.score,
        ).model_dump()
        for item in results
    ]
    summary = f"检索到 {len(citations)} 条法条"
    if citations:
        summary += f"，首条为《{citations[0]['law']}》{citations[0]['article']}"
    return {"citations": citations, "trace": [_step("retrieve_laws", "检索法条", started, summary)]}


def calculate_node(state: QAState) -> dict:
    started = time.perf_counter()
    facts = QuestionFacts(**state["facts"])
    result = calculate_compensation(facts)
    if result is None:
        summary = "当前问题不涉及金额计算或缺少必要事实"
        return {"calculation": None, "trace": [_step("calculate", "金额计算", started, summary)]}
    summary = f"{result.formula}；金额 {result.amount:,.0f} 元"
    return {
        "calculation": result.model_dump(),
        "trace": [_step("calculate", "金额计算", started, summary)],
    }


def compose_answer_node(state: QAState) -> dict:
    started = time.perf_counter()
    facts = QuestionFacts(**state["facts"])
    citations = [LegalCitation(**item) for item in state["citations"]]
    calculation = (
        CompensationResult(**state["calculation"]) if state.get("calculation") else None
    )
    conclusion, analysis = build_answer(state["question"], facts, calculation, citations)

    llm = get_llm_client()
    if llm.enabled and citations:
        enriched = llm.compose_answer(state["question"], state["intent"], citations, calculation)
        if enriched:
            conclusion = enriched["conclusion"]
            analysis = enriched.get("analysis") or analysis

    return {
        "conclusion": conclusion,
        "analysis": analysis,
        "disclaimer": DISCLAIMER,
        "trace": [
            _step(
                "compose_answer",
                "生成回答",
                started,
                f"引用 {len(citations)} 条法条，结论长度 {len(conclusion)} 字",
            )
        ],
    }


def save_qa_node(state: QAState) -> dict:
    started = time.perf_counter()
    step = _step("save_record", "保存问答", started, "问答记录已写入 SQLite")
    trace = list(state.get("trace", [])) + [step]
    payload = {
        "id": state["qa_id"],
        "question": state["question"],
        "intent": state["intent"],
        "conclusion": state["conclusion"],
        "analysis": state["analysis"],
        "calculation": state.get("calculation"),
        "citations": state["citations"],
        "disclaimer": state["disclaimer"],
        "trace": trace,
        "llm_mode": state.get("llm_mode", "offline"),
        "created_at": state["created_at"],
    }
    repository = state.get("repository") or get_repository()
    repository.save_qa(
        {
            "id": payload["id"],
            "question": payload["question"],
            "intent": payload["intent"],
            "citations_count": len(payload["citations"]),
            "created_at": payload["created_at"],
            "payload": payload,
        }
    )
    return {"trace": [step]}
