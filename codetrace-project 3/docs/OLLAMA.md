# Ollama integration

The backend adapter in `backend/llm.py` calls only Ollama's `/api/chat` endpoint. It requests JSON output and validates the response against `CandidateAnswer` before returning it. It never starts Ollama and never downloads models.

The prompt puts system instructions in a separate message and wraps retrieved evidence as untrusted JSON records. The adapter checks that every returned evidence ID belongs to the supplied records. A non-`insufficient` answer with no evidence IDs is rejected. Model confidence is not used as proof.

Failures are mapped to stable codes: `ai_service_unavailable`, `ai_service_timeout`, `ai_model_unavailable`, `ai_malformed_output`, and `ai_ungrounded_answer`. The API turns these into safe frontend messages without exposing prompts, raw source content, stack traces, or tokens.

Operational metadata records only model name, evidence count, latency, and output size. It does not log the question, prompt, source excerpts, or model output.

For local use, install and run Ollama separately, pull a model explicitly, and set `CODETRACE_OLLAMA_MODEL` to that existing model. Live model behavior is not covered by the ordinary unit tests.
