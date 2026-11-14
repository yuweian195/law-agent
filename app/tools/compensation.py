"""Severance and illegal-dismissal compensation calculator."""

from __future__ import annotations

from app.schemas import CompensationResult
from app.tools.question_parser import QuestionFacts


def _compensation_years(years: float, months: int) -> float:
    total_months = int(round(years * 12)) + months
    full_years = total_months // 12
    remainder = total_months % 12
    if remainder >= 6:
        return float(full_years + 1)
    if remainder > 0:
        return float(full_years) + 0.5
    return float(full_years)


def calculate_compensation(facts: QuestionFacts) -> CompensationResult | None:
    if facts.monthly_salary <= 0:
        return None
    if facts.years <= 0 and facts.months <= 0:
        return None
    if facts.intent not in ("severance", "probation"):
        return None

    years = _compensation_years(facts.years, facts.months)
    salary = facts.monthly_salary
    breakdown: list[str] = []
    assumptions = [
        "月工资按劳动合同解除或终止前十二个月的平均工资计算。",
        "未考虑当地上年度职工月平均工资三倍的封顶规则和十二年上限。",
        "未包含未休年假、加班费、未签书面合同二倍工资等其他请求。",
    ]

    if facts.termination == "illegal":
        amount = 2 * years * salary
        formula = "赔偿金 = 2 × 经济补偿年限 × 月工资"
        breakdown.append(f"经济补偿年限：{years:g} 个月工资")
        breakdown.append(f"违法解除赔偿金：2 × {years:g} × {salary:,.0f} = {amount:,.0f} 元")
    elif facts.termination == "resign":
        return CompensationResult(
            applies=False,
            formula="主动辞职通常不产生经济补偿",
            years=years,
            base_salary=salary,
            amount=0.0,
            breakdown=["劳动者主动辞职，且不属于被迫解除情形的，一般无经济补偿。"],
            assumptions=assumptions,
        )
    else:
        amount = years * salary
        formula = "经济补偿 = 经济补偿年限 × 月工资"
        breakdown.append(f"经济补偿年限：{years:g} 个月工资")
        breakdown.append(f"经济补偿：{years:g} × {salary:,.0f} = {amount:,.0f} 元")
        if facts.notice_missing and facts.termination in ("unspecified", "probation_dismissal"):
            amount += salary
            breakdown.append(f"未提前三十日书面通知，额外支付一个月工资：{salary:,.0f} 元")
            formula += "（未提前通知时 +1 个月工资）"

    return CompensationResult(
        applies=True,
        formula=formula,
        years=years,
        base_salary=salary,
        amount=round(amount, 2),
        breakdown=breakdown,
        assumptions=assumptions,
    )
