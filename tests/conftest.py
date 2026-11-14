import json
from pathlib import Path

import pytest

from app.config import Settings
from app.db import LawRepository
from app.llm.client import LLMClient
from app.services.qa import QAService
from app.services.review import ReviewService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(llm_api_key="", database_path=tmp_path / "test.db")


@pytest.fixture
def repository(settings: Settings) -> LawRepository:
    return LawRepository(settings.database_path)


@pytest.fixture
def qa_service(repository: LawRepository, settings: Settings) -> QAService:
    return QAService(repository=repository, llm=LLMClient(settings))


@pytest.fixture
def review_service(repository: LawRepository, settings: Settings) -> ReviewService:
    return ReviewService(repository=repository, llm=LLMClient(settings))


@pytest.fixture
def contract_text():
    def _read(name: str) -> str:
        return (ROOT / "data" / "contracts" / name).read_text(encoding="utf-8")

    return _read


@pytest.fixture
def eval_questions() -> list[dict]:
    return json.loads(
        (ROOT / "data" / "qa" / "eval_questions.json").read_text(encoding="utf-8")
    )
