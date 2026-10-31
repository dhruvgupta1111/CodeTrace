from __future__ import annotations

import urllib.error
from datetime import datetime, timezone

import pytest

from backend.llm import LLMGroundingError, LLMMalformedOutput, LLMModelUnavailable, LLMTimeout, LLMUnavailable, OllamaService
from backend.models import EvidenceRecord, Provenance


def evidence(evidence_id: str = "evidence_1") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id, repository_id="repo_1", source_type="commit", source_id="git:1", title="fix retry",
        summary="fix retry", author="A", observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc), source_url="https://github.com/a/b/commit/1",
        excerpt="fix retry", excerpt_origin="original", provenance=Provenance(source_type="commit", source_id="git:1", repository_id="repo_1", raw_source_ref="raw:repo_1:git:1", ingested_at=datetime(2026, 1, 1, tzinfo=timezone.utc), normalizer_version="test"), content_hash="hash",
    )


def service_with(payload, seen=None) -> OllamaService:
    def request(url, body, timeout):
        if seen is not None:
            seen.append((url, body, timeout))
        return payload

    return OllamaService("http://ollama.test", "test-model", timeout_seconds=4, context_limit=2000, request=request)


def test_valid_structured_output_is_grounded_and_prompt_separates_untrusted_evidence() -> None:
    seen = []
    service = service_with({"message": {"content": '{"answer":"The source only says fix retry.","status":"supported","evidence_ids":["evidence_1"],"conflicts":[],"evidence_facts":["The commit message says fix retry."],"interpretation":null}'}}, seen)
    answer, metadata = service.answer("Why is retry here?", [evidence()])
    assert answer.evidence_ids == ["evidence_1"]
    assert answer.status == "supported"
    assert metadata.evidence_count == 1
    assert seen[0][1]["messages"][0]["role"] == "system"
    assert "untrusted" in seen[0][1]["messages"][0]["content"]
    assert "evidence_1" in seen[0][1]["messages"][1]["content"]
    assert seen[0][1]["stream"] is False


def test_malformed_output_is_rejected() -> None:
    service = service_with({"message": {"content": "not json"}})
    with pytest.raises(LLMMalformedOutput):
        service.answer("why", [evidence()])


def test_unknown_evidence_ids_and_missing_ids_are_rejected() -> None:
    unknown = service_with({"message": {"content": '{"answer":"claim","status":"supported","evidence_ids":["not_supplied"]}'}})
    with pytest.raises(LLMGroundingError):
        unknown.answer("why", [evidence()])
    missing = service_with({"message": {"content": '{"answer":"claim","status":"supported","evidence_ids":[]}'}})
    with pytest.raises(LLMGroundingError):
        missing.answer("why", [evidence()])


def test_insufficient_answer_can_have_no_evidence_ids() -> None:
    service = service_with({"response": '{"answer":"Insufficient evidence.","status":"insufficient_evidence","evidence_ids":[],"conflicts":[],"evidence_facts":[],"interpretation":null}'})
    answer, _ = service.answer("why", [evidence()])
    assert answer.status == "insufficient_evidence"
    assert answer.evidence_ids == []


@pytest.mark.parametrize("error", [LLMTimeout("timeout"), LLMUnavailable("down"), LLMModelUnavailable("missing")])
def test_controlled_transport_errors_are_preserved(error) -> None:
    def request(url, body, timeout):
        raise error

    service = OllamaService("http://ollama.test", "test-model", request=request)
    with pytest.raises(type(error)):
        service.answer("why", [evidence()])


def test_connection_failures_from_default_transport_are_mapped() -> None:
    def request(url, body, timeout):
        raise urllib.error.URLError("connection refused")

    service = OllamaService("http://ollama.test", "test-model", request=request)
    with pytest.raises(LLMUnavailable):
        service.answer("why", [evidence()])
