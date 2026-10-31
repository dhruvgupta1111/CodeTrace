from __future__ import annotations

from datetime import datetime, timezone

from backend.models import CandidateAnswer, CandidateClaim, EvidenceRecord, Provenance, RetrievalHit, RetrievalResult
from backend.verification import verify_answer


def evidence(evidence_id: str, excerpt: str, url: str | None = "https://github.com/a/b/commit/1") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id, repository_id="repo_1", source_type="commit", source_id=f"git:{evidence_id}", title="Retry policy", summary=None,
        author="A", observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc), source_url=url, excerpt=excerpt, excerpt_origin="original",
        provenance=Provenance(source_type="commit", source_id=f"git:{evidence_id}", repository_id="repo_1", raw_source_ref=f"raw:repo_1:{evidence_id}", ingested_at=datetime(2026, 1, 1, tzinfo=timezone.utc), normalizer_version="test"), content_hash=evidence_id,
    )


def retrieval(*ids: str, status: str = "found") -> RetrievalResult:
    return RetrievalResult(repository_id="repo_1", question="why", normalized_question="why", intent="why", status=status, hits=[RetrievalHit(evidence_id=evidence_id, score=1, rank=index + 1, source_type="commit", excerpt=None) for index, evidence_id in enumerate(ids)])


def test_valid_citation_and_trusted_source_url_are_returned() -> None:
    item = evidence("e1", "The gateway rate limit required bounded retries.")
    candidate = CandidateAnswer(answer="Retries were bounded because the gateway had a rate limit.", status="supported", evidence_ids=["e1"], claims=[CandidateClaim(text="The gateway rate limit required bounded retries.", evidence_ids=["e1"])])
    answer, report = verify_answer(candidate, retrieval("e1"), [item])
    assert report.status == "supported"
    assert report.mechanically_verified
    assert report.sources[0].source_url == item.source_url
    assert answer == candidate.answer


def test_fabricated_evidence_id_abstains() -> None:
    candidate = CandidateAnswer(answer="The retry was introduced because of an outage.", status="supported", evidence_ids=["fabricated"], claims=[CandidateClaim(text="The retry was introduced because of an outage.", evidence_ids=["fabricated"])])
    answer, report = verify_answer(candidate, retrieval("e1"), [evidence("e1", "fix retry")])
    assert report.status == "insufficient_evidence"
    assert "citation_not_found_in_retrieved_evidence" in report.warnings
    assert "cannot establish" in answer.lower()


def test_invalid_url_is_not_taken_from_candidate_and_is_omitted() -> None:
    item = evidence("e1", "The gateway rate limit required bounded retries.", "javascript:alert(1)")
    candidate = CandidateAnswer(answer="The gateway rate limit required bounded retries.", status="supported", evidence_ids=["e1"], claims=[CandidateClaim(text="The gateway rate limit required bounded retries.", evidence_ids=["e1"])])
    _, report = verify_answer(candidate, retrieval("e1"), [item])
    assert report.status == "supported"
    assert report.sources[0].source_url is None
    assert "invalid_stored_source_url_omitted" in report.warnings


def test_unsupported_causal_claim_abstains_even_with_a_real_citation() -> None:
    item = evidence("e1", "fix retry")
    candidate = CandidateAnswer(answer="Retry was introduced because the gateway failed.", status="supported", evidence_ids=["e1"], claims=[CandidateClaim(text="Retry was introduced because the gateway failed.", evidence_ids=["e1"])])
    answer, report = verify_answer(candidate, retrieval("e1"), [item])
    assert report.status == "insufficient_evidence"
    assert report.claims[0].support == "uncertain"
    assert "cannot establish" in answer.lower()


def test_partial_support_and_conflicting_retrieval_are_visible() -> None:
    first = evidence("e1", "Gateway rate limits required bounded retries.")
    second = evidence("e2", "This contradicts the earlier retry rationale.")
    candidate = CandidateAnswer(answer="Retries were bounded and the reason is partly unclear.", status="partially_supported", evidence_ids=["e1", "e2"], claims=[CandidateClaim(text="Gateway rate limits required bounded retries.", evidence_ids=["e1"]), CandidateClaim(text="The reason is unclear.", evidence_ids=["e2"])])
    _, report = verify_answer(candidate, retrieval("e1", "e2", status="conflicting"), [first, second])
    assert report.status == "conflicting_evidence"
    assert any(claim.support == "conflicting" for claim in report.claims)


def test_empty_retrieval_abstains() -> None:
    candidate = CandidateAnswer(answer="There is a reason.", status="supported", evidence_ids=[])
    answer, report = verify_answer(candidate, retrieval(), [])
    assert report.status == "insufficient_evidence"
    assert "no_retrieved_evidence" in report.warnings
    assert "cannot establish" in answer.lower()
