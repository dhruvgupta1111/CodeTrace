import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ArrowRight, GitCompare } from 'lucide-react';
import { Drawer, EmptyState, ErrorMessage, Loading, PageHeader, StatusBadge } from '../components/ui';
import { useAsync } from '../hooks/useAsync';
import { timelineService } from '../services';
import { decisions } from '../data/mock';
import { cx, fmtDate } from '../lib/utils';
import type { DecisionType, EvidenceStatus, TimelineEntry } from '../types';
import { useApp } from '../hooks/useApp';

const TYPE_LABEL: Record<DecisionType, string> = { original: 'Original decision', modified: 'Modified', superseded: 'Superseded', current: 'Current implementation' };
const TYPE_CLS: Record<DecisionType, string> = { original: 'text-cyan', modified: 'text-warn', superseded: 'text-bad', current: 'text-ok' };

function Diff({ text }: { text: string }) {
  return <pre className="overflow-x-auto rounded-md border border-line bg-bg p-2 text-xs">{text.split('\n').map((l, i) => <div key={i} className={l.startsWith('+') ? 'text-ok' : l.startsWith('-') ? 'text-bad' : ''}>{l}</div>)}</pre>;
}

export default function TimelinePage() {
  const { repo } = useApp();
  const { data, error, loading, reload } = useAsync(() => timelineService.list(repo.id), repo.id);
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState('');
  const [file, setFile] = useState('all');
  const [type, setType] = useState<'all' | DecisionType>('all');
  const [status, setStatus] = useState<'all' | EvidenceStatus>('all');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [cmp, setCmp] = useState<string[]>([]);
  const [showCmp, setShowCmp] = useState(false);

  const files = useMemo(() => Array.from(new Set((data ?? []).flatMap((t) => t.commit.files))), [data]);
  const list = useMemo(() => (data ?? []).filter((t) =>
    (!q || `${t.commit.message} ${t.commit.hash} ${t.commit.author}`.toLowerCase().includes(q.toLowerCase())) &&
    (file === 'all' || t.commit.files.includes(file)) && (type === 'all' || t.decisionType === type) &&
    (status === 'all' || t.evidenceStatus === status) && (!from || t.date >= from) && (!to || t.date <= to)), [data, q, file, type, status, from, to]);

  if (loading) return <Loading label="Loading timeline" />;
  if (error || !data) return <ErrorMessage message={error ?? 'No data'} onRetry={reload} />;
  if (!data.length) return <div className="mx-auto max-w-6xl space-y-4"><PageHeader title="Decision Timeline" desc={`${repo.fullName} · historical decisions from indexed evidence`} /><EmptyState title="No decisions indexed yet" desc="Synchronize this repository successfully before exploring decision history." /></div>;
  const openId = params.get('entry');
  const open = data.find((t) => t.id === openId);
  const pair = cmp.map((id) => data.find((t) => t.id === id)!).filter(Boolean);
  const toggleCmp = (id: string) => setCmp((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c.slice(-1), id]));
  const chain = data.filter((t) => ['t1', 't2', 't3'].includes(t.id));

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <PageHeader title="Decision Timeline" desc="How decisions evolved over time." demo={repo.isDemo ? 'Sample history' : undefined}
        actions={<button className="btn" disabled={cmp.length !== 2} onClick={() => setShowCmp(true)}><GitCompare size={14} />Compare selected ({cmp.length}/2)</button>} />

      {chain.length >= 3 && <section className="card p-4" aria-label="Retry policy evolution">
        <h2 className="mb-3 text-sm font-medium">Retry policy evolution</h2>
        <div className="flex flex-col items-stretch gap-2 md:flex-row md:items-center">
          {[chain[0], chain[1], chain[2]].map((t, i) => {
            const label = i === 2 ? 'Current implementation (pending verification)' : i === 0 ? 'Original decision' : 'Modified';
            return (
              <div key={t.id} className="flex flex-1 items-center gap-2">
                <button onClick={() => setParams({ entry: t.id })} className="flex-1 rounded-md border border-line p-3 text-left hover:border-accent/60">
                  <div className={cx('text-xs font-medium', i === 2 ? 'text-ok' : i === 0 ? 'text-cyan' : 'text-warn')}>{label}</div>
                  <div className="mt-1 text-sm">{decisions.find((d) => d.id === t.decisionId)?.title}</div><div className="text-xs text-muted">{fmtDate(t.date)}</div>
                  {i === 2 && <div className="mt-1 text-xs text-bad">Supersedes: Fixed retry limit (per PR #377)</div>}
                </button>
                {i < 2 && <ArrowRight size={14} className="hidden text-muted md:block" />}
              </div>
            );
          })}
        </div>
      </section>}

      <section className="card grid gap-2 p-3 sm:grid-cols-2 lg:grid-cols-6" aria-label="Filters">
        <input className="input lg:col-span-2" placeholder="Search commits..." aria-label="Search commits" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input" aria-label="File" value={file} onChange={(e) => setFile(e.target.value)}><option value="all">All files</option>{files.map((f) => <option key={f}>{f}</option>)}</select>
        <select className="input" aria-label="Decision type" value={type} onChange={(e) => setType(e.target.value as 'all')}><option value="all">All types</option>{Object.entries(TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        <select className="input" aria-label="Evidence status" value={status} onChange={(e) => setStatus(e.target.value as 'all')}><option value="all">Any evidence</option><option value="strong">Strong</option><option value="partial">Partial</option><option value="insufficient">Insufficient</option></select>
        <div className="flex gap-1"><input type="date" className="input" aria-label="From date" value={from} onChange={(e) => setFrom(e.target.value)} /><input type="date" className="input" aria-label="To date" value={to} onChange={(e) => setTo(e.target.value)} /></div>
      </section>

      {list.length === 0 ? <EmptyState title="No matching events" desc="Adjust or clear the filters." action={<button className="btn" onClick={() => { setQ(''); setFile('all'); setType('all'); setStatus('all'); setFrom(''); setTo(''); }}>Clear filters</button>} /> : (
        <ol className="relative space-y-3 border-l border-line pl-5">
          {list.map((t) => (
            <li key={t.id} className="relative">
              <span className="absolute -left-[26px] top-4 h-2.5 w-2.5 rounded-full border-2 border-bg bg-accent" />
              <div className="card p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <button className="text-left" onClick={() => setParams({ entry: t.id })}>
                    <div className="font-medium hover:underline">{t.commit.message}</div>
                    <div className="text-xs text-muted"><code className="text-cyan">{t.commit.hash}</code> · {t.commit.author} · {fmtDate(t.date)}</div>
                  </button>
                  <label className="flex items-center gap-1.5 text-xs text-muted"><input type="checkbox" checked={cmp.includes(t.id)} onChange={() => toggleCmp(t.id)} />Compare</label>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                  <span className={cx('font-medium', TYPE_CLS[t.decisionType])}>{TYPE_LABEL[t.decisionType]}</span><StatusBadge status={t.evidenceStatus} />
                  <span className="text-muted">Source: {t.evidenceSource}</span>
                </div>
                <div className="mt-1 text-xs text-muted">{t.relation}</div>
                <div className="mt-1 truncate text-xs text-muted">{t.commit.files.join(', ')}</div>
              </div>
            </li>
          ))}
        </ol>
      )}

      <Drawer open={!!open} onClose={() => setParams({})} title={open?.commit.message ?? ''}>
        {open && <EntryDetail t={open} />}
      </Drawer>
      <Drawer open={showCmp} onClose={() => setShowCmp(false)} title="Compare events">
        <div className="space-y-4">{pair.map((t) => <div key={t.id}><div className="mb-1 text-xs text-muted">{fmtDate(t.date)} · {TYPE_LABEL[t.decisionType]}</div><EntryDetail t={t} /></div>)}
          {pair.length === 2 && <p className="rounded-md bg-raised p-2 text-xs text-muted">{Math.abs((new Date(pair[0].date).getTime() - new Date(pair[1].date).getTime()) / 864e5).toFixed(0)} days apart · {pair[0].commit.files.some((f) => pair[1].commit.files.includes(f)) ? 'Touch shared files' : 'No shared files'}</p>}</div>
      </Drawer>
    </div>
  );
}

function EntryDetail({ t }: { t: TimelineEntry }) {
  const d = decisions.find((x) => x.id === t.decisionId);
  return (
    <div className="space-y-3 text-sm">
      <div className="text-xs text-muted"><code className="text-cyan">{t.commit.hash}</code> · {t.commit.author} · {fmtDate(t.date)}</div>
      <div><div className="mb-1 text-xs font-medium text-muted">Changes</div><Diff text={t.change} /></div>
      <div><div className="mb-1 text-xs font-medium text-muted">Associated decision</div>{d?.title ?? 'None'}<p className="text-xs text-muted">{d?.summary}</p></div>
      <div><div className="mb-1 text-xs font-medium text-muted">Evidence</div>{t.evidenceSource} <StatusBadge status={t.evidenceStatus} /></div>
      <div className="text-xs text-muted">{t.relation}</div>
    </div>
  );
}
