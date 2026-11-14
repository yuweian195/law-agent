"""State for the legal Q&A workflow."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class QAState(TypedDict, total=False):
    qa_id: str
    created_at: str
    llm_mode: str
    repository: Any

    question: str
    context: str
    intent: str
    facts: dict
    citations: list[dict]
    calculation: dict | None
    conclusion: str
    analysis: str
    disclaimer: str

    trace: Annotated[list[dict], operator.add]
