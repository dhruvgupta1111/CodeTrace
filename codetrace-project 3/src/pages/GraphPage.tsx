import { useRef, useState } from 'react';
import { Eye, EyeOff, Maximize, RotateCcw, Search, ZoomIn, ZoomOut } from 'lucide-react';
import { GraphCanvas, NODE_STYLE, type GraphHandle, type Selection } from '../components/graph/GraphCanvas';
import { GraphDetails } from '../components/graph/GraphDetails';
import { EmptyState, ErrorMessage, Loading, PageHeader } from '../components/ui';
import { useAsync } from '../hooks/useAsync';
import { graphService } from '../services';
import type { GraphNodeType, GraphRelType } from '../types';
import { useApp } from '../hooks/useApp';

const REL: GraphRelType[] = ['CONTAINS', 'MODIFIED_BY', 'REFERENCES', 'DISCUSSED_IN', 'SUPPORTED_BY', 'AFFECTS', 'SUPERSEDES', 'RELATED_TO'];
const NODE_TYPES = Object.keys(NODE_STYLE) as GraphNodeType[];

function toggle<T>(s: Set<T>, v: T) { const n = new Set(s); n.has(v) ? n.delete(v) : n.add(v); return n; }

export default function GraphPage() {
  const { repo } = useApp();
  const { data, error, loading, reload } = useAsync(() => graphService.get(repo.id), repo.id);
  const [nodeTypes, setNodeTypes] = useState(new Set<GraphNodeType>(NODE_TYPES));
  const [relTypes, setRelTypes] = useState(new Set<GraphRelType>(REL));
  const [labels, setLabels] = useState(true);
  const [query, setQuery] = useState('');
  const [sel, setSel] = useState<Selection>(null);
  const handle = useRef<GraphHandle>(null);

  if (loading) return <Loading label="Loading graph" />;
  if (error || !data) return <ErrorMessage message={error ?? 'No data'} onRetry={reload} />;
  if (!data.nodes.length) return <div className="mx-auto max-w-6xl space-y-4"><PageHeader title="Decision Graph" desc="Relationships from indexed repository evidence." /><EmptyState title="No graph data yet" desc="Connect and synchronize a repository before exploring its relationships." /></div>;
  const node = sel?.kind === 'node' ? data.nodes.find((n) => n.id === sel.id) : undefined;
  const edge = sel?.kind === 'edge' ? data.edges.find((e) => e.id === sel.id) : undefined;

  return (
    <div className="mx-auto flex h-full max-w-7xl flex-col">
      <PageHeader title="Decision Graph" desc="Relationships between files, commits, decisions, PRs, issues, and incidents." demo={repo.isDemo ? 'Sample graph data' : undefined} />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative"><Search size={13} className="absolute left-2.5 top-2.5 text-muted" /><input className="input !pl-8 sm:w-56" placeholder="Search nodes" aria-label="Search nodes" value={query} onChange={(e) => setQuery(e.target.value)} /></div>
        <div className="flex gap-1">
          <button className="btn !p-1.5" aria-label="Zoom in" onClick={() => handle.current?.zoom(1.3)}><ZoomIn size={14} /></button>
          <button className="btn !p-1.5" aria-label="Zoom out" onClick={() => handle.current?.zoom(0.77)}><ZoomOut size={14} /></button>
          <button className="btn" onClick={() => handle.current?.fit()}><Maximize size={13} />Fit</button>
          <button className="btn" onClick={() => { handle.current?.reset(); setQuery(''); setNodeTypes(new Set(NODE_TYPES)); setRelTypes(new Set(REL)); }}><RotateCcw size={13} />Reset</button>
          <button className="btn" onClick={() => setLabels(!labels)} aria-pressed={labels}>{labels ? <EyeOff size={13} /> : <Eye size={13} />}Labels</button>
        </div>
      </div>
      <div className="mb-3 space-y-2 text-xs">
        <div className="flex flex-wrap items-center gap-1.5"><span className="w-20 text-muted">Node types</span>
          {NODE_TYPES.map((t) => <button key={t} aria-pressed={nodeTypes.has(t)} onClick={() => setNodeTypes(toggle(nodeTypes, t))} className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 ${nodeTypes.has(t) ? 'border-line text-fg' : 'border-line/50 text-muted opacity-50'}`}><span className="h-2 w-2 rounded-full" style={{ background: NODE_STYLE[t].color }} />{NODE_STYLE[t].label}</button>)}
        </div>
        <div className="flex flex-wrap items-center gap-1.5"><span className="w-20 text-muted">Relations</span>
          {REL.map((t) => <button key={t} aria-pressed={relTypes.has(t)} onClick={() => setRelTypes(toggle(relTypes, t))} className={`rounded-full border px-2 py-0.5 font-mono ${relTypes.has(t) ? 'border-cyan/50 text-cyan' : 'border-line/50 text-muted opacity-50'}`}>{t}</button>)}
        </div>
      </div>
      <div className="grid min-h-[480px] flex-1 gap-4 lg:grid-cols-[1fr_300px]">
        <div className="card relative overflow-hidden"><GraphCanvas ref={handle} data={data} nodeTypes={nodeTypes} relTypes={relTypes} showLabels={labels} query={query} selection={sel} onSelect={setSel} />
          <span className="absolute bottom-2 left-2 rounded bg-raised px-2 py-0.5 text-[11px] text-muted">Click a node or edge · scroll to zoom</span></div>
        {sel ? <GraphDetails data={data} node={node} edge={edge} onClose={() => setSel(null)} onSelectNode={(id) => setSel({ kind: 'node', id })} />
          : <div className="card p-4 text-sm text-muted">Select a node or relationship to see details and supporting evidence.</div>}
      </div>
    </div>
  );
}
