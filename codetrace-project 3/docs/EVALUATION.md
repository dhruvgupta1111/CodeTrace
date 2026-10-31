# Hackathon evaluation smoke set

This is a small deterministic evaluation set built from test fixtures, not a production benchmark. It checks the trust boundaries that matter for the demo: citation integrity, abstention, conflicts, temporal replacement, graph contribution, and provider failure handling.

| Case | Fixture and expected behavior | Automated coverage | Observed result |
| --- | --- | --- | --- |
| Evidence-backed answer | Gateway rate-limit evidence supports bounded retries | `tests/test_verification.py::test_valid_citation_and_trusted_source_url_are_returned` | Citation accepted; stored HTTPS URL returned |
| Historical reversal | Later explicit revert on the same timeout behavior | `tests/test_decision.py::test_explicit_reversal_confirms_supersession_for_same_behavior` | Confirmed supersession with both evidence IDs |
| Missing explanation | “fix retry” does not establish a causal reason | `tests/test_verification.py::test_unsupported_causal_claim_abstains_even_with_a_real_citation` | `insufficient_evidence` |
| Conflicting evidence | Contradictory retry rationale | `tests/test_verification.py::test_partial_support_and_conflicting_retrieval_are_visible` | `conflicting_evidence` |
| Graph-assisted retrieval | Issue connected through a referenced retry file | `tests/test_retrieval.py::test_graph_traversal_finds_related_issue_not_matching_file_text` | Graph path discovers the issue; keyword-only path does not return it in the same fixture |
| Provider failure | Ollama unavailable, timeout, or missing model | `tests/test_llm.py::test_controlled_transport_errors_are_preserved` | Controlled typed errors; API maps them to safe HTTP errors |
| Graph failure | Neo4j unavailable | `tests/test_graph.py::test_graph_service_returns_explicit_empty_response_without_neo4j` | Empty bounded response with `neo4j_unavailable` warning |

The current measured suite result is 45 passing backend tests, including these cases. This is pass/fail fixture coverage, not a statistically meaningful estimate of retrieval recall, answer quality, latency, or supersession precision. No live GitHub, Neo4j, or Ollama benchmark was run. End-to-end latency is therefore not measured; unit tests complete in under one second on the local environment, which is not a representative service latency measurement.

Manual audit conclusions:

- Graph relationships materially add context in the retry fixture by discovering a related issue that direct text retrieval misses.
- Source URLs are taken from stored evidence and validated before being exposed by verification.
- The frontend uses real backend data only when `VITE_USE_MOCKS=false`; mock mode is explicit and labeled.
- GitHub Discussions are currently reported as unavailable because the implemented client uses REST and does not pretend that issue data are discussions.
