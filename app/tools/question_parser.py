"""Lightweight fact extraction for labour-law questions."""

from __future__ import annotations

import re
from dataclasses import dataclass

_CN_DIGITS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


@dataclass
class QuestionFacts:
    intent: str = "general"
    years: float = 0.0
    months: int = 0
    monthly_salary: float = 0.0
    termination: str = "unspecified"
    notice_missing: bool = False


def _cn_to_int(text: str) -> int:
    if text.isdigit():
        return int(text)
    if text == "十":
        return 10
    if "十" in text:
        left, _, right = text.partition("十")
        tens = _CN_DIGITS.get(left, 1) if left else 1
        ones = _CN_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    return _CN_DIGITS.get(text, 0)


def classify_intent(question: str) -> str:
    text = question.replace(" ", "")
    if "试用期" in text:
        return "probation"
    if "竞业" in text:
        return "non_compete"
    if "服务期" in text:
        return "service_period"
    if any(word in text for word in ("社保", "社会保险", "五险")):
        return "social_insurance"
    if "加班" in text:
        return "overtime"
    if "违约金" in text:
        return "contract_penalty"
    if any(word in text for word in ("n+1", "n + 1", "被优化", "优化了", "劝退")):
        return "severance"
    if any(word in text for word in ("赔偿", "补偿", "辞退", "解除", "裁员", "开除")):
        return "severance"
    return "general"


def _extract_years_months(text: str) -> tuple[float, int]:
    match = re.search(r"(\d+)\s*年\s*(\d+)\s*个月", text)
    if match:
        return float(match.group(1)), int(match.group(2))
    match = re.search(r"([一二两三四五六七八九十]+)\s*年\s*([一二两三四五六七八九十]+)\s*个月", text)
    if match:
        return float(_cn_to_int(match.group(1))), _cn_to_int(match.group(2))
    match = re.search(r"工作(?:了)?\s*(\d+(?:\.\d+)?)\s*年", text)
    if match:
        return float(match.group(1)), 0
    match = re.search(r"([一二两三四五六七八九十]+)\s*年", text)
    if match:
        return float(_cn_to_int(match.group(1))), 0
    match = re.search(r"工作(?:了)?\s*(\d+)\s*个月", text)
    if match:
        return 0.0, int(match.group(1))
    return 0.0, 0


def _normalize_salary(value: str, unit: str | None) -> float:
    number = float(value)
    if unit == "万":
        return number * 10000
    if unit in ("k", "K", "千"):
        return number * 1000
    return number


def _extract_salary(text: str) -> float:
    match = re.search(r"(?:月薪|月工资|工资)\s*(?:为|是|：|:)?\s*(\d+(?:\.\d+)?)\s*(万|k|K|千|元)?", text)
    if match:
        salary = _normalize_salary(match.group(1), match.group(2))
        return salary if salary >= 1000 else 0.0
    match = re.search(r"(\d+(?:\.\d+)?)\s*万\s*(?:元)?", text)
    if match:
        return float(match.group(1)) * 10000
    return 0.0


def _termination_type(text: str) -> str:
    if any(word in text for word in ("违法解除", "违法辞退", "无故辞退", "单方解除", "强行辞退")):
        return "illegal"
    if any(word in text for word in ("协商解除", "协商一致")):
        return "mutual"
    if any(word in text for word in ("裁员", "经济性裁员")):
        return "layoff"
    if any(word in text for word in ("主动辞职", "自己离职", "个人原因")):
        return "resign"
    if "试用期" in text and any(word in text for word in ("辞退", "解除")):
        return "probation_dismissal"
    return "unspecified"


def extract_facts(question: str, context: str = "") -> QuestionFacts:
    text = f"{question}\n{context}"
    years, months = _extract_years_months(text)
    return QuestionFacts(
        intent=classify_intent(question),
        years=years,
        months=months,
        monthly_salary=_extract_salary(text),
        termination=_termination_type(text),
        notice_missing=any(
            word in text for word in ("未提前通知", "没有提前通知", "立即辞退", "当天辞退", "马上走人")
        ),
    )
