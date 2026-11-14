"""Legal Q&A service."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.db import LawRepository, get_repository
from app.graph.qa_workflow import get_qa_graph
from app.llm.client import LLMClient, get_llm_client
from app.schemas import QAListItem, QARecord, QARequest


class QAService:
    def __init__(
        self,
        repository: LawRepository | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self.repository = repository or get_repository()
        self.llm = llm or get_llm_client()

    def ask(self, payload: QARequest) -> QARecord:
        qa_id = uuid.uuid4().hex[:12]
        created_at = datetime.now().isoformat(timespec="seconds")
        initial_state = {
            "qa_id": qa_id,
            "created_at": created_at,
            "llm_mode": self.llm.mode,
            "repository": self.repository,
            "question": payload.question,
            "context": payload.context,
            "trace": [],
        }
        final_state = get_qa_graph().invoke(initial_state)
        return QARecord(
            id=qa_id,
            question=payload.question,
            intent=final_state["intent"],
            conclusion=final_state["conclusion"],
            analysis=final_state["analysis"],
            calculation=final_state.get("calculation"),
            citations=final_state["citations"],
            disclaimer=final_state["disclaimer"],
            trace=final_state["trace"],
            llm_mode=final_state.get("llm_mode", self.llm.mode),
            created_at=created_at,
        )

    def get_record(self, record_id: str) -> QARecord | None:
        payload = self.repository.get_qa(record_id)
        if payload is None:
            return None
        return QARecord.model_validate(payload)

    def list_recent(self, limit: int = 20) -> list[QAListItem]:
        return [
            QAListItem(
                id=item["id"],
                question=item["question"],
                intent=item["intent"],
                citations_count=item["citations_count"],
                created_at=item["created_at"],
            )
            for item in self.repository.list_qa(limit)
        ]


_service: QAService | None = None


def get_qa_service() -> QAService:
    global _service
    if _service is None:
        _service = QAService()
    return _service
