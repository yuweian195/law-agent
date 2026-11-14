"""Load the local legal corpus from JSONL files."""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.schemas import LegalArticle


def load_articles(laws_dir: Path | None = None) -> list[LegalArticle]:
    directory = Path(laws_dir or get_settings().laws_dir)
    if not directory.exists():
        return []

    articles: list[LegalArticle] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                article = LegalArticle.model_validate_json(line)
            except Exception:
                continue
            if article.id in seen:
                continue
            seen.add(article.id)
            articles.append(article)
    return articles
