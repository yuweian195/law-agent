"""Deterministic contract risk rules with statutory citations."""

from __future__ import annotations

import re

from app.schemas import (
    ContractClause,
    LegalArticle,
    LegalBasis,
    ParsedContract,
    RiskFinding,
    RiskLevel,
)

_RISK_PENALTY = {RiskLevel.HIGH: 30.0, RiskLevel.MEDIUM: 10.0, RiskLevel.LOW: 0.0}


def _parse_number(value: str, unit: str | None) -> float:
    number = float(value)
    if unit == "万":
        return number * 10000
    if unit in ("k", "K"):
        return number * 1000
    return number


def _contract_term_months(text: str) -> int:
    match = re.search(r"合同期限[^。；\n]{0,30}?(\d+)\s*年", text)
    if not match:
        match = re.search(r"期限(?:为|：|:)?\s*(\d+)\s*年", text)
    if match:
        return int(match.group(1)) * 12
    if re.search(r"无固定期限", text):
        return 0
    return 0


def _probation_months(text: str) -> int:
    match = re.search(r"试用期(?:为|：|:)?\s*(\d+)\s*个月", text)
    return int(match.group(1)) if match else 0


def _probation_ratio(text: str) -> float | None:
    percent = re.search(r"试用期工资[^。；\n]{0,30}?(\d+(?:\.\d+)?)\s*%", text)
    if percent:
        return float(percent.group(1)) / 100
    amount = re.search(
        r"试用期工资[^。；\n]{0,20}?(\d+(?:\.\d+)?)\s*(万|元|k|K)", text
    )
    salary = re.search(r"(?:月工资|月薪|工资)[^。；\n]{0,15}?(\d+(?:\.\d+)?)\s*(万|元|k|K)", text)
    if amount and salary:
        return _parse_number(amount.group(1), amount.group(2)) / max(
            1.0, _parse_number(salary.group(1), salary.group(2))
        )
    return None


def _penalty_percent(text: str) -> float | None:
    match = re.search(r"违约金[^。；\n]{0,30}?(\d+(?:\.\d+)?)\s*%", text)
    if not match:
        match = re.search(r"(\d+(?:\.\d+)?)\s*%[^。；\n]{0,20}?违约金", text)
    return float(match.group(1)) if match else None


def _non_compete_years(text: str) -> int | None:
    match = re.search(r"竞业限制[^。；\n]{0,40}?(\d+)\s*年", text)
    return int(match.group(1)) if match else None


def _legal_basis(article_ids: list[str]) -> list[LegalBasis]:
    from app.rag.retriever import get_retriever

    retriever = get_retriever()
    basis: list[LegalBasis] = []
    for article_id in article_ids:
        article = retriever.get(article_id)
        if article:
            basis.append(_to_basis(article))
    return basis


def _to_basis(article: LegalArticle) -> LegalBasis:
    return LegalBasis(
        article_id=article.id,
        law=article.law,
        article=article.article,
        title=article.title,
        text=article.text,
    )


def _finding(
    rule_id: str,
    clause: ContractClause,
    level: RiskLevel,
    issue: str,
    suggestion: str,
    matched_text: str,
    article_ids: list[str],
) -> RiskFinding:
    return RiskFinding(
        rule_id=rule_id,
        clause_index=clause.index,
        clause_title=clause.title,
        risk_level=level,
        issue=issue,
        suggestion=suggestion,
        matched_text=matched_text,
        legal_basis=_legal_basis(article_ids),
    )


def _check_probation_limit(
    contract_text: str, clause: ContractClause
) -> RiskFinding | None:
    probation = _probation_months(clause.text)
    if not probation:
        return None
    term = _contract_term_months(contract_text)
    if term <= 0:
        return None
    if term < 3:
        maximum = 0
    elif term < 12:
        maximum = 1
    elif term < 36:
        maximum = 2
    else:
        maximum = 6
    if probation <= maximum:
        return None
    return _finding(
        "probation_limit",
        clause,
        RiskLevel.HIGH,
        f"合同期限 {term} 个月，约定试用期 {probation} 个月，超过法定上限 {maximum} 个月。",
        f"将试用期调整为不超过 {maximum} 个月，或延长合同期限；同一用人单位只能约定一次试用期。",
        f"试用期 {probation} 个月",
        ["labor-19"],
    )


def _check_probation_salary(clause: ContractClause) -> RiskFinding | None:
    if "试用期" not in clause.text:
        return None
    ratio = _probation_ratio(clause.text)
    if ratio is None or ratio >= 0.8:
        return None
    return _finding(
        "probation_salary",
        clause,
        RiskLevel.HIGH,
        f"试用期工资约为约定工资的 {ratio:.0%}，低于法定 80% 下限。",
        "将试用期工资调整至不低于本单位同岗位最低档工资或劳动合同约定工资的 80%，且不低于当地最低工资。",
        f"试用期工资比例 {ratio:.0%}",
        ["labor-20"],
    )


def _check_service_period(clause: ContractClause) -> RiskFinding | None:
    if "服务期" not in clause.text or "违约金" not in clause.text:
        return None
    if any(word in clause.text for word in ("培训费用", "培训费", "费用凭证", "培训支出")):
        return None
    return _finding(
        "service_period_penalty",
        clause,
        RiskLevel.HIGH,
        "约定服务期违约金，但未说明专项培训费用依据。",
        "补充专项培训费用凭证与培训协议；违约金不得超过培训费用，且不得超过服务期尚未履行部分分摊的培训费用。",
        "服务期违约金",
        ["labor-22"],
    )


def _check_non_compete(clause: ContractClause) -> list[RiskFinding]:
    if "竞业限制" not in clause.text:
        return []
    findings: list[RiskFinding] = []
    negatives = (
        "无需支付经济补偿",
        "不支付经济补偿",
        "没有经济补偿",
        "无经济补偿",
        "不给予补偿",
        "无需补偿",
    )
    positives = ("经济补偿", "补偿金", "按月支付", "按月给予")
    has_compensation = any(word in clause.text for word in positives) and not any(
        word in clause.text for word in negatives
    )
    if not has_compensation:
        findings.append(
            _finding(
                "non_compete_compensation",
                clause,
                RiskLevel.HIGH,
                "约定竞业限制但未约定解除或终止后的按月经济补偿。",
                "明确竞业限制期限、地域、范围，并约定按月支付经济补偿；未支付补偿可能影响条款效力。",
                "竞业限制无补偿",
                ["labor-23"],
            )
        )
    years = _non_compete_years(clause.text)
    if years and years > 2:
        findings.append(
            _finding(
                "non_compete_term",
                clause,
                RiskLevel.HIGH,
                f"竞业限制期限 {years} 年，超过法定最长 2 年。",
                "将竞业限制期限调整为不超过 2 年，并明确适用人员范围。",
                f"竞业限制 {years} 年",
                ["labor-24"],
            )
        )
    return findings


def _check_liquidated_damages(clause: ContractClause) -> RiskFinding | None:
    if "违约金" not in clause.text or "服务期" in clause.text:
        return None
    percent = _penalty_percent(clause.text)
    if percent is None or percent < 30:
        return None
    return _finding(
        "liquidated_damages",
        clause,
        RiskLevel.MEDIUM,
        f"约定违约金为合同金额的 {percent:.0f}%，可能被认定为过分高于实际损失。",
        "将违约金与实际损失挂钩，或约定损失赔偿计算方法；过高时可请求法院或仲裁机构适当减少。",
        f"违约金 {percent:.0f}%",
        ["civil-585"],
    )


def _check_unilateral_termination(clause: ContractClause) -> RiskFinding | None:
    has_termination = any(word in clause.text for word in ("随时解除", "随时辞退", "单方解除"))
    has_no_compensation = any(
        word in clause.text
        for word in ("无须支付", "无需支付", "不支付经济补偿", "不承担任何责任")
    ) and any(word in clause.text for word in ("解除", "辞退"))
    if not (has_termination or has_no_compensation):
        return None
    matched = next(
        word
        for word in ("随时解除", "随时辞退", "单方解除", "无须支付", "无需支付", "不支付经济补偿", "不承担任何责任")
        if word in clause.text
    )
    return _finding(
        "unilateral_termination",
        clause,
        RiskLevel.HIGH,
        "约定用人单位可随时解除且不承担补偿责任，排除劳动者法定权利。",
        "删除无条件解除条款，按劳动合同法第 39、40、41 条规定明确解除情形与程序，并依法支付经济补偿或赔偿金。",
        matched,
        ["labor-48", "labor-87"],
    )


def _check_social_insurance(clause: ContractClause) -> RiskFinding | None:
    triggers = ("不缴纳社会保险", "不交社保", "员工自行缴纳", "社保由员工承担", "放弃社保", "放弃社会保险")
    if not any(trigger in clause.text for trigger in triggers):
        return None
    return _finding(
        "social_insurance",
        clause,
        RiskLevel.HIGH,
        "约定不缴纳社保或由员工自行承担，违反社会保险强制性规定。",
        "自用工之日起 30 日内为员工办理社保登记并依法缴纳；员工放弃社保的承诺通常无效。",
        next(trigger for trigger in triggers if trigger in clause.text),
        ["social-58", "labor-38"],
    )


def _check_overtime_pay(clause: ContractClause) -> RiskFinding | None:
    triggers = ("加班费已包含", "不再支付加班费", "无加班费", "自愿加班")
    if not any(trigger in clause.text for trigger in triggers):
        return None
    return _finding(
        "overtime_pay",
        clause,
        RiskLevel.HIGH,
        "约定加班费已包含在工资中或不支付加班费，可能违反加班工资规定。",
        "按工作日 150%、休息日 200%、法定休假日 300% 的标准支付加班费，或在工资结构中明确拆分。",
        next(trigger for trigger in triggers if trigger in clause.text),
        ["labor-law-44", "labor-31"],
    )


def _check_unilateral_change(clause: ContractClause) -> RiskFinding | None:
    triggers = ("单方调整", "单方变更", "有权调整岗位", "有权变更岗位", "调岗调薪")
    if not any(trigger in clause.text for trigger in triggers):
        return None
    if "协商一致" in clause.text:
        return None
    return _finding(
        "unilateral_change",
        clause,
        RiskLevel.MEDIUM,
        "约定用人单位可单方调整岗位或薪资，未体现协商一致。",
        "岗位、工作地点、薪酬变更应与劳动者协商一致并采用书面形式；明确调整的合理边界。",
        next(trigger for trigger in triggers if trigger in clause.text),
        ["labor-35"],
    )


def _check_final_interpretation(clause: ContractClause) -> RiskFinding | None:
    if "最终解释权" not in clause.text:
        return None
    return _finding(
        "final_interpretation",
        clause,
        RiskLevel.MEDIUM,
        "约定公司享有最终解释权，属于不合理免除自身责任、限制对方权利的格式条款。",
        "删除最终解释权条款；对格式条款履行提示说明义务，争议按法律规定处理。",
        "最终解释权",
        ["civil-496", "civil-497"],
    )


def _check_auto_renewal(clause: ContractClause) -> RiskFinding | None:
    if not any(trigger in clause.text for trigger in ("自动续约", "自动续期")):
        return None
    return _finding(
        "auto_renewal",
        clause,
        RiskLevel.MEDIUM,
        "约定自动续约/续期，未明确续期条件与退出机制。",
        "明确续期期限、通知方式和一方不续期的权利，避免无限期自动续约。",
        "自动续约",
        ["civil-496", "civil-509"],
    )


def scan_contract(
    parsed: ParsedContract,
    contract_type: str = "labor",
) -> list[RiskFinding]:
    full_text = "\n".join(clause.text for clause in parsed.clauses)
    findings: list[RiskFinding] = []
    for clause in parsed.clauses:
        if contract_type == "labor":
            for check in (
                _check_probation_limit,
                _check_probation_salary,
                _check_service_period,
                _check_unilateral_termination,
                _check_social_insurance,
                _check_overtime_pay,
                _check_unilateral_change,
            ):
                finding = check(full_text, clause) if check is _check_probation_limit else check(clause)
                if finding:
                    findings.append(finding)
            findings.extend(_check_non_compete(clause))
        else:
            for check in (
                _check_liquidated_damages,
                _check_unilateral_change,
                _check_final_interpretation,
                _check_auto_renewal,
            ):
                finding = check(clause)
                if finding:
                    findings.append(finding)
        # Shared format-clause checks.
        for check in (_check_final_interpretation,):
            finding = check(clause)
            if finding and not any(
                item.rule_id == finding.rule_id and item.clause_index == finding.clause_index
                for item in findings
            ):
                findings.append(finding)

    # Deduplicate by (rule_id, clause_index).
    unique: list[RiskFinding] = []
    seen: set[tuple[str, int]] = set()
    for finding in findings:
        key = (finding.rule_id, finding.clause_index)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique


def risk_score(findings: list[RiskFinding]) -> float:
    """0 = no detected risk, 100 = maximum detected risk."""
    penalty = sum(_RISK_PENALTY[finding.risk_level] for finding in findings)
    return round(min(100.0, penalty), 1)


def overall_risk(findings: list[RiskFinding]) -> RiskLevel:
    if any(finding.risk_level == RiskLevel.HIGH for finding in findings):
        return RiskLevel.HIGH
    if any(finding.risk_level == RiskLevel.MEDIUM for finding in findings):
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
