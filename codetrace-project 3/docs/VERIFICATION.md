# Answer verification and abstention

`backend/verification.py` runs after retrieval and Ollama generation. It is independent from both services and accepts only the candidate answer, the retrieval result, and the trusted stored evidence records.

## Mechanical checks

The verifier mechanically checks:

- every cited evidence ID exists in the retrieved evidence set;
- claims without evidence links are flagged;
- source metadata comes from stored `EvidenceRecord` values, never from model output;
- stored URLs are revalidated before being returned to the UI;
- empty retrieval produces `insufficient_evidence`;
- retrieval conflicts are surfaced as `conflicting_evidence`;
- missing or fabricated citations produce an abstention.

It returns trusted source cards, per-claim support labels, warnings, uncertainties, and a `mechanically_verified` marker.

## Semantic limits

The current support check is a conservative lexical heuristic over the stored title, summary, and excerpt. It can detect obvious mismatches and unsupported causal claims, but it cannot prove that a source truly establishes historical intent. Answers without explicit per-claim citations are downgraded to `partially_supported` with `claim_support_requires_semantic_review`.

The verifier is therefore a safety boundary, not perfect hallucination prevention. Human review, stronger claim extraction, and future evaluation are still required for high-confidence historical explanations.

