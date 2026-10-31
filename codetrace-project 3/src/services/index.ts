import { activity, answers, demoEvalResult, evidence, fallbackAnswer, files, graph, initialEval, repositories, seedHistory, timeline, decisions } from '../data/mock';
import { http, USE_MOCKS } from '../lib/http';
import type { ActivityEvent, Decision, Evidence, EvalRun, GraphData, QuestionAnswer, RepoFile, Repository, TimelineEntry } from '../types';

type BackendRepository = { id: string; full_name: string; default_branch?: string | null; language?: string | null; index_status: Repository['indexStatus']; last_indexed_at?: string | null; counts?: Record<string, number> | null };
type BackendEvidence = { evidence_id: string; source_type: Evidence['type']; title?: string | null; author?: string | null; observed_at?: string | null; source_url?: string | null; excerpt?: string | null; excerpt_origin?: 'original' | 'derived' | null; changed_files?: { path: string }[] };
type BackendDecision = { decision_id: string; statement: string; status: 'candidate' | 'confirmed' | 'superseded' | 'unresolved' | 'conflicting'; evidence_kind: 'explicit' | 'inferred'; evidence_ids: string[]; affected_paths: string[]; observed_at?: string | null; source_type: string; source_id: string };
type BackendGraph = { nodes: { id: string; label: string; node_type: string; metadata: Record<string, unknown>; source_ids: string[] }[]; edges: { id: string; source: string; target: string; relationship_type: string; evidence_ids: string[] }[] };
type BackendAnswer = { id: string; question: string; answer: string; status: QuestionAnswer['status']; evidence_ids: string[]; evidence_facts: string[]; interpretation?: string | null; conflicts: string[]; warnings: string[]; created_at: string; retrieval?: { hits: { evidence_id: string; source_url?: string | null; observed_at?: string | null; excerpt?: string | null; source_type: string }[] } | null };
type IngestionJob = { id: string; repository_id: string; status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'; progress?: number | null; stage?: string | null; error?: { code: string; message: string } | null };

const delay = <T,>(v: T, ms = 350): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));
const date = (value?: string | null) => value ?? '';

function mapRepository(r: BackendRepository): Repository {
  return { id: r.id, fullName: r.full_name, defaultBranch: r.default_branch ?? '—', language: r.language ?? 'Unknown', commitsAnalyzed: r.counts?.commits ?? 0, filesIndexed: r.counts?.files ?? 0, lastIndexed: date(r.last_indexed_at), indexStatus: r.index_status === 'running' ? 'indexing' : r.index_status, isDemo: false };
}
function mapEvidence(e: BackendEvidence): Evidence {
  return { id: e.evidence_id, title: e.title ?? e.evidence_id, type: e.source_type, date: date(e.observed_at), author: e.author ?? 'Unknown author', excerpt: e.excerpt ?? 'No excerpt available.', entities: (e.changed_files ?? []).map((f) => f.path), decisionIds: [], url: e.source_url ?? '', status: e.excerpt_origin === 'original' ? 'strong' : 'partial' };
}
function mapDecision(d: BackendDecision): Decision {
  const type: Decision['type'] = d.status === 'superseded' ? 'superseded' : d.evidence_kind === 'explicit' ? 'original' : 'modified';
  return { id: d.decision_id, title: d.statement, summary: d.statement, type, status: d.status === 'confirmed' ? 'strong' : d.status === 'conflicting' ? 'conflicting' : d.status === 'unresolved' ? 'insufficient' : 'partial', date: date(d.observed_at), files: d.affected_paths, supersedes: undefined, verified: d.status === 'confirmed' };
}
function mapGraph(g: BackendGraph): GraphData {
  return { nodes: g.nodes.map((n) => ({ id: n.id, label: n.label, type: (n.node_type === 'code_entity' ? 'function' : n.node_type) as GraphData['nodes'][number]['type'], description: String(n.metadata?.description ?? n.node_type), timestamp: typeof n.metadata?.observed_at === 'string' ? n.metadata.observed_at : undefined, url: typeof n.metadata?.source_url === 'string' ? n.metadata.source_url : '', evidence: n.source_ids })), edges: g.edges.map((e) => ({ id: e.id, source: e.source, target: e.target, type: e.relationship_type as GraphData['edges'][number]['type'], evidence: e.evidence_ids.join(', ') || 'No supporting evidence ID supplied' })) };
}
function mapAnswer(a: BackendAnswer): QuestionAnswer {
  const first = a.retrieval?.hits?.[0];
  return { id: a.id, question: a.question, answer: a.answer, status: a.status, timestamp: a.created_at, evidenceIds: a.evidence_ids, conflicts: a.conflicts, evidenceFacts: a.evidence_facts, interpretation: a.interpretation ?? undefined, warnings: a.warnings, excerpt: first?.excerpt ?? undefined, sourceUrl: first?.source_url ?? undefined, sources: (a.retrieval?.hits ?? []).map((hit) => ({ id: hit.evidence_id, type: hit.source_type, url: hit.source_url, excerpt: hit.excerpt, date: hit.observed_at })), relatedFiles: [], relatedDecisionIds: [], relatedCommits: [], history: a.evidence_ids.length ? `${a.evidence_ids.length} retrieved evidence source(s).` : 'No evidence was retrieved.', searched: a.evidence_ids.length ? undefined : ['Indexed commits, discussions, and documentation'], missing: a.evidence_ids.length ? undefined : ['A source that directly supports the requested explanation'] };
}

export const repositoryService = {
  list: async (): Promise<Repository[]> => USE_MOCKS ? delay(repositories, 100) : (await http<{ items: BackendRepository[] }>('/repositories')).items.map(mapRepository),
  create: async (remoteUrl: string, defaultBranch?: string): Promise<Repository> => USE_MOCKS ? repositories[0] : mapRepository(await http<BackendRepository>('/repositories', { method: 'POST', body: JSON.stringify({ remote_url: remoteUrl, default_branch: defaultBranch || undefined }) })),
  sync: async (repositoryId: string): Promise<IngestionJob> => USE_MOCKS ? ({ id: 'demo-job', repository_id: repositoryId, status: 'completed', progress: null }) : http<IngestionJob>(`/repositories/${encodeURIComponent(repositoryId)}/ingestion-jobs`, { method: 'POST' }),
  status: async (repositoryId: string): Promise<Repository> => USE_MOCKS ? repositories.find((r) => r.id === repositoryId) ?? repositories[0] : mapRepository(await http<BackendRepository>(`/repositories/${encodeURIComponent(repositoryId)}`)),
  activity: (): Promise<ActivityEvent[]> => USE_MOCKS ? delay(activity, 150) : Promise.resolve([]),
  decisions: async (repositoryId?: string): Promise<Decision[]> => USE_MOCKS ? delay(decisions, 100) : repositoryId ? (await http<{ items: BackendDecision[] }>(`/repositories/${encodeURIComponent(repositoryId)}/decisions`)).items.map(mapDecision) : [],
  files: (): Promise<RepoFile[]> => USE_MOCKS ? delay(files, 150) : Promise.resolve([]),
};

const keywords: [string[], number][] = [[['retry', 'three', '3', 'limit'], 0], [['revers', 'later', 'replaced'], 1], [['between', 'commits', 'changed'], 2], [['workaround', 'cache'], 3], [['evidence', 'supports', 'valid'], 4]];
export const questionService = {
  history: (): Promise<QuestionAnswer[]> => USE_MOCKS ? delay(seedHistory, 100) : Promise.resolve([]),
  ask: async (question: string, repositoryId?: string): Promise<QuestionAnswer> => {
    if (!USE_MOCKS) { if (!repositoryId) throw new Error('Connect a repository before asking a question.'); return mapAnswer(await http<BackendAnswer>(`/repositories/${encodeURIComponent(repositoryId)}/questions`, { method: 'POST', body: JSON.stringify({ question, entity_ids: [] }) })); }
    const q = question.toLowerCase();
    if (q.includes('fail-demo')) return new Promise((_, rej) => setTimeout(() => rej(new Error('Mock error: simulated service failure.')), 400));
    const hit = keywords.find(([ks]) => ks.some((k) => q.includes(k)));
    const exact = answers.find((a) => a.question.toLowerCase() === q.trim());
    const base = exact ?? (hit ? answers[hit[1]] : undefined);
    return delay(base ? { ...base, id: `qa-${Date.now()}`, question, timestamp: new Date().toISOString() } : fallbackAnswer(question), 900);
  },
};
export const graphService = { get: async (repositoryId?: string): Promise<GraphData> => USE_MOCKS ? delay(graph, 250) : repositoryId ? mapGraph(await http<BackendGraph>(`/repositories/${encodeURIComponent(repositoryId)}/graph?depth=2&limit=250`)) : { nodes: [], edges: [] } };
export const timelineService = { list: async (repositoryId?: string): Promise<TimelineEntry[]> => USE_MOCKS ? delay(timeline, 250) : (await repositoryService.decisions(repositoryId)).map((d) => ({ id: d.id, date: d.date, commit: { hash: d.id, message: d.title, author: 'Source metadata', date: d.date, files: d.files }, decisionId: d.id, decisionType: d.type, evidenceStatus: d.status, evidenceSource: d.verified ? 'Verified decision record' : 'Decision candidate', relation: d.verified ? 'Confirmed by stored evidence' : 'Relationship requires review', change: d.summary })) };
export const evidenceService = { list: async (repositoryId?: string): Promise<Evidence[]> => USE_MOCKS ? delay(evidence, 250) : repositoryId ? (await http<{ items: BackendEvidence[] }>(`/repositories/${encodeURIComponent(repositoryId)}/evidence`)).items.map(mapEvidence) : [] };
export const evaluationService = { initial: (): Promise<EvalRun> => delay(initialEval, 150), runDemo: (): Promise<EvalRun> => delay({ ...demoEvalResult, ranAt: new Date().toISOString() }, 1600) };
