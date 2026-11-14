"""State for the contract review workflow."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class ReviewState(TypedDict, total=False):
    review_id: str
    created_at: str
    llm_mode: str
    repository: Any

    contract_text: str
    contract_type: str
    title: str
    parsed_contract: dict
    findings: list[dict]
    overall_risk: str
    risk_score: float
    summary: str

    trace: Annotated[list[dict], operator.add]
