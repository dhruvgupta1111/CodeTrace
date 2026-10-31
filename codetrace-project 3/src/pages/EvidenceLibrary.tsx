import { useMemo, useState } from 'react';
import { Drawer, EmptyState, ErrorMessage, EvidenceCard, Loading, PageHeader, SourceLink, StatusBadge } from '../components/ui';
import { useAsync } from '../hooks/useAsync';
import { evidenceService } from '../services';
import { decisions } from '../data/mock';
import type { Evidence, EvidenceStatus, EvidenceType } from '../types';
import { fmtDate } from '../lib/utils';
import { useApp } from '../hooks/useApp';

const TYPES: EvidenceType[] = ['commit', 'pull_request', 'issue', 'code_excerpt', 'documentation', 'decision_record'];

export default function EvidenceLibrary() {
  const { repo } = useApp();
  const { data, error, loading, reload } = useAsync(() => evidenceService.list(repo.id), repo.id);
  const [q, setQ] = useState('');
  const [type, setType] = useState<'all' | EvidenceType>('all');
  const [status, setStatus] = useState<'all' | EvidenceStatus>('all');
  const [open, setOpen] = useState<Evidence | null>(null);
  const list = useMemo(() => (data ?? []).filter((e) =>
    (type === 'all' || e.type === type) && (status === 'all' || e.status === status) &&
    (!q || `${e.title} ${e.excerpt} ${e.author} ${e.entities.join(' ')}`.toLowerCase().includes(q.toLowerCase()))), [data, q, type, status]);

  if (loading) return <Loading label="Loading evidence" />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;
  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <PageHeader title="Evidence Library" desc="Search the sources behind each decision." demo={repo.isDemo ? 'Sample evidence' : undefined} />
      <div className="card grid gap-2 p-3 sm:grid-cols-3">
        <input className="input" placeholder="Search evidence..." aria-label="Search evidence" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input" aria-label="Type" value={type} onChange={(e) => setType(e.target.value as 'all')}><option value="all">All types</option>{TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}</select>
        <select className="input" aria-label="Status" value={status} onChange={(e) => setStatus(e.target.value as 'all')}><option value="all">Any status</option><option value="strong">Strong</option><option value="partial">Partial</option><option value="insufficient">Insufficient</option></select>
      </div>
      <div className="text-xs text-muted">{list.length} of {data?.length} sample records</div>
      {list.length ? <div className="grid gap-3 md:grid-cols-2">{list.map((e) => <EvidenceCard key={e.id} ev={e} onOpen={setOpen} />)}</div>
        : <EmptyState title="No evidence found" desc="Try a different search or filter." action={<button className="btn" onClick={() => { setQ(''); setType('all'); setStatus('all'); }}>Clear filters</button>} />}
      <Drawer open={!!open} onClose={() => setOpen(null)} title={open?.title ?? ''}>
        {open && (
          <div className="space-y-3 text-sm">
            <StatusBadge status={open.status} />
            <div className="text-xs text-muted">{open.type.replace('_', ' ')} · {open.author} · {fmtDate(open.date)}</div>
            <p>{open.excerpt}</p>
            <div><div className="mb-1 text-xs font-medium text-muted">Related code entities</div>{open.entities.map((e) => <code key={e} className="mr-1 rounded bg-raised px-1.5 py-0.5 text-xs">{e}</code>)}</div>
            <div><div className="mb-1 text-xs font-medium text-muted">Related decisions</div>{open.decisionIds.length ? open.decisionIds.map((id) => <div key={id}>{decisions.find((d) => d.id === id)?.title}</div>) : <span className="text-xs text-muted">None linked</span>}</div>
            {open.url ? <SourceLink url={open.url} /> : <span className="text-xs text-muted">No source URL was supplied by the backend.</span>}
            {open.url && <p className="text-xs text-muted">Source URL is provided by the backend record.</p>}
          </div>
        )}
      </Drawer>
    </div>
  );
}
