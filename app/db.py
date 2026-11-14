"""SQLite persistence for contract reviews and legal Q&A records."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from app.config import get_settings


class LawRepository:
    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = Path(database_path or get_settings().database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _init_schema(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS contract_reviews (
                    id TEXT PRIMARY KEY,
                    contract_title TEXT NOT NULL,
                    contract_type TEXT NOT NULL,
                    overall_risk TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    findings_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_reviews_created_at "
                "ON contract_reviews(created_at DESC)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS qa_records (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    citations_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_qa_created_at "
                "ON qa_records(created_at DESC)"
            )

    def save_review(self, record: dict[str, Any]) -> None:
        payload = record.get("payload", record)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO contract_reviews
                (id, contract_title, contract_type, overall_risk, risk_score,
                 findings_count, created_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["contract_title"],
                    record["contract_type"],
                    record["overall_risk"],
                    float(record["risk_score"]),
                    int(record["findings_count"]),
                    record["created_at"],
                    json.dumps(payload, ensure_ascii=False, default=str),
                ),
            )

    def list_reviews(self, limit: int = 20) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT id, contract_title, contract_type, overall_risk, risk_score,
                       findings_count, created_at
                FROM contract_reviews ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_review(self, review_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload FROM contract_reviews WHERE id = ?", (review_id,)
            ).fetchone()
        if not row:
            return None
        return json.loads(row["payload"])

    def save_qa(self, record: dict[str, Any]) -> None:
        payload = record.get("payload", record)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO qa_records
                (id, question, intent, citations_count, created_at, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["question"],
                    record["intent"],
                    int(record["citations_count"]),
                    record["created_at"],
                    json.dumps(payload, ensure_ascii=False, default=str),
                ),
            )

    def list_qa(self, limit: int = 20) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT id, question, intent, citations_count, created_at
                FROM qa_records ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_qa(self, record_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload FROM qa_records WHERE id = ?", (record_id,)
            ).fetchone()
        if not row:
            return None
        return json.loads(row["payload"])

    def count_reviews(self) -> int:
        with closing(self._connect()) as connection, connection:
            row = connection.execute("SELECT COUNT(*) AS n FROM contract_reviews").fetchone()
        return int(row["n"])


_repository: LawRepository | None = None


def get_repository() -> LawRepository:
    global _repository
    if _repository is None:
        _repository = LawRepository()
    return _repository
