"""Hybrid legal retrieval: BM25 + title/tag boosting + citation objects."""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.rag.bm25 import BM25Index
from app.rag.corpus import load_articles
from app.rag.tokenizer import tokenize
from app.schemas import LegalArticle, RetrievedArticle


class LawRetriever:
    def __init__(
        self,
        articles: list[LegalArticle] | None = None,
        laws_dir: Path | None = None,
    ) -> None:
        self.articles = articles if articles is not None else load_articles(laws_dir)
        self._tokens = [
            tokenize(f"{article.title} {' '.join(article.tags)} {article.text}")
            for article in self.articles
        ]
        self._index = BM25Index(self._tokens)
        self._title_tokens = [set(tokenize(article.title)) for article in self.articles]
        self._tag_tokens = [
            set(tokenize(" ".join(article.tags))) for article in self.articles
        ]

    @property
    def count(self) -> int:
        return len(self.articles)

    def get(self, article_id: str) -> LegalArticle | None:
        for article in self.articles:
            if article.id == article_id:
                return article
        return None

    def search(
        self,
        query: str,
        top_k: int | None = None,
        law: str | None = None,
    ) -> list[RetrievedArticle]:
        top_k = top_k or get_settings().retrieval_top_k
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        raw_results = self._index.search(query_tokens, top_k=max(top_k * 4, top_k))
        query_set = set(query_tokens)
        scored: list[tuple[int, float, float, list[str]]] = []
        for index, score, matched in raw_results:
            article = self.articles[index]
            if law and law not in article.law:
                continue
            title_hits = len(query_set & self._title_tokens[index])
            tag_hits = len(query_set & self._tag_tokens[index])
            boosted = score + 0.35 * title_hits + 0.20 * tag_hits
            coverage = len(set(matched)) / max(1, len(query_set))
            scored.append((index, boosted, coverage, matched))

        scored.sort(key=lambda item: item[1], reverse=True)
        results: list[RetrievedArticle] = []
        for index, score, coverage, matched in scored[:top_k]:
            results.append(
                RetrievedArticle(
                    article=self.articles[index],
                    score=round(score / (score + 2.0), 4),
                    coverage=round(coverage, 4),
                    matched_terms=matched[:8],
                )
            )
        return results


_retriever: LawRetriever | None = None


def get_retriever() -> LawRetriever:
    global _retriever
    if _retriever is None:
        _retriever = LawRetriever()
    return _retriever
