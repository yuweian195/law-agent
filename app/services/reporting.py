"""Markdown report rendering for reviews and legal Q&A."""

from __future__ import annotations

from app.schemas import ContractReview, QARecord

_RISK_LABEL = {"high": "高", "medium": "中", "low": "低"}
_INTENT_LABEL = {
    "severance": "解除与补偿",
    "probation": "试用期",
    "non_compete": "竞业限制",
    "service_period": "服务期",
    "social_insurance": "社会保险",
    "overtime": "加班工资",
    "contract_penalty": "违约金",
    "general": "一般咨询",
}


def review_markdown(review: ContractReview) -> str:
    lines = [
        f"# 合同审查报告：{review.contract_title}",
        "",
        f"- 合同类型：{review.contract_type}",
        f"- 整体风险：**{_RISK_LABEL.get(review.overall_risk.value, review.overall_risk.value)}**",
        f"- 风险评分：**{review.risk_score:.0f}/100**",
        f"- 风险数量：{len(review.findings)}",
        f"- 审查编号：{review.id}",
        "",
        "## 总体结论",
        "",
        review.summary,
        "",
        "## 风险清单",
        "",
        "| # | 条款 | 风险 | 问题 | 修改建议 |",
        "|---:|---|---|---|---|",
    ]
    for index, finding in enumerate(review.findings, start=1):
        lines.append(
            f"| {index} | {finding.clause_title} | "
            f"{_RISK_LABEL.get(finding.risk_level.value, finding.risk_level.value)} | "
            f"{finding.issue} | {finding.suggestion} |"
        )
    if not review.findings:
        lines.append("| - | - | 低 | 未发现明显高风险条款 | 建议人工复核 |")

    basis: dict[str, str] = {}
    for finding in review.findings:
        for item in finding.legal_basis:
            basis[item.article_id] = (
                f"《{item.law}》{item.article}（{item.title}）：{item.text}"
            )
    if basis:
        lines += ["", "## 法条依据", ""]
        for text in basis.values():
            lines.append(f"- {text}")

    lines += [
        "",
        "> 本报告由规则与本地法条库生成，不构成正式法律意见；签署前建议由执业律师复核。",
    ]
    return "\n".join(lines) + "\n"


def qa_markdown(record: QARecord) -> str:
    lines = [
        "# 法律咨询记录",
        "",
        f"- 问题：{record.question}",
        f"- 意图：{_INTENT_LABEL.get(record.intent, record.intent)}",
        f"- 记录编号：{record.id}",
        "",
        "## 结论",
        "",
        record.conclusion,
        "",
        "## 分析",
        "",
        record.analysis,
    ]
    if record.calculation and record.calculation.applies:
        lines += [
            "",
            "## 计算明细",
            "",
            f"- 公式：{record.calculation.formula}",
            f"- 金额：**{record.calculation.amount:,.0f} 元**",
        ]
        lines += [f"- {item}" for item in record.calculation.breakdown]
        lines += ["", "假设："] + [f"- {item}" for item in record.calculation.assumptions]

    if record.citations:
        lines += ["", "## 法条依据", ""]
        for citation in record.citations:
            lines.append(
                f"- 《{citation.law}》{citation.article}（{citation.title}）：{citation.text}"
            )

    lines += ["", "---", "", record.disclaimer]
    return "\n".join(lines) + "\n"
