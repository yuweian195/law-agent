"""FastAPI service for legal Q&A and contract review."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, get_settings
from app.db import get_repository
from app.schemas import (
    ContractReview,
    ContractReviewListItem,
    ContractReviewRequest,
    HealthResponse,
    LawSearchResponse,
    QAListItem,
    QARecord,
    QARequest,
)
from app.services.law import get_law_service
from app.services.qa import get_qa_service
from app.services.reporting import qa_markdown, review_markdown
from app.services.review import get_review_service
from app.tools.contract_parser import decode_text


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_repository()
    yield


settings = get_settings()
app = FastAPI(
    title="LawAgent API",
    version=settings.version,
    description="Legal RAG, contract risk review and compensation calculation.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.version,
        llm_mode=get_qa_service().llm.mode,
        laws=get_law_service().count(),
    )


@app.get("/laws/search", response_model=LawSearchResponse)
def search_laws(q: str, top_k: int = 5, law: str | None = None) -> LawSearchResponse:
    return get_law_service().search(q, top_k=max(1, min(top_k, 20)), law=law)


@app.post("/contract/review", response_model=ContractReview)
def review_contract(payload: ContractReviewRequest) -> ContractReview:
    return get_review_service().review(payload)


@app.post("/contract/review/upload", response_model=ContractReview)
async def review_contract_upload(
    file: Annotated[UploadFile, File(...)],
    contract_type: Annotated[str, Form()] = "labor",
) -> ContractReview:
    content = await file.read()
    text = decode_text(file.filename or "", content)
    if len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail="未能从文件中解析出有效合同文本")
    return get_review_service().review(
        ContractReviewRequest(contract_text=text, contract_type=contract_type)
    )


@app.get("/reviews", response_model=list[ContractReviewListItem])
def list_reviews(limit: int = 20) -> list[ContractReviewListItem]:
    return get_review_service().list_recent(limit=max(1, min(limit, 100)))


@app.get("/reviews/{review_id}", response_model=ContractReview)
def get_review(review_id: str) -> ContractReview:
    review = get_review_service().get_review(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="审查记录不存在")
    return review


@app.get("/reviews/{review_id}/report", response_class=PlainTextResponse)
def get_review_report(review_id: str) -> PlainTextResponse:
    review = get_review_service().get_review(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="审查记录不存在")
    return PlainTextResponse(
        review_markdown(review),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="review-{review_id}.md"'},
    )


@app.post("/qa", response_model=QARecord)
def ask(payload: QARequest) -> QARecord:
    return get_qa_service().ask(payload)


@app.get("/qa/history", response_model=list[QAListItem])
def qa_history(limit: int = 20) -> list[QAListItem]:
    return get_qa_service().list_recent(limit=max(1, min(limit, 100)))


@app.get("/qa/{record_id}", response_model=QARecord)
def get_qa(record_id: str) -> QARecord:
    record = get_qa_service().get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="问答记录不存在")
    return record


@app.get("/qa/{record_id}/report", response_class=PlainTextResponse)
def get_qa_report(record_id: str) -> PlainTextResponse:
    record = get_qa_service().get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="问答记录不存在")
    return PlainTextResponse(
        qa_markdown(record),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="qa-{record_id}.md"'},
    )


# TypeScript contract review console (built with `npm run build`).
CONSOLE_DIST = BASE_DIR / "web" / "dist"
if CONSOLE_DIST.exists():
    app.mount("/console", StaticFiles(directory=CONSOLE_DIST, html=True), name="console")

    @app.get("/", include_in_schema=False)
    def console_root() -> RedirectResponse:
        return RedirectResponse(url="/console/")
