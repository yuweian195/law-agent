"""Seed demo contract reviews and legal Q&A records.

Usage:
    python scripts/seed_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.schemas import ContractReviewRequest, QARequest  # noqa: E402
from app.services.qa import get_qa_service  # noqa: E402
from app.services.review import get_review_service  # noqa: E402

CONTRACTS = [
    ("labor_contract_risky.txt", "labor"),
    ("service_contract.txt", "service"),
    ("labor_contract_clean.txt", "labor"),
]
QUESTIONS = [
    "公司违法解除劳动合同，我工作3年2个月，月薪2万，能拿多少赔偿？",
    "试用期6个月合法吗？合同期1年",
    "竞业限制没有约定补偿金，还有效吗？",
]


def main() -> None:
    review_service = get_review_service()
    for filename, contract_type in CONTRACTS:
        text = (ROOT / "data" / "contracts" / filename).read_text(encoding="utf-8")
        review = review_service.review(
            ContractReviewRequest(contract_text=text, contract_type=contract_type)
        )
        print(
            f"{review.contract_title:<10} {review.overall_risk.value:<7} "
            f"{review.risk_score:5.0f}/100  {len(review.findings)} 项风险"
        )

    qa_service = get_qa_service()
    for question in QUESTIONS:
        record = qa_service.ask(QARequest(question=question))
        print(f"QA {record.intent:<16} {len(record.citations)} 条引用")

    print(
        f"\n已写入 {len(review_service.list_recent(50))} 份审查、"
        f"{len(qa_service.list_recent(50))} 条问答"
    )


if __name__ == "__main__":
    main()
