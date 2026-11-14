"""Evaluation for retrieval, contract rules and legal Q&A.

Usage:
    python scripts/evaluate.py
"""

from __future__ import annotations

import json
import statistics
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.db import LawRepository  # noqa: E402
from app.llm.client import LLMClient  # noqa: E402
from app.rag.retriever import LawRetriever  # noqa: E402
from app.schemas import QARequest  # noqa: E402
from app.services.qa import QAService  # noqa: E402
from app.tools.contract_parser import parse_contract  # noqa: E402
from app.tools.risk_rules import scan_contract  # noqa: E402


def evaluate_retrieval(
    retriever: LawRetriever, questions: list[dict], expand: bool = True
) -> tuple[float, float]:
    hits = 0
    reciprocal_ranks: list[float] = []
    for item in questions:
        results = [
            result.article.id
            for result in retriever.search(item["question"], top_k=3, expand=expand)
        ]
        expected = item["expected_articles"]
        if any(article_id in results for article_id in expected):
            hits += 1
        rank = next(
            (index + 1 for index, article_id in enumerate(results) if article_id in expected),
            None,
        )
        reciprocal_ranks.append(1 / rank if rank else 0.0)
    return hits / len(questions), sum(reciprocal_ranks) / len(reciprocal_ranks)


def evaluate_rules(contract_labels: list[dict]) -> tuple[float, float, int]:
    true_positive = false_positive = false_negative = 0
    for item in contract_labels:
        text = (ROOT / "data" / "contracts" / item["contract"]).read_text(encoding="utf-8")
        parsed = parse_contract(text)
        actual = {finding.rule_id for finding in scan_contract(parsed, item["contract_type"])}
        expected = set(item["expected_rules"])
        true_positive += len(actual & expected)
        false_positive += len(actual - expected)
        false_negative += len(expected - actual)
    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, true_positive + false_negative)
    return precision, recall, false_positive


def evaluate_qa(questions: list[dict]) -> tuple[float, float, float, float]:
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(llm_api_key="", database_path=Path(tmp) / "eval.db")
        service = QAService(
            repository=LawRepository(settings.database_path), llm=LLMClient(settings)
        )
        intent_hits = 0
        citation_hits = 0
        amount_hits = 0
        amount_total = 0
        latencies: list[float] = []

        for item in questions:
            started = time.perf_counter()
            record = service.ask(QARequest(question=item["question"]))
            latencies.append((time.perf_counter() - started) * 1000)
            if record.intent == item["intent"]:
                intent_hits += 1
            top_citations = {citation.article_id for citation in record.citations[:3]}
            if top_citations & set(item["expected_articles"]):
                citation_hits += 1
            if "expected_amount" in item:
                amount_total += 1
                if (
                    record.calculation
                    and abs(record.calculation.amount - item["expected_amount"]) < 1
                ):
                    amount_hits += 1

        return (
            intent_hits / len(questions),
            citation_hits / len(questions),
            amount_hits / max(1, amount_total),
            statistics.mean(latencies),
        )


def main() -> None:
    questions = json.loads(
        (ROOT / "data" / "qa" / "eval_questions.json").read_text(encoding="utf-8")
    )
    contract_labels = json.loads(
        (ROOT / "data" / "fixtures" / "review_labels.json").read_text(encoding="utf-8")
    )

    retriever = LawRetriever()
    baseline_recall, baseline_mrr = evaluate_retrieval(retriever, questions, expand=False)
    recall_at_3, mrr = evaluate_retrieval(retriever, questions, expand=True)
    rule_precision, rule_recall, false_positives = evaluate_rules(contract_labels)
    intent_accuracy, citation_recall, amount_accuracy, qa_latency = evaluate_qa(questions)

    lines = [
        "# 离线评估报告",
        "",
        f"生成日期：{date.today().isoformat()}  ",
        "运行模式：离线规则 + BM25（不调用外部 LLM）  ",
        f"法条库：{retriever.count} 条",
        "",
        "## 法条检索",
        "",
        "| 策略 | Recall@3 | MRR |",
        "|---|---:|---:|",
        f"| 纯 BM25 | {baseline_recall:.0%} | {baseline_mrr:.3f} |",
        f"| BM25 + 同义扩展 | **{recall_at_3:.0%}** | **{mrr:.3f}** |",
        "",
        "## 合同风险规则",
        "",
        "| 指标 | 结果 |",
        "|---|---:|",
        f"| Precision | **{rule_precision:.0%}** |",
        f"| Recall | **{rule_recall:.0%}** |",
        f"| False positives | **{false_positives}** |",
        "",
        "## 法律问答",
        "",
        "| 指标 | 结果 |",
        "|---|---:|",
        f"| 意图准确率 | **{intent_accuracy:.0%}** |",
        f"| 法条引用 Recall@3 | **{citation_recall:.0%}** |",
        f"| 金额计算准确率 | **{amount_accuracy:.0%}** |",
        f"| 平均单题耗时 | **{qa_latency:.0f} ms** |",
        "",
        "> 评估集为 15 个合成问题与 3 份合成合同，标签按法条与规则人工标注，用于检查检索和规则量级，不构成法律意见；指标不代表真实案件泛化能力。",
    ]
    report = "\n".join(lines) + "\n"
    output = ROOT / "reports" / "evaluation.md"
    output.parent.mkdir(exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(report)
    print(f"written to {output}")


if __name__ == "__main__":
    main()
