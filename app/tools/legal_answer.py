"""Template-based legal answer composition with mandatory citations."""

from __future__ import annotations

import re

from app.schemas import CompensationResult, LegalCitation
from app.tools.question_parser import QuestionFacts

DISCLAIMER = (
    "以上分析基于你提供的信息和本地法条节选，不构成正式法律意见。"
    "具体案件请咨询执业律师，并以劳动仲裁或法院的认定为准。"
)

INTENT_LABEL = {
    "severance": "解除劳动合同与补偿",
    "probation": "试用期",
    "non_compete": "竞业限制",
    "service_period": "服务期与违约金",
    "social_insurance": "社会保险",
    "overtime": "加班工资",
    "contract_penalty": "合同违约金",
    "general": "一般法律咨询",
}


def citation_label(citation: LegalCitation) -> str:
    return f"《{citation.law}》{citation.article}（{citation.title}）"


def _has_evidence(citations: list[LegalCitation]) -> bool:
    return bool(citations) and any(
        citation.score >= 0.35 and citation.text for citation in citations[:3]
    )


def _probation_conclusion(question: str) -> str:
    term = re.search(r"合同期(?:限)?\s*(\d+)\s*年", question)
    probation = re.search(r"试用期\s*(\d+)\s*个月", question)
    if term and probation:
        years = int(term.group(1))
        months = int(probation.group(1))
        maximum = 6 if years >= 3 else 2 if years >= 1 else 1
        if months > maximum:
            return (
                f"合同期限 {years} 年，依法试用期不得超过 {maximum} 个月；"
                f"约定 {months} 个月试用期不合法，超出部分应按正常工资标准支付。"
            )
        return f"合同期限 {years} 年，约定 {months} 个月试用期未超过法定上限 {maximum} 个月。"
    return "试用期期限需结合劳动合同期限判断：合同期不满一年最长 1 个月，一年以上不满三年最长 2 个月，三年以上最长 6 个月。"


def build_answer(
    question: str,
    facts: QuestionFacts,
    calculation: CompensationResult | None,
    citations: list[LegalCitation],
) -> tuple[str, str]:
    intent = facts.intent
    labels = "、".join(citation_label(item) for item in citations[:3])

    if not _has_evidence(citations):
        return (
            "现有法条检索结果不足以支持明确结论，建议补充事实或咨询执业律师。",
            "本地知识库未检索到与问题高度相关的法条。你可以补充劳动合同期限、工资、解除原因、"
            "竞业限制约定等事实后重新提问。",
        )

    if intent == "severance":
        if calculation and calculation.applies:
            conclusion = (
                f"按你描述的情形测算，金额约为 {calculation.amount:,.0f} 元。"
                f"计算方式：{calculation.formula}。"
            )
            analysis = (
                "；".join(calculation.breakdown)
                + "。上述金额为估算值，未考虑当地社平工资三倍封顶、十二年上限、"
                "未休年假、加班费及未签书面合同二倍工资等其他请求。"
                f"主要依据：{labels}。"
            )
        else:
            conclusion = (
                "要判断是否能获得赔偿以及金额，需要补充工作年限、月工资和解除方式。"
            )
            analysis = (
                "经济补偿通常按工作年限计算：每满一年支付一个月工资，六个月以上不满一年按一年计算，"
                "不满六个月支付半个月工资；违法解除的赔偿金为经济补偿标准的二倍。"
                f"主要依据：{labels}。"
            )
    elif intent == "probation":
        conclusion = _probation_conclusion(question)
        analysis = (
            "试用期工资不得低于本单位相同岗位最低档工资或者劳动合同约定工资的 80%，"
            "并不得低于用人单位所在地最低工资标准；同一用人单位与同一劳动者只能约定一次试用期。"
            f"主要依据：{labels}。"
        )
    elif intent == "non_compete":
        conclusion = (
            "竞业限制可以约定，但用人单位应在竞业限制期限内按月支付经济补偿；"
            "期限最长不得超过二年，且适用人员限于高级管理人员、高级技术人员和其他负有保密义务的人员。"
        )
        analysis = (
            "未约定补偿并不当然导致条款无效，但劳动者履行竞业限制义务后可以主张相应补偿；"
            "用人单位长期不支付补偿的，劳动者可依法主张解除竞业限制约定。"
            f"主要依据：{labels}。"
        )
    elif intent == "service_period":
        conclusion = (
            "服务期违约金只有在用人单位提供专项培训费用、进行专业技术培训时才具有依据，"
            "且违约金不得超过培训费用。"
        )
        analysis = (
            "如果公司无法提供专项培训费用凭证，服务期违约金条款可能缺乏依据；"
            "即使有效，违约金也不得超过服务期尚未履行部分所应分摊的培训费用。"
            f"主要依据：{labels}。"
        )
    elif intent == "social_insurance":
        conclusion = (
            "用人单位应当自用工之日起三十日内为职工办理社会保险登记并依法缴纳。"
            "不缴社保的，劳动者可以要求补缴，并可能据此解除劳动合同、主张经济补偿。"
        )
        analysis = (
            "社保缴纳属于强制性义务，员工自愿放弃社保的承诺通常无效。"
            "以未依法缴纳社保为由解除劳动合同的，用人单位应支付经济补偿。"
            f"主要依据：{labels}。"
        )
    elif intent == "overtime":
        conclusion = (
            "加班工资按以下标准支付：工作日延长工作时间不低于 150%，"
            "休息日不能补休不低于 200%，法定休假日不低于 300%。"
        )
        analysis = (
            "计算基数通常按劳动合同约定工资或正常工作时间工资确定；"
            "用人单位不得以“加班费已包含在工资中”为由拒付法定加班工资。"
            f"主要依据：{labels}。"
        )
    elif intent == "contract_penalty":
        conclusion = (
            "约定的违约金过分高于实际损失的，法院或仲裁机构可以根据当事人请求适当减少；"
            "低于实际损失的，也可以请求增加。"
        )
        analysis = (
            "判断是否“过分高于”通常结合实际损失、合同履行情况、当事人过错程度等因素；"
            "50% 的违约金比例存在被调整的可能，但并非当然无效。"
            f"主要依据：{labels}。"
        )
    else:
        conclusion = "根据检索到的法条，建议结合具体事实进一步判断，并保留合同、工资流水、沟通记录等证据。"
        analysis = f"相关法条：{labels}。如能补充合同期限、工资、解除原因等事实，我可以给出更具体的分析。"

    return conclusion, analysis
