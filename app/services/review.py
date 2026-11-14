"""Contract review service."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.db import LawRepository, get_repository
from app.graph.review_workflow import get_review_graph
from app.llm.client import LLMClient, get_llm_client
from app.schemas import (
    ContractReview,
    ContractReviewListItem,
    ContractReviewRequest,
    RiskLevel,
)


class ReviewService:
    def __init__(
        self,
        repository: LawRepository | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self.repository = repository or get_repository()
        self.llm = llm or get_llm_client()

    def review(self, payload: ContractReviewRequest) -> ContractReview:
        review_id = uuid.uuid4().hex[:12]
        created_at = datetime.now().isoformat(timespec="seconds")
        initial_state = {
            "review_id": review_id,
            "created_at": created_at,
            "llm_mode": self.llm.mode,
            "repository": self.repository,
            "contract_text": payload.contract_text,
            "contract_type": payload.contract_type,
            "title": payload.title or "",
            "trace": [],
        }
        final_state = get_review_graph().invoke(initial_state)
        return ContractReview(
            id=review_id,
            contract_title=final_state.get("title")
            or final_state["parsed_contract"]["title"],
            contract_type=payload.contract_type,
            overall_risk=RiskLevel(final_state["overall_risk"]),
            risk_score=final_state["risk_score"],
            findings=final_state["findings"],
            clauses=final_state["parsed_contract"]["clauses"],
            summary=final_state["summary"],
            trace=final_state["trace"],
            llm_mode=final_state.get("llm_mode", self.llm.mode),
            created_at=created_at,
        )

    def get_review(self, review_id: str) -> ContractReview | None:
        payload = self.repository.get_review(review_id)
        if payload is None:
            return None
        return ContractReview.model_validate(payload)

    def list_recent(self, limit: int = 20) -> list[ContractReviewListItem]:
        return [
            ContractReviewListItem(
                id=item["id"],
                contract_title=item["contract_title"],
                contract_type=item["contract_type"],
                overall_risk=RiskLevel(item["overall_risk"]),
                risk_score=item["risk_score"],
                findings_count=item["findings_count"],
                created_at=item["created_at"],
            )
            for item in self.repository.list_reviews(limit)
        ]


_service: ReviewService | None = None


def get_review_service() -> ReviewService:
    global _service
    if _service is None:
        _service = ReviewService()
    return _service
