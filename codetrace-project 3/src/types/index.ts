/** Strength of an individual source; distinct from the status of an answer. */
export type EvidenceStatus = 'strong' | 'partial' | 'insufficient' | 'conflicting';
export type AnswerStatus = 'supported' | 'partially_supported' | 'insufficient_evidence' | 'conflicting_evidence';
export type EvidenceType = 'commit' | 'pull_request' | 'issue' | 'comment' | 'discussion' | 'code_excerpt' | 'documentation' | 'incident' | 'decision_record' | 'code_change';
export type NormalizedEvidenceType = 'commit' | 'pull_request' | 'issue' | 'comment' | 'discussion' | 'documentation' | 'incident' | 'decision_record' | 'code_change' | 'code_excerpt';

export interface NormalizedLineRange { start: number; end: number }
export interface NormalizedFileChange {
  path: string;
  previous_path?: string | null;
  status: 'added' | 'modified' | 'deleted' | 'renamed' | 'binary' | 'unknown';
  additions?: number | null;
  deletions?: number | null;
  line_ranges: NormalizedLineRange[];
}
export interface EvidenceInterpretation {
  text: string;
  kind: 'inferred' | 'machine_extracted';
  basis_evidence_ids: string[];
}
export interface EvidenceProvenance {
  source_type: NormalizedEvidenceType;
  source_id: string;
  repository_id: string;
  raw_source_ref: string;
  ingested_at: string;
  normalizer_version: string;
  parent_source_ids: string[];
}
export interface NormalizedEvidence {
  evidence_id: string;
  repository_id: string;
  source_type: NormalizedEvidenceType;
  source_id: string;
  title?: string | null;
  summary?: string | null;
  author?: string | null;
  observed_at?: string | null;
  source_url?: string | null;
  excerpt?: string | null;
  excerpt_origin?: 'original' | 'derived' | null;
  changed_files: NormalizedFileChange[];
  interpretations: EvidenceInterpretation[];
  provenance: EvidenceProvenance;
  content_hash: string;
}
export type DecisionType = 'original' | 'modified' | 'superseded' | 'current';

export interface Repository {
  id: string;
  fullName: string;
  defaultBranch: string;
  language: string;
  commitsAnalyzed: number;
  filesIndexed: number;
  lastIndexed: string;
  indexStatus: 'not_indexed' | 'pending' | 'running' | 'indexed' | 'indexing' | 'stale' | 'failed';
  isDemo?: boolean;
}

export interface Commit {
  hash: string;
  message: string;
  author: string;
  date: string;
  files: string[];
}

export interface Decision {
  id: string;
  title: string;
  summary: string;
  type: DecisionType;
  status: EvidenceStatus;
  date: string;
  files: string[];
  supersedes?: string;
  verified: boolean;
}

export interface Evidence {
  id: string;
  title: string;
  type: EvidenceType;
  date: string;
  author: string;
  excerpt: string;
  entities: string[];
  decisionIds: string[];
  url: string;
  status: EvidenceStatus;
}

export type GraphNodeType = 'repository' | 'file' | 'function' | 'code_entity' | 'configuration_key' | 'commit' | 'evidence' | 'decision' | 'decision_record' | 'code_change' | 'code_excerpt' | 'pull_request' | 'issue' | 'discussion' | 'comment' | 'documentation' | 'incident' | 'person';
export type GraphRelType = 'CONTAINS' | 'MODIFIED_BY' | 'REFERENCES' | 'DISCUSSED_IN' | 'SUPPORTED_BY' | 'AFFECTS' | 'EXPLAINS' | 'SUPERSEDES' | 'RELATED_TO';

export interface CodeEntity {
  id: string;
  kind: 'file' | 'function' | 'class' | 'module' | 'configuration';
  name: string;
  path?: string;
  lineStart?: number;
  lineEnd?: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: GraphNodeType;
  description: string;
  timestamp?: string;
  url: string;
  evidence: string[];
}
export interface GraphRelationship {
  id: string;
  source: string;
  target: string;
  type: GraphRelType;
  evidence: string;
}
export interface GraphData {
  nodes: GraphNode[];
  edges: GraphRelationship[];
}

export interface TimelineEntry {
  id: string;
  date: string;
  commit: Commit;
  decisionId: string;
  decisionType: DecisionType;
  evidenceStatus: EvidenceStatus;
  evidenceSource: string;
  relation: string;
  change: string;
}

export interface QuestionAnswer {
  id: string;
  question: string;
  answer: string;
  status: AnswerStatus;
  file?: string;
  commit?: Commit;
  pullRequest?: string;
  excerpt?: string;
  sourceUrl?: string;
  timestamp: string;
  relatedDecisionIds: string[];
  relatedFiles: string[];
  relatedCommits: Commit[];
  history: string;
  searched?: string[];
  missing?: string[];
  followUps?: string[];
  evidenceIds?: string[];
  conflicts?: string[];
  evidenceFacts?: string[];
  interpretation?: string;
  warnings?: string[];
  sources?: { id: string; type: string; url?: string | null; excerpt?: string | null; date?: string | null }[];
}

export interface RepoFile {
  path: string;
  language: string;
  modified: string;
  decisionCount: number;
  content: string;
  commits: Commit[];
  evidenceIds: string[];
}

export interface EvalCase {
  id: string;
  question: string;
  expected: string;
  retrieved: string;
  result: 'passed' | 'failed' | 'unsupported';
  supersession: boolean;
  status: string;
}
export interface EvalMetric {
  key: string;
  label: string;
  value: number;
  unit: string;
  caption: string;
}
export interface EvalRun {
  metrics: EvalMetric[];
  cases: EvalCase[];
  simulated: boolean;
  ranAt?: string;
}

export interface ActivityEvent {
  id: string;
  title: string;
  date: string;
  file: string;
  entryId: string;
}
