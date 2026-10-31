from __future__ import annotations

import uuid
from datetime import datetime, timezone

import re

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import Settings
from .llm import LLMError, LLMGroundingError, LLMMalformedOutput, LLMModelUnavailable, LLMService, LLMTimeout, LLMUnavailable, OllamaService
from .embeddings import OllamaEmbeddingService
from .models import Answer, CandidateAnswer, CreateRepositoryRequest, DecisionList, ErrorEnvelope, ErrorInfo, EvidenceList, GraphResponse, IngestionJob, QuestionRequest, Repository, RepositoryList, EvidenceRecord, RetrievalResult
from .graph import GraphService
from .retrieval import RetrievalService
from .service import IngestionService
from .url_validation import RepositoryUrlError
from .verification import verify_answer


settings = Settings.from_env()
graph_service = GraphService.from_settings(settings)
service = IngestionService(settings, graph=graph_service)
llm_service: LLMService = OllamaService.from_settings(settings)
embedding_service = OllamaEmbeddingService.from_settings(settings) if settings.semantic_search_enabled else None
retrieval_service = RetrievalService(service.store, graph_service, settings, embedding_service)
app = FastAPI(title="CodeTrace API", version="0.1.0", description="Evidence-backed repository history and explanation API")
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "X-Request-ID"])

_REPOSITORY_ID = re.compile(r"^repo_[0-9a-f]{24}$")


def validate_repository_id(repository_id: str) -> str:
    if not _REPOSITORY_ID.fullmatch(repository_id):
        raise HTTPException(status_code=422, detail="invalid_repository_id")
    return repository_id


def error_response(code: str, message: str, request_id: str, status_code: int, details: dict | None = None) -> JSONResponse:
    body = ErrorEnvelope(error=ErrorInfo(code=code, message=message, request_id=request_id, details=details or {}))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


@app.exception_handler(RepositoryUrlError)
async def repository_url_error(request: Request, exc: RepositoryUrlError) -> JSONResponse:
    return error_response("invalid_repository_url", str(exc), request.headers.get("x-request-id", "request_unknown"), 422)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    detail = str(exc.detail)
    return error_response(detail if detail.isidentifier() else "http_error", detail, request.headers.get("x-request-id", "request_unknown"), exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response("invalid_request", "Request validation failed", request.headers.get("x-request-id", "request_unknown"), 422, {"fields": exc.errors()})


@app.get("/health", tags=["system"])
@app.get("/api/health", include_in_schema=False, tags=["system"])
def health() -> dict[str, object]:
    return {"status": "ok", "dependencies": {"database": "ok", "neo4j": "configured" if graph_service.store else "unconfigured", "ollama": "not_checked"}}


@app.get("/v1/repositories", response_model=RepositoryList)
def list_repositories() -> RepositoryList:
    return RepositoryList(items=[Repository.model_validate(item) for item in service.store.list_repositories()])


@app.post("/v1/repositories", response_model=Repository, status_code=status.HTTP_201_CREATED)
def create_repository(payload: CreateRepositoryRequest) -> Repository:
    return service.register_repository(str(payload.remote_url), payload.default_branch)


@app.get("/v1/repositories/{repository_id}", response_model=Repository)
def get_repository(repository_id: str) -> Repository:
    validate_repository_id(repository_id)
    value = service.store.get_repository(repository_id)
    if not value:
        raise HTTPException(status_code=404, detail="repository_not_found")
    return Repository.model_validate(value)


@app.post("/v1/repositories/{repository_id}/ingestion-jobs", response_model=IngestionJob, status_code=status.HTTP_202_ACCEPTED)
def create_ingestion_job(repository_id: str, background_tasks: BackgroundTasks) -> IngestionJob:
    validate_repository_id(repository_id)
    try:
        job = service.create_job(repository_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="repository_not_found") from None
    background_tasks.add_task(service.run_job, job.id)
    return job


@app.get("/v1/ingestion-jobs/{job_id}", response_model=IngestionJob)
def get_ingestion_job(job_id: str) -> IngestionJob:
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ingestion_job_not_found")
    return job


@app.get("/v1/repositories/{repository_id}/evidence", response_model=EvidenceList)
def list_evidence(repository_id: str) -> EvidenceList:
    validate_repository_id(repository_id)
    if not service.store.get_repository(repository_id):
        raise HTTPException(status_code=404, detail="repository_not_found")
    return EvidenceList(items=service.store.list_evidence(repository_id))


@app.get("/v1/repositories/{repository_id}/graph", response_model=GraphResponse)
def get_graph(repository_id: str, node_type: list[str] | None = None, depth: int = Query(default=1, ge=0, le=3), limit: int = Query(default=100, ge=1, le=250)) -> GraphResponse:
    validate_repository_id(repository_id)
    if not service.store.get_repository(repository_id):
        raise HTTPException(status_code=404, detail="repository_not_found")
    return graph_service.get(repository_id, node_type, depth, limit)


@app.post("/v1/repositories/{repository_id}/questions", response_model=Answer)
def ask_question(repository_id: str, payload: QuestionRequest, request: Request) -> Answer:
    validate_repository_id(repository_id)
    if not service.store.get_repository(repository_id):
        raise HTTPException(status_code=404, detail="repository_not_found")
    retrieval = retrieval_service.retrieve(repository_id, payload.question)
    evidence_by_id = {item.evidence_id: item for item in [EvidenceRecord.model_validate(item) for item in service.store.list_evidence(repository_id)]}
    evidence = [evidence_by_id[hit.evidence_id] for hit in retrieval.hits if hit.evidence_id in evidence_by_id]
    if retrieval.status == "insufficient":
        candidate = CandidateAnswer(answer="No supported answer was generated.", status="insufficient_evidence", evidence_ids=[])
        answer_text, verification = verify_answer(candidate, retrieval, evidence)
        return Answer(id=f"answer_{uuid.uuid4().hex}", question=payload.question, answer=answer_text, status=verification.status, evidence_ids=verification.cited_evidence_ids, conflicts=[], evidence_facts=[], interpretation=None, created_at=datetime.now(timezone.utc), model=None, retrieval=retrieval, verification=verification, warnings=verification.warnings, claims=[])
    try:
        candidate, metadata = llm_service.answer(payload.question, evidence)
    except LLMError as exc:
        if isinstance(exc, LLMGroundingError):
            candidate = CandidateAnswer(answer="No supported answer was generated.", status="insufficient_evidence", evidence_ids=[])
            answer_text, verification = verify_answer(candidate, retrieval, evidence)
            verification.warnings.append("model_output_failed_citation_integrity")
            return Answer(id=f"answer_{uuid.uuid4().hex}", question=payload.question, answer=answer_text, status="insufficient_evidence", evidence_ids=[], conflicts=[], evidence_facts=[], interpretation=None, created_at=datetime.now(timezone.utc), model=None, retrieval=retrieval, verification=verification, warnings=verification.warnings, claims=[])
        messages = {
            LLMUnavailable.code: "AI service unavailable",
            LLMTimeout.code: "AI service timed out",
            LLMModelUnavailable.code: "Configured AI model is unavailable",
            LLMMalformedOutput.code: "Answer could not be generated",
            LLMGroundingError.code: "Answer could not be grounded in the indexed evidence",
        }
        codes = {LLMTimeout.code: 504, LLMUnavailable.code: 503, LLMModelUnavailable.code: 503, LLMMalformedOutput.code: 502, LLMGroundingError.code: 502}
        return error_response(exc.code, messages.get(exc.code, "Answer could not be generated"), request.headers.get("x-request-id", "request_unknown"), codes.get(exc.code, 502))
    answer_text, verification = verify_answer(candidate, retrieval, evidence)
    return Answer(id=f"answer_{uuid.uuid4().hex}", question=payload.question, answer=answer_text, status=verification.status, evidence_ids=verification.cited_evidence_ids, conflicts=candidate.conflicts, evidence_facts=candidate.evidence_facts, interpretation=candidate.interpretation, claims=candidate.claims, created_at=datetime.now(timezone.utc), model=metadata.model, retrieval=retrieval, verification=verification, warnings=verification.warnings)


@app.post("/v1/repositories/{repository_id}/retrieval", response_model=RetrievalResult)
def retrieve_question(repository_id: str, payload: QuestionRequest) -> RetrievalResult:
    validate_repository_id(repository_id)
    if not service.store.get_repository(repository_id):
        raise HTTPException(status_code=404, detail="repository_not_found")
    return retrieval_service.retrieve(repository_id, payload.question)


@app.get("/v1/repositories/{repository_id}/decisions", response_model=DecisionList)
def list_decisions(repository_id: str) -> DecisionList:
    validate_repository_id(repository_id)
    if not service.store.get_repository(repository_id):
        raise HTTPException(status_code=404, detail="repository_not_found")
    decisions, supersessions = service.store.list_decisions(repository_id)
    return DecisionList(repository_id=repository_id, items=decisions, supersessions=supersessions)
