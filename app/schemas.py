"""Pydantic models shared by the API, workflows and UI."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LegalArticle(BaseModel):
    id: str
    law: str
    article: str
    title: str
    text: str
    tags: list[str] = Field(default_factory=list)


class RetrievedArticle(BaseModel):
    article: LegalArticle
    score: float
    coverage: float = 0.0
    matched_terms: list[str] = Field(default_factory=list)


class LawSearchResponse(BaseModel):
    query: str
    results: list[RetrievedArticle] = Field(default_factory=list)


class ContractClause(BaseModel):
    index: int
    title: str
    text: str


class ParsedContract(BaseModel):
    title: str = ""
    parties: list[str] = Field(default_factory=list)
    clauses: list[ContractClause] = Field(default_factory=list)


class LegalBasis(BaseModel):
    article_id: str
    law: str
    article: str
    title: str
    text: str = ""


class RiskFinding(BaseModel):
    rule_id: str
    clause_index: int
    clause_title: str
    risk_level: RiskLevel
    issue: str
    suggestion: str
    matched_text: str = ""
    legal_basis: list[LegalBasis] = Field(default_factory=list)


class ContractReviewRequest(BaseModel):
    contract_text: str = Field(min_length=20)
    contract_type: str = "labor"
    title: str | None = None


class ContractReview(BaseModel):
    id: str
    contract_title: str
    contract_type: str
    overall_risk: RiskLevel
    risk_score: float
    findings: list[RiskFinding] = Field(default_factory=list)
    clauses: list[ContractClause] = Field(default_factory=list)
    summary: str = ""
    trace: list[TraceStep] = Field(default_factory=list)
    llm_mode: str = "offline"
    created_at: datetime = Field(default_factory=datetime.now)


class ContractReviewListItem(BaseModel):
    id: str
    contract_title: str
    contract_type: str
    overall_risk: RiskLevel
    risk_score: float
    findings_count: int
    created_at: datetime


class QARequest(BaseModel):
    question: str = Field(min_length=5)
    context: str = ""


class CompensationResult(BaseModel):
    applies: bool = False
    formula: str = ""
    years: float = 0.0
    base_salary: float = 0.0
    amount: float = 0.0
    breakdown: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class LegalCitation(BaseModel):
    article_id: str
    law: str
    article: str
    title: str
    text: str
    score: float


class QARecord(BaseModel):
    id: str
    question: str
    intent: str
    conclusion: str
    analysis: str
    calculation: CompensationResult | None = None
    citations: list[LegalCitation] = Field(default_factory=list)
    disclaimer: str = ""
    trace: list[TraceStep] = Field(default_factory=list)
    llm_mode: str = "offline"
    created_at: datetime = Field(default_factory=datetime.now)


class QAListItem(BaseModel):
    id: str
    question: str
    intent: str
    citations_count: int
    created_at: datetime


class TraceStep(BaseModel):
    node: str
    label: str
    status: str = "ok"
    duration_ms: int = 0
    summary: str = ""


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_mode: str
    laws: int


ContractReview.model_rebuild()
QARecord.model_rebuild()
