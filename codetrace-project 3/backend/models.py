from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


JobStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


class ErrorInfo(BaseModel):
    code: str
    message: str
    request_id: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorInfo


class CreateRepositoryRequest(BaseModel):
    remote_url: HttpUrl
    default_branch: str | None = Field(default=None, min_length=1, max_length=255)


class Repository(BaseModel):
    id: str
    full_name: str
    remote_url: str
    default_branch: str | None = None
    language: str | None = None
    index_status: Literal["not_indexed", "pending", "running", "indexed", "stale", "failed"]
    last_indexed_at: datetime | None = None
    last_sync_sha: str | None = None
    counts: dict[str, int] | None = None


class RepositoryList(BaseModel):
    items: list[Repository]
    next_cursor: str | None = None


class IngestionJob(BaseModel):
    id: str
    repository_id: str
    status: JobStatus
    progress: float | None = Field(default=None, ge=0, le=1)
    stage: str | None = None
    error: ErrorInfo | None = None
    created_at: datetime
    updated_at: datetime


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    entity_ids: list[str] = Field(default_factory=list, max_length=100)


AnswerStatus = Literal["supported", "partially_supported", "insufficient_evidence", "conflicting_evidence"]


class CandidateAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=20_000)
    status: AnswerStatus
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    conflicts: list[str] = Field(default_factory=list, max_length=50)
    evidence_facts: list[str] = Field(default_factory=list, max_length=100)
    interpretation: str | None = Field(default=None, max_length=10_000)
    claims: list["CandidateClaim"] = Field(default_factory=list, max_length=100)


class CandidateClaim(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)


class Answer(CandidateAnswer):
    id: str
    question: str
    created_at: datetime
    model: str | None = None
    retrieval: "RetrievalResult | None" = None
    verification: "VerificationReport | None" = None
    warnings: list[str] = Field(default_factory=list)


class GitCommit(BaseModel):
    source_id: str
    sha: str
    message: str
    author_name: str
    author_email: str | None = None
    authored_at: datetime | None
    changed_paths: list[str]
    additions: int | None = None
    deletions: int | None = None
    changed_files: int | None = None
    source_url: str | None = None
    file_changes: list["FileChange"] = Field(default_factory=list)


class GitHubSource(BaseModel):
    source_id: str
    source_type: Literal["issue", "pull_request", "discussion", "comment"]
    title: str | None = None
    body: str | None = None
    author: str | None = None
    observed_at: datetime | None = None
    source_url: str | None = None
    number: int | None = None
    parent_source_id: str | None = None


class LineRange(BaseModel):
    start: int = Field(ge=1)
    end: int = Field(ge=1)


class FileChange(BaseModel):
    path: str
    previous_path: str | None = None
    status: Literal["added", "modified", "deleted", "renamed", "binary", "unknown"] = "unknown"
    additions: int | None = None
    deletions: int | None = None
    line_ranges: list[LineRange] = Field(default_factory=list)


class RawDocumentation(BaseModel):
    source_id: str
    repository_id: str
    path: str
    title: str | None = None
    content: str
    source_url: str | None = None
    author: str | None = None
    observed_at: datetime | None = None


class Interpretation(BaseModel):
    text: str
    kind: Literal["inferred", "machine_extracted"]
    basis_evidence_ids: list[str] = Field(default_factory=list)


class Provenance(BaseModel):
    source_type: Literal["commit", "pull_request", "issue", "comment", "discussion", "documentation", "incident", "decision_record", "code_change", "code_excerpt"]
    source_id: str
    repository_id: str
    raw_source_ref: str
    ingested_at: datetime
    normalizer_version: str
    parent_source_ids: list[str] = Field(default_factory=list)


class EvidenceRecord(BaseModel):
    evidence_id: str
    repository_id: str
    source_type: Literal["commit", "pull_request", "issue", "comment", "discussion", "documentation", "incident", "decision_record", "code_change", "code_excerpt"]
    source_id: str
    title: str | None = None
    summary: str | None = None
    author: str | None = None
    observed_at: datetime | None = None
    source_url: str | None = None
    excerpt: str | None = None
    excerpt_origin: Literal["original", "derived"] | None = None
    changed_files: list[FileChange] = Field(default_factory=list)
    interpretations: list[Interpretation] = Field(default_factory=list)
    provenance: Provenance
    content_hash: str


class EvidenceList(BaseModel):
    items: list[EvidenceRecord]
    next_cursor: str | None = None


GraphNodeType = Literal["repository", "file", "code_entity", "configuration_key", "commit", "pull_request", "issue", "discussion", "comment", "documentation", "incident", "decision_record", "code_change", "code_excerpt", "evidence", "decision", "person"]
GraphRelationshipType = Literal["CONTAINS", "MODIFIED_BY", "REFERENCES", "DISCUSSED_IN", "SUPPORTED_BY", "AFFECTS", "RELATED_TO", "SUPERSEDES"]


class GraphNode(BaseModel):
    id: str
    repository_id: str
    node_type: GraphNodeType
    label: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_ids: list[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    id: str
    repository_id: str
    source: str
    target: str
    relationship_type: GraphRelationshipType
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    repository_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    available: bool = True
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)


class GraphPathNode(BaseModel):
    id: str
    label: str
    node_type: GraphNodeType


class GraphPath(BaseModel):
    nodes: list[GraphPathNode]
    relationships: list[GraphRelationshipType]


class RetrievalHit(BaseModel):
    evidence_id: str
    score: float = Field(ge=0)
    rank: int = Field(ge=1)
    signals: dict[str, float] = Field(default_factory=dict)
    matched_terms: list[str] = Field(default_factory=list)
    title: str | None = None
    source_type: str
    observed_at: datetime | None = None
    source_url: str | None = None
    excerpt: str | None = None
    graph_paths: list[GraphPath] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    repository_id: str
    question: str
    normalized_question: str
    intent: Literal["why", "what_changed", "current", "support", "unknown"]
    status: Literal["found", "insufficient", "conflicting"]
    hits: list[RetrievalHit] = Field(default_factory=list)
    graph_paths: list[GraphPath] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    diagnostics: dict[str, int] = Field(default_factory=dict)


class VerifiedSource(BaseModel):
    evidence_id: str
    source_type: str
    title: str | None = None
    source_url: str | None = None
    observed_at: datetime | None = None


class VerifiedClaim(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    support: Literal["supported", "unsupported", "uncertain", "conflicting"]
    warnings: list[str] = Field(default_factory=list)


class VerificationReport(BaseModel):
    status: AnswerStatus
    claims: list[VerifiedClaim] = Field(default_factory=list)
    cited_evidence_ids: list[str] = Field(default_factory=list)
    sources: list[VerifiedSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    mechanically_verified: bool = False


DecisionStatus = Literal["candidate", "confirmed", "superseded", "unresolved", "conflicting"]
SupersessionStatus = Literal["confirmed", "uncertain", "rejected"]


class DecisionCandidate(BaseModel):
    decision_id: str
    repository_id: str
    statement: str
    status: DecisionStatus
    evidence_kind: Literal["explicit", "inferred"]
    evidence_ids: list[str] = Field(default_factory=list)
    affected_paths: list[str] = Field(default_factory=list)
    configuration_keys: list[str] = Field(default_factory=list)
    observed_at: datetime | None = None
    source_type: str
    source_id: str


class SupersessionAssessment(BaseModel):
    assessment_id: str
    repository_id: str
    newer_decision_id: str
    older_decision_id: str
    status: SupersessionStatus
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str
    same_behavior: bool


class DecisionList(BaseModel):
    repository_id: str
    items: list[DecisionCandidate]
    supersessions: list[SupersessionAssessment] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


Answer.model_rebuild()


GitCommit.model_rebuild()


class SyncResult(BaseModel):
    repository_id: str
    sync_sha: str
    commits: list[GitCommit]
    github_sources: list[GitHubSource]
    warnings: list[str] = Field(default_factory=list)
    counts: dict[str, int]
