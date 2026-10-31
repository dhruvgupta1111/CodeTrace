import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, FileCode2, Folder } from 'lucide-react';
import { CommitCard, EmptyState, ErrorMessage, Loading, PageHeader, StatusBadge } from '../components/ui';
import { useAsync } from '../hooks/useAsync';
import { repositoryService } from '../services';
import { evidence, decisions } from '../data/mock';
import { useApp } from '../hooks/useApp';
import { cx } from '../lib/utils';

const KW = /\b(class|def|return|for|in|if|try|except|raise|import|from|self|assert|range)\b/g;
function highlight(line: string) {
  const ci = line.indexOf('#');
  const code = ci >= 0 ? line.slice(0, ci) : line;
  const comment = ci >= 0 ? line.slice(ci) : '';
  const parts = code.split(KW);
  return <>{parts.map((p, i) => (i % 2 ? <span key={i} className="text-accent">{p}</span> : <span key={i}>{p}</span>))}<span className="text-muted">{comment}</span></>;
}

export default function Explorer() {
  const { repo } = useApp();
  const { data, error, loading, reload } = useAsync(repositoryService.files);
  const [sel, setSel] = useState<string | null>(null);
  const [q, setQ] = useState('');
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  useEffect(() => { if (data?.length && !sel) setSel(data[0].path); }, [data, sel]);

  const groups = useMemo(() => {
    const m = new Map<string, NonNullable<typeof data>>();
    (data ?? []).filter((f) => f.path.toLowerCase().includes(q.toLowerCase())).forEach((f) => {
      const dir = f.path.split('/').slice(0, -1).join('/');
      m.set(dir, [...(m.get(dir) ?? []), f]);
    });
    return Array.from(m.entries());
  }, [data, q]);

  if (loading) return <Loading label="Loading files" />;
  if (error || !data) return <ErrorMessage message={error ?? 'No data'} onRetry={reload} />;
  if (!data.length) return <div className="mx-auto max-w-6xl space-y-4"><PageHeader title="Repository Explorer" desc={`${repo.fullName} · ${repo.defaultBranch} · ${repo.language}`} /><EmptyState title="No files indexed yet" desc="Synchronize this repository to browse files and their history." /></div>;
  const file = data.find((f) => f.path === sel);

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title="Repository Explorer" desc={`${repo.fullName} · ${repo.defaultBranch} · ${repo.language}`} demo={repo.isDemo ? 'Sample files' : undefined} />
      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <section className="card p-3">
          <input className="input mb-2" placeholder="Search files" aria-label="Search files" value={q} onChange={(e) => setQ(e.target.value)} />
          {groups.length === 0 && <p className="p-2 text-xs text-muted">No files match.</p>}
          {groups.map(([dir, fs]) => (
            <div key={dir}>
              <button className="flex w-full items-center gap-1 py-1 text-xs text-muted" onClick={() => setCollapsed((c) => { const n = new Set(c); n.has(dir) ? n.delete(dir) : n.add(dir); return n; })}>
                {collapsed.has(dir) ? <ChevronRight size={12} /> : <ChevronDown size={12} />}<Folder size={12} />{dir}
              </button>
              {!collapsed.has(dir) && fs.map((f) => (
                <button key={f.path} onClick={() => setSel(f.path)} className={cx('ml-4 flex w-[calc(100%-1rem)] items-center justify-between rounded px-2 py-1 text-left text-sm', sel === f.path ? 'bg-accent/15 text-accent' : 'hover:bg-raised')}>
                  <span className="flex items-center gap-1.5 truncate"><FileCode2 size={13} />{f.path.split('/').pop()}</span>
                  {f.decisionCount > 0 && <span className="rounded-full bg-raised px-1.5 text-[10px] text-muted" title="Related decisions">{f.decisionCount}</span>}
                </button>
              ))}
            </div>
          ))}
        </section>

        {file ? (
          <div className="grid min-w-0 gap-4 xl:grid-cols-[1fr_280px]">
            <section className="card min-w-0">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2.5 text-xs"><code>{file.path}</code><span className="text-muted">{file.language} · modified {file.modified}</span></div>
              <pre className="overflow-x-auto p-4 text-xs leading-6">{file.content.split('\n').map((l, i) => <div key={i}><span className="mr-4 inline-block w-5 select-none text-right text-muted">{i + 1}</span>{highlight(l)}</div>)}</pre>
            </section>
            <div className="space-y-4">
              <section className="card p-3"><h3 className="mb-2 text-sm font-medium">Commit history</h3><div className="space-y-1.5">{file.commits.map((c) => <CommitCard key={c.hash} commit={c} compact />)}</div></section>
              <section className="card p-3"><h3 className="mb-2 text-sm font-medium">Related decisions</h3>
                {decisions.filter((d) => d.files.includes(file.path)).map((d) => <div key={d.id} className="mb-1.5 flex items-center justify-between gap-2 text-xs"><span>{d.title}</span><StatusBadge status={d.status} /></div>)}
                {file.decisionCount === 0 && <p className="text-xs text-muted">No decisions linked.</p>}</section>
              <section className="card p-3"><h3 className="mb-2 text-sm font-medium">Linked evidence</h3>
                {file.evidenceIds.length ? file.evidenceIds.map((id) => { const e = evidence.find((x) => x.id === id); return e && <div key={id} className="mb-1.5 text-xs">{e.title}</div>; }) : <p className="text-xs text-muted">No evidence linked.</p>}</section>
            </div>
          </div>
        ) : <EmptyState title="Select a file" desc="Choose a file to view its source and history." />}
      </div>
    </div>
  );
}
