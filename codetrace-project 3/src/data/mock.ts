import type {
  ActivityEvent, Commit, Decision, Evidence, EvalRun, GraphData, QuestionAnswer, RepoFile, Repository, TimelineEntry,
} from '../types';

// All data in this file is fictional sample content. Not produced by any real analysis.

export const repositories: Repository[] = [
  { id: 'r1', fullName: 'acme/payment-service', defaultBranch: 'main', language: 'Python', commitsAnalyzed: 1284, filesIndexed: 346, lastIndexed: '2026-10-29T17:42:00+05:30', indexStatus: 'indexed', isDemo: true },
  { id: 'r2', fullName: 'acme/ledger-core', defaultBranch: 'main', language: 'Go', commitsAnalyzed: 902, filesIndexed: 214, lastIndexed: '2026-10-28T09:10:00+05:30', indexStatus: 'stale', isDemo: true },
  { id: 'r3', fullName: 'acme/web-checkout', defaultBranch: 'develop', language: 'TypeScript', commitsAnalyzed: 2210, filesIndexed: 689, lastIndexed: '2026-10-29T20:55:00+05:30', indexStatus: 'indexing', isDemo: true },
];

export const commits: Record<string, Commit> = {
  c1: { hash: 'a3f91c2', message: 'Add retry policy with fixed limit of 3 attempts', author: 'Maya Chen', date: '2025-02-11T10:20:00Z', files: ['src/config/retry_policy.py', 'src/services/payment_service.py'] },
  c2: { hash: 'b71e0d4', message: 'Retry: add exponential backoff and jitter', author: 'Luis Ortega', date: '2025-06-03T14:05:00Z', files: ['src/config/retry_policy.py'] },
  c3: { hash: 'd90c5aa', message: 'Make retry limit configurable via RETRY_MAX_ATTEMPTS', author: 'Priya Nair', date: '2025-09-19T08:40:00Z', files: ['src/config/retry_policy.py', 'tests/test_payment_service.py'] },
  c4: { hash: 'e12b7f8', message: 'Refactor payment validation into dedicated validators', author: 'Sam Okafor', date: '2025-10-02T12:00:00Z', files: ['src/services/payment_service.py'] },
  c5: { hash: 'f48a31e', message: 'Fix stale cache after refund by invalidating on webhook', author: 'Maya Chen', date: '2025-10-14T16:30:00Z', files: ['src/cache/invalidation.py'] },
  c6: { hash: '0c2d9b6', message: 'Auth middleware: reject expired tokens before rate limit', author: 'Dana Whitfield', date: '2025-10-21T11:15:00Z', files: ['src/middleware/auth.py'] },
};

export const decisions: Decision[] = [
  { id: 'd1', title: 'Fixed retry limit of three', summary: 'Retries bounded to 3 attempts to cap load on the upstream gateway during transient failures.', type: 'original', status: 'strong', date: '2025-02-11', files: ['src/config/retry_policy.py'], verified: true },
  { id: 'd2', title: 'Exponential backoff with jitter', summary: 'Retry timing changed to avoid synchronized retry storms. Limit remained fixed.', type: 'modified', status: 'partial', date: '2025-06-03', files: ['src/config/retry_policy.py'], supersedes: undefined, verified: false },
  { id: 'd3', title: 'Configurable retry limit', summary: 'Limit moved to an environment variable; default remains 3. Appears to replace the fixed constant.', type: 'current', status: 'partial', date: '2025-09-19', files: ['src/config/retry_policy.py'], supersedes: 'd1', verified: false },
  { id: 'd4', title: 'Dedicated payment validators', summary: 'Validation split out of the service class for testability.', type: 'original', status: 'strong', date: '2025-10-02', files: ['src/services/payment_service.py'], verified: true },
  { id: 'd5', title: 'Webhook-driven cache invalidation', summary: 'Cache invalidated on refund webhooks instead of TTL only.', type: 'original', status: 'partial', date: '2025-10-14', files: ['src/cache/invalidation.py'], verified: false },
];

export const timeline: TimelineEntry[] = [
  { id: 't1', date: '2025-02-11', commit: commits.c1, decisionId: 'd1', decisionType: 'original', evidenceStatus: 'strong', evidenceSource: 'PR #214', relation: 'Original decision', change: '-MAX_RETRIES = None\n+MAX_RETRIES = 3' },
  { id: 't2', date: '2025-06-03', commit: commits.c2, decisionId: 'd2', decisionType: 'modified', evidenceStatus: 'partial', evidenceSource: 'Issue #301', relation: 'Modified d1 (timing only)', change: '+def backoff(attempt):\n+    return min(2 ** attempt, 30) + jitter()' },
  { id: 't3', date: '2025-09-19', commit: commits.c3, decisionId: 'd3', decisionType: 'superseded', evidenceStatus: 'partial', evidenceSource: 'PR #377', relation: 'Superseded the fixed limit (d1); current implementation pending verification', change: '-MAX_RETRIES = 3\n+MAX_RETRIES = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))' },
  { id: 't4', date: '2025-10-02', commit: commits.c4, decisionId: 'd4', decisionType: 'original', evidenceStatus: 'strong', evidenceSource: 'PR #389', relation: 'Original decision', change: '+class AmountValidator: ...\n+class CurrencyValidator: ...' },
  { id: 't5', date: '2025-10-14', commit: commits.c5, decisionId: 'd5', decisionType: 'original', evidenceStatus: 'partial', evidenceSource: 'Incident INC-58', relation: 'Original decision', change: '+def on_refund_webhook(event):\n+    cache.invalidate(event.payment_id)' },
  { id: 't6', date: '2025-10-21', commit: commits.c6, decisionId: 'd4', decisionType: 'modified', evidenceStatus: 'insufficient', evidenceSource: 'None found', relation: 'Unrelated to prior decisions', change: '+if token.expired:\n+    raise Unauthorized()' },
];

export const evidence: Evidence[] = [
  { id: 'e1', title: 'PR #214: Introduce retry policy', type: 'pull_request', date: '2025-02-11', author: 'Maya Chen', excerpt: 'Gateway rate limits us at 50 rps. Unbounded retries caused an outage; cap at 3.', entities: ['retry_policy.py', 'MAX_RETRIES'], decisionIds: ['d1'], url: 'https://example.com/acme/payment-service/pull/214', status: 'strong' },
  { id: 'e2', title: 'Commit a3f91c2', type: 'commit', date: '2025-02-11', author: 'Maya Chen', excerpt: 'Add retry policy with fixed limit of 3 attempts.', entities: ['retry_policy.py'], decisionIds: ['d1'], url: 'https://example.com/acme/payment-service/commit/a3f91c2', status: 'strong' },
  { id: 'e3', title: 'Issue #301: Retry storms during gateway blips', type: 'issue', date: '2025-05-28', author: 'Luis Ortega', excerpt: 'All workers retry at the same moment. Consider jitter.', entities: ['backoff'], decisionIds: ['d2'], url: 'https://example.com/acme/payment-service/issues/301', status: 'partial' },
  { id: 'e4', title: 'PR #377: Configurable retry limit', type: 'pull_request', date: '2025-09-19', author: 'Priya Nair', excerpt: 'Ops wants to tune attempts per environment. Default stays at 3.', entities: ['MAX_RETRIES', 'RETRY_MAX_ATTEMPTS'], decisionIds: ['d3'], url: 'https://example.com/acme/payment-service/pull/377', status: 'partial' },
  { id: 'e5', title: 'ADR-007: Retry and idempotency', type: 'decision_record', date: '2025-02-20', author: 'Architecture Guild', excerpt: 'Retries are only safe with idempotency keys. Bound attempts to protect upstream.', entities: ['PaymentService.charge'], decisionIds: ['d1'], url: 'https://example.com/acme/payment-service/docs/adr-007', status: 'strong' },
  { id: 'e6', title: 'docs/runbook.md: Retry tuning', type: 'documentation', date: '2025-09-25', author: 'Priya Nair', excerpt: 'Set RETRY_MAX_ATTEMPTS only after consulting the gateway team.', entities: ['RETRY_MAX_ATTEMPTS'], decisionIds: ['d3'], url: 'https://example.com/acme/payment-service/docs/runbook', status: 'partial' },
  { id: 'e7', title: 'Excerpt: invalidation.py#L12-L24', type: 'code_excerpt', date: '2025-10-14', author: 'Maya Chen', excerpt: 'def on_refund_webhook(event): cache.invalidate(event.payment_id)', entities: ['on_refund_webhook'], decisionIds: ['d5'], url: 'https://example.com/acme/payment-service/blob/main/src/cache/invalidation.py#L12', status: 'partial' },
  { id: 'e8', title: 'Issue #392: Auth change rationale unclear', type: 'issue', date: '2025-10-22', author: 'Dana Whitfield', excerpt: 'No linked discussion explains the reordering of middleware checks.', entities: ['AuthMiddleware'], decisionIds: [], url: 'https://example.com/acme/payment-service/issues/392', status: 'insufficient' },
];

export const graph: GraphData = {
  nodes: [
    { id: 'n1', label: 'retry_policy.py', type: 'file', description: 'Defines retry limits and backoff.', url: 'https://example.com/blob/retry_policy.py', evidence: ['e1', 'e4'] },
    { id: 'n2', label: 'payment_service.py', type: 'file', description: 'Core charge and refund logic.', url: 'https://example.com/blob/payment_service.py', evidence: ['e5'] },
    { id: 'n3', label: 'invalidation.py', type: 'file', description: 'Cache invalidation hooks.', url: 'https://example.com/blob/invalidation.py', evidence: ['e7'] },
    { id: 'n4', label: 'with_retry()', type: 'function', description: 'Wraps gateway calls with retries.', url: 'https://example.com/blob/retry_policy.py#L20', evidence: ['e2'] },
    { id: 'n5', label: 'PaymentService.charge', type: 'function', description: 'Charges a card via the gateway.', url: 'https://example.com/blob/payment_service.py#L55', evidence: ['e5'] },
    { id: 'n6', label: 'a3f91c2', type: 'commit', description: 'Add retry policy with fixed limit.', timestamp: '2025-02-11', url: 'https://example.com/commit/a3f91c2', evidence: ['e2'] },
    { id: 'n7', label: 'd90c5aa', type: 'commit', description: 'Make retry limit configurable.', timestamp: '2025-09-19', url: 'https://example.com/commit/d90c5aa', evidence: ['e4'] },
    { id: 'n8', label: 'Fixed retry limit', type: 'decision', description: 'Retries bounded to 3.', timestamp: '2025-02-11', url: 'https://example.com/adr/007', evidence: ['e1', 'e5'] },
    { id: 'n9', label: 'Configurable limit', type: 'decision', description: 'Limit from env var, default 3.', timestamp: '2025-09-19', url: 'https://example.com/pull/377', evidence: ['e4', 'e6'] },
    { id: 'n10', label: 'PR #214', type: 'pull_request', description: 'Introduce retry policy.', timestamp: '2025-02-11', url: 'https://example.com/pull/214', evidence: ['e1'] },
    { id: 'n11', label: 'PR #377', type: 'pull_request', description: 'Configurable retry limit.', timestamp: '2025-09-19', url: 'https://example.com/pull/377', evidence: ['e4'] },
    { id: 'n12', label: 'Issue #301', type: 'issue', description: 'Retry storms during gateway blips.', timestamp: '2025-05-28', url: 'https://example.com/issues/301', evidence: ['e3'] },
    { id: 'n13', label: 'INC-58 stale refunds', type: 'incident', description: 'Refunded payments showed as charged.', timestamp: '2025-10-12', url: 'https://example.com/incidents/58', evidence: ['e7'] },
    { id: 'n14', label: 'Webhook invalidation', type: 'decision', description: 'Invalidate cache on refund webhooks.', timestamp: '2025-10-14', url: 'https://example.com/pull/395', evidence: ['e7'] },
    { id: 'n15', label: 'f48a31e', type: 'commit', description: 'Fix stale cache after refund.', timestamp: '2025-10-14', url: 'https://example.com/commit/f48a31e', evidence: ['e7'] },
  ],
  edges: [
    { id: 'g1', source: 'n1', target: 'n6', type: 'MODIFIED_BY', evidence: 'Commit a3f91c2 created the file.' },
    { id: 'g2', source: 'n1', target: 'n7', type: 'MODIFIED_BY', evidence: 'Commit d90c5aa changed MAX_RETRIES.' },
    { id: 'g3', source: 'n8', target: 'n4', type: 'EXPLAINS', evidence: 'ADR-007 describes with_retry bounds.' },
    { id: 'g4', source: 'n8', target: 'n10', type: 'DISCUSSED_IN', evidence: 'PR #214 description.' },
    { id: 'g5', source: 'n9', target: 'n11', type: 'DISCUSSED_IN', evidence: 'PR #377 description.' },
    { id: 'g6', source: 'n9', target: 'n8', type: 'SUPERSEDES', evidence: 'PR #377 replaces the constant; ADR not yet updated (partial).' },
    { id: 'g7', source: 'n12', target: 'n4', type: 'RELATED_TO', evidence: 'Issue references with_retry timing.' },
    { id: 'g8', source: 'n4', target: 'n5', type: 'RELATED_TO', evidence: 'charge() calls with_retry().' },
    { id: 'g9', source: 'n2', target: 'n5', type: 'RELATED_TO', evidence: 'Defined in payment_service.py.' },
    { id: 'g10', source: 'n6', target: 'n10', type: 'RELATED_TO', evidence: 'Commit belongs to PR #214.' },
    { id: 'g11', source: 'n7', target: 'n11', type: 'RELATED_TO', evidence: 'Commit belongs to PR #377.' },
    { id: 'g12', source: 'n13', target: 'n14', type: 'DISCUSSED_IN', evidence: 'Incident postmortem proposed the change.' },
    { id: 'g13', source: 'n14', target: 'n3', type: 'EXPLAINS', evidence: 'Decision explains the webhook hook.' },
    { id: 'g14', source: 'n3', target: 'n15', type: 'MODIFIED_BY', evidence: 'Commit f48a31e.' },
    { id: 'g15', source: 'n13', target: 'n5', type: 'RELATED_TO', evidence: 'Refund path in charge/refund service.' },
  ],
};

const retryCommits = [commits.c1, commits.c2, commits.c3];

export const answers: QuestionAnswer[] = [
  {
    id: 'qa1', question: 'Why is the retry limit set to three?',
    answer: 'The retry limit was configured to bound repeated requests during transient failures. A later change may have adjusted the policy to reduce unnecessary load. Review the linked historical evidence before treating this as the current decision.',
    status: 'partially_supported', file: 'src/config/retry_policy.py', commit: commits.c1, pullRequest: 'PR #214: Introduce retry policy',
    excerpt: 'MAX_RETRIES = 3  # bound load on gateway (50 rps limit)', sourceUrl: 'https://example.com/acme/payment-service/pull/214',
    timestamp: '2026-10-29T21:00:00+05:30', relatedDecisionIds: ['d1', 'd3'], relatedFiles: ['src/config/retry_policy.py', 'src/services/payment_service.py'],
    relatedCommits: retryCommits, history: 'Fixed limit (Feb) → backoff added (Jun) → limit made configurable (Sep, pending verification).',
  },
  {
    id: 'qa2', question: 'Was this decision later reversed?',
    answer: 'The fixed limit appears to have been replaced by a configurable limit whose default is still three. Evidence is partial: PR #377 describes the change but the original ADR has not been updated.',
    status: 'partially_supported', file: 'src/config/retry_policy.py', commit: commits.c3, pullRequest: 'PR #377: Configurable retry limit',
    excerpt: 'MAX_RETRIES = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))', sourceUrl: 'https://example.com/acme/payment-service/pull/377',
    timestamp: '2026-10-29T20:40:00+05:30', relatedDecisionIds: ['d1', 'd3'], relatedFiles: ['src/config/retry_policy.py'],
    relatedCommits: [commits.c3, commits.c1], history: 'd3 supersedes d1 per PR #377; verification pending.',
  },
  {
    id: 'qa3', question: 'What changed between these two commits?',
    answer: 'Between a3f91c2 and d90c5aa the retry policy gained backoff with jitter and its limit became environment-configurable. Both changes are directly visible in the diffs.',
    status: 'supported', file: 'src/config/retry_policy.py', commit: commits.c3, pullRequest: 'PR #377: Configurable retry limit',
    excerpt: '+def backoff(attempt): ...', sourceUrl: 'https://example.com/acme/payment-service/compare/a3f91c2...d90c5aa',
    timestamp: '2026-10-28T10:00:00+05:30', relatedDecisionIds: ['d2', 'd3'], relatedFiles: ['src/config/retry_policy.py', 'tests/test_payment_service.py'],
    relatedCommits: retryCommits, history: 'Two commits touched the policy between these points.',
  },
  {
    id: 'qa4', question: 'Why was this workaround introduced?',
    answer: 'The webhook-based cache invalidation was introduced after incident INC-58, where refunded payments displayed as charged. The commit message and incident link support this, though no ADR exists.',
    status: 'partially_supported', file: 'src/cache/invalidation.py', commit: commits.c5, pullRequest: 'PR #395: Invalidate on refund webhook',
    excerpt: 'cache.invalidate(event.payment_id)', sourceUrl: 'https://example.com/acme/payment-service/incidents/58',
    timestamp: '2026-10-27T15:00:00+05:30', relatedDecisionIds: ['d5'], relatedFiles: ['src/cache/invalidation.py'],
    relatedCommits: [commits.c5], history: 'Introduced Oct 14 after incident; not modified since.',
  },
  {
    id: 'qa5', question: 'What evidence supports this implementation?',
    answer: 'Payment validation was split into dedicated validators. PR #389 and the commit message explicitly state the testability goal.',
    status: 'supported', file: 'src/services/payment_service.py', commit: commits.c4, pullRequest: 'PR #389: Extract validators',
    excerpt: 'class AmountValidator: ...', sourceUrl: 'https://example.com/acme/payment-service/pull/389',
    timestamp: '2026-10-26T12:00:00+05:30', relatedDecisionIds: ['d4'], relatedFiles: ['src/services/payment_service.py'],
    relatedCommits: [commits.c4], history: 'Single refactor, linked to PR #389.',
  },
];

export const fallbackAnswer = (question: string): QuestionAnswer => ({
  id: `qa-${Date.now()}`, question,
  answer: "I couldn't find sufficient evidence in the indexed repository to establish why this decision was made.",
  status: 'insufficient_evidence', timestamp: new Date().toISOString(), relatedDecisionIds: [], relatedFiles: [], relatedCommits: [],
  history: 'No decision history found for this question.',
  searched: ['Commit messages (1,284)', 'Pull request descriptions', 'Linked issues', 'ADR documents in docs/'],
  missing: ['Commit or PR that explicitly states the rationale', 'Linked issue or incident', 'Decision record'],
  followUps: ['Rephrase with a specific file or function name', 'Ask the original author or reviewers', 'Add an ADR once the reason is confirmed'],
});

export const seedHistory: QuestionAnswer[] = answers.slice(0, 5);

export const activity: ActivityEvent[] = [
  { id: 'a1', title: 'Retry policy updated', date: '2025-09-19T08:40:00Z', file: 'src/config/retry_policy.py', entryId: 't3' },
  { id: 'a2', title: 'Payment validation refactored', date: '2025-10-02T12:00:00Z', file: 'src/services/payment_service.py', entryId: 't4' },
  { id: 'a3', title: 'Cache invalidation logic changed', date: '2025-10-14T16:30:00Z', file: 'src/cache/invalidation.py', entryId: 't5' },
  { id: 'a4', title: 'Authentication middleware modified', date: '2025-10-21T11:15:00Z', file: 'src/middleware/auth.py', entryId: 't6' },
];

export const files: RepoFile[] = [
  { path: 'src/services/payment_service.py', language: 'Python', modified: '2025-10-02', decisionCount: 1, evidenceIds: ['e5'], commits: [commits.c4, commits.c1],
    content: `class PaymentService:\n    def __init__(self, gateway, validators):\n        self.gateway = gateway\n        self.validators = validators\n\n    def charge(self, payment):\n        for v in self.validators:\n            v.validate(payment)\n        return with_retry(self.gateway.charge)(payment)\n\n    def refund(self, payment_id):\n        return self.gateway.refund(payment_id)\n` },
  { path: 'src/middleware/auth.py', language: 'Python', modified: '2025-10-21', decisionCount: 0, evidenceIds: ['e8'], commits: [commits.c6],
    content: `class AuthMiddleware:\n    def __call__(self, request):\n        token = parse(request)\n        if token.expired:\n            raise Unauthorized()\n        rate_limit(request)\n        return self.next(request)\n` },
  { path: 'src/config/retry_policy.py', language: 'Python', modified: '2025-09-19', decisionCount: 3, evidenceIds: ['e1', 'e3', 'e4', 'e5', 'e6'], commits: retryCommits,
    content: `import os\n\n# Bounded to protect upstream gateway (see ADR-007)\nMAX_RETRIES = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))\n\ndef backoff(attempt):\n    return min(2 ** attempt, 30) + jitter()\n\ndef with_retry(fn):\n    def wrapper(*a, **kw):\n        for attempt in range(MAX_RETRIES):\n            try:\n                return fn(*a, **kw)\n            except TransientError:\n                sleep(backoff(attempt))\n        raise RetryExhausted()\n    return wrapper\n` },
  { path: 'src/cache/invalidation.py', language: 'Python', modified: '2025-10-14', decisionCount: 1, evidenceIds: ['e7'], commits: [commits.c5],
    content: `def on_refund_webhook(event):\n    # Workaround for INC-58: TTL alone left stale charged status\n    cache.invalidate(event.payment_id)\n` },
  { path: 'tests/test_payment_service.py', language: 'Python', modified: '2025-09-19', decisionCount: 0, evidenceIds: [], commits: [commits.c3],
    content: `def test_retry_limit_from_env(monkeypatch):\n    monkeypatch.setenv("RETRY_MAX_ATTEMPTS", "5")\n    assert load_policy().max_retries == 5\n` },
];

const baseCases = [
  { id: 'ec1', question: 'Why is the retry limit three?', expected: 'PR #214, ADR-007', retrieved: 'PR #214, ADR-007', result: 'passed', supersession: false },
  { id: 'ec2', question: 'Was the fixed retry limit replaced?', expected: 'PR #377', retrieved: 'PR #377', result: 'passed', supersession: true },
  { id: 'ec3', question: 'Why was jitter added?', expected: 'Issue #301', retrieved: 'Commit b71e0d4', result: 'failed', supersession: false },
  { id: 'ec4', question: 'Why does auth reject expired tokens first?', expected: 'No evidence', retrieved: 'No evidence', result: 'unsupported', supersession: false },
  { id: 'ec5', question: 'Is ADR-007 still current?', expected: 'PR #377', retrieved: 'ADR-007 only', result: 'failed', supersession: true },
  { id: 'ec6', question: 'Why was cache invalidation added?', expected: 'INC-58', retrieved: 'INC-58', result: 'passed', supersession: false },
] as const;

export const initialEval: EvalRun = {
  simulated: false,
  metrics: [
    { key: 'ret', label: 'Evidence retrieval success', value: 78, unit: '%', caption: 'Demo value' },
    { key: 'cit', label: 'Citation correctness', value: 84, unit: '%', caption: 'Demo value' },
    { key: 'sup', label: 'Supersession accuracy', value: 66, unit: '%', caption: 'Demo value' },
    { key: 'uns', label: 'Unsupported-question handling', value: 92, unit: '%', caption: 'Demo value' },
    { key: 'lat', label: 'Average answer latency', value: 1.8, unit: 's', caption: 'Demo value' },
  ],
  cases: baseCases.map((c) => ({ ...c, status: c.result === 'passed' ? 'Evidence matched' : c.result === 'failed' ? 'Mismatch' : 'Correctly declined' })),
};

export const demoEvalResult: EvalRun = {
  simulated: true,
  metrics: [
    { key: 'ret', label: 'Evidence retrieval success', value: 83, unit: '%', caption: 'Simulated locally' },
    { key: 'cit', label: 'Citation correctness', value: 88, unit: '%', caption: 'Simulated locally' },
    { key: 'sup', label: 'Supersession accuracy', value: 75, unit: '%', caption: 'Simulated locally' },
    { key: 'uns', label: 'Unsupported-question handling', value: 95, unit: '%', caption: 'Simulated locally' },
    { key: 'lat', label: 'Average answer latency', value: 1.5, unit: 's', caption: 'Simulated locally' },
  ],
  cases: baseCases.map((c) => {
    const flip = c.id === 'ec3' || c.id === 'ec5';
    return { ...c, retrieved: flip ? c.expected : c.retrieved, result: flip ? 'passed' : c.result, status: c.result === 'unsupported' ? 'Correctly declined' : 'Evidence matched (mock)' };
  }),
};
