"""Legal corpus search service."""

from __future__ import annotations

from app.rag.retriever import get_retriever
from app.schemas import LawSearchResponse


class LawService:
    def search(self, query: str, top_k: int = 5, law: str | None = None) -> LawSearchResponse:
        return LawSearchResponse(query=query, results=get_retriever().search(query, top_k, law))

    def count(self) -> int:
        return get_retriever().count


_service: LawService | None = None


def get_law_service() -> LawService:
    global _service
    if _service is None:
        _service = LawService()
    return _service
