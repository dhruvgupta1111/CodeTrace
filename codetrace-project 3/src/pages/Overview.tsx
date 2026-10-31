import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { Activity, BookOpen, Clock, FileSearch, FolderTree, GitCommit, Layers, MessageSquareText, Network, Replace, ArrowRight, RefreshCw, Settings } from 'lucide-react';
import { DemoBadge, EmptyState, ErrorMessage, Loading, MetricCard, StatusBadge } from '../components/ui';
import { RepositorySelector } from '../components/layout/RepositorySelector';
import { useApp } from '../hooks/useApp';
import { useAsync } from '../hooks/useAsync';
import { evidenceService, questionService, repositoryService } from '../services';
import { fmtDate, fmtDateTime } from '../lib/utils';

const quick = [
  { to: '/ask', title: 'Ask why this code exists', desc: 'Investigate a function or config.', icon: MessageSquareText },
  { to: '/graph', title: 'Explore decision graph', desc: 'See how entities connect.', icon: Network },
  { to: '/timeline', title: 'View decision history', desc: 'Follow changes over time.', icon: Clock },
  { to: '/evidence', title: 'Inspect evidence sources', desc: 'Browse commits, PRs, ADRs.', icon: BookOpen },
  { to: '/explorer', title: 'Browse repository files', desc: 'Explore indexed paths and changes.', icon: FolderTree },
  { to: '/evaluation', title: 'Evaluate answer quality', desc: 'Review retrieval and grounding.', icon: Activity },
  { to: '/settings', title: 'Manage workspace settings', desc: 'Appearance and API preferences.', icon: Settings },
];

export default function Overview() {
  const { repo, setRepo } = useApp();
  const [url, setUrl] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const nav = useNavigate();
  const act = useAsync(repositoryService.activity);
  const hist = useAsync(questionService.history);
  const ev = useAsync(() => evidenceService.list(repo.id), repo.id);
  const dec = useAsync(() => repositoryService.decisions(repo.id), repo.id);
  const hour = new Date().getHours();
  const greet = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  const connect = async () => {
    if (!url.trim()) return;
    setConnecting(true); setConnectError(null);
    try { const created = await repositoryService.create(url.trim()); setRepo(created); await repositoryService.sync(created.id); } catch (e) { setConnectError((e as Error).message); } finally { setConnecting(false); }
  };
  const sync = async () => {
    if (!repo.id || syncing) return;
    setSyncing(true); setConnectError(null);
    try { await repositoryService.sync(repo.id); const refreshed = await repositoryService.status(repo.id); setRepo(refreshed); }
    catch (e) { setConnectError((e as Error).message); }
    finally { setSyncing(false); }
  };
  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{greet}, Developer</h1>
          <p className="text-sm text-muted">Explore the decisions, trade-offs, and history behind your codebase.</p>
        </div>
        <div className="flex flex-wrap gap-2"><RepositorySelector large />{repo.id && <button className="btn" onClick={sync} disabled={syncing}><RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />{syncing ? 'Syncing…' : 'Sync now'}</button>}<button className="btn btn-primary" onClick={() => nav('/ask')}><MessageSquareText size={14} />Ask a Question</button></div>
      </div>

      <details className="card reveal-up group border-accent/30 p-5">
        <summary className="flex cursor-pointer list-none items-center justify-between font-medium"><span>{repo.id ? 'Connect another repository' : 'Connect a GitHub repository'}</span><span className="text-xs text-accent transition-transform group-open:rotate-45">+</span></summary>
        <div className="mt-3">
        <p className="mt-1 text-sm text-muted">Add a public GitHub repository to switch between codebases. CodeTrace reads history and linked evidence; it never executes repository code.</p>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row"><input className="input flex-1" placeholder="https://github.com/owner/repository" aria-label="GitHub repository URL" value={url} onChange={(e) => setUrl(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && connect()} /><button className="btn btn-primary" disabled={connecting || !url.trim()} onClick={connect}>{connecting ? 'Connecting…' : 'Connect repository'}</button></div>
        {connectError && <p className="mt-2 text-sm text-bad" role="alert">{connectError}</p>}
        </div>
      </details>
      <section className="card reveal-up p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2"><Layers size={16} className="text-accent" /><code className="text-sm font-medium">{repo.fullName}</code>{repo.isDemo && <DemoBadge text="Demo repository" />}</div>
          <span className="text-xs text-muted">{repo.lastIndexed ? `Last indexed ${fmtDateTime(repo.lastIndexed)}` : 'Not indexed yet'}</span>
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          {[['Default branch', repo.defaultBranch], ['Language', repo.language], ['Commits analyzed', repo.commitsAnalyzed.toLocaleString()], ['Files indexed', repo.filesIndexed.toLocaleString()]].map(([k, v]) => (
            <div key={k}><dt className="text-xs text-muted">{k}</dt><dd className="font-medium">{v}</dd></div>
          ))}
        </dl>
      </section>

      <section aria-label="Repository insights" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Link to="/timeline" className="block rounded-lg transition-transform hover:-translate-y-0.5"><MetricCard label="Decisions identified" value={dec.loading ? '…' : String(dec.data?.length ?? 0)} caption={repo.isDemo ? 'Sample decision records' : 'Candidates from indexed history'} icon={<Layers size={14} />} /></Link>
        <Link to="/evidence" className="block rounded-lg transition-transform hover:-translate-y-0.5"><MetricCard label="Evidence sources" value={ev.loading ? '…' : String(ev.data?.length ?? 0)} caption={repo.isDemo ? 'Illustrative demo sources' : 'Commits and connected sources'} icon={<BookOpen size={14} />} /></Link>
        <MetricCard label="Needs review" value={dec.loading ? '…' : String(dec.data?.filter((d) => d.status === 'insufficient' || d.status === 'conflicting').length ?? 0)} caption="Unresolved or conflicting history" icon={<Replace size={14} />} />
        <MetricCard label="Files indexed" value={String(repo.filesIndexed)} caption={repo.filesIndexed ? 'Ready to explore' : 'File content not indexed yet'} icon={<FileSearch size={14} />} />
      </section>

      <div className="grid gap-5 lg:grid-cols-5">
        <section className="card reveal-up p-4 lg:col-span-3">
          <h2 className="mb-3 font-medium">Recent activity</h2>
          {act.loading ? <Loading /> : act.error ? <ErrorMessage message={act.error} onRetry={act.reload} /> : act.data?.length ? (
            <ol className="relative space-y-4 border-l border-line pl-4">
              {act.data!.map((a) => (
                <li key={a.id} className="relative">
                  <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-panel bg-accent" />
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div><div className="text-sm font-medium">{a.title}</div><code className="text-xs text-muted">{a.file}</code></div>
                    <div className="flex items-center gap-3 text-xs text-muted">{fmtDate(a.date)}<Link className="inline-flex items-center gap-1 text-cyan hover:underline" to={`/timeline?entry=${a.entryId}`}>Inspect <ArrowRight size={11} /></Link></div>
                  </div>
                </li>
              ))}
            </ol>
          ) : <EmptyState title="No activity stream yet" desc="Sync the repository to populate recent history." />}
        </section>

        <section className="card reveal-up p-4 lg:col-span-2">
          <h2 className="mb-3 font-medium">Recent questions</h2>
          {hist.loading ? <Loading /> : hist.data?.length ? (
            <ul className="space-y-2">
              {hist.data!.map((q) => (
                <li key={q.id}><Link to={`/ask?q=${encodeURIComponent(q.id)}`} className="block rounded-md border border-line p-2.5 hover:border-accent/60">
                  <div className="text-sm">{q.question}</div>
                  <div className="mt-1.5 flex items-center justify-between"><StatusBadge status={q.status} /><span className="text-xs text-muted">{fmtDateTime(q.timestamp)}</span></div>
                </Link></li>
              ))}
            </ul>
          ) : <EmptyState title="No questions yet" desc="Ask a question to create a traceable answer record." action={<Link className="btn btn-primary mt-2" to="/ask">Ask a question</Link>} />}
        </section>
      </div>

      <section aria-label="Quick actions" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {quick.map((q, i) => (
          <Link key={q.to} to={q.to} style={{ animationDelay: `${i * 70}ms` }} className="card reveal-up group p-4 transition-all hover:-translate-y-0.5 hover:border-accent/60 hover:shadow-lg">
            <q.icon size={18} className="text-accent" /><div className="mt-2 text-sm font-medium">{q.title}</div><div className="text-xs text-muted">{q.desc}</div>
          </Link>
        ))}
      </section>
      {repo.isDemo && <p className="flex items-center gap-1 text-xs text-muted"><GitCommit size={12} />Demo mode is enabled. Set VITE_USE_MOCKS=false to use the backend.</p>}
    </div>
  );
}
