import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight, History, MessageSquareText } from 'lucide-react';
import { AnswerPanel } from '../components/evidence/AnswerPanel';
import { QuestionInput, SuggestedQuestions } from '../components/evidence/QuestionInput';
import { CommitCard, EmptyState, ErrorMessage, Loading, PageHeader, StatusBadge } from '../components/ui';
import { questionService } from '../services';
import { fmtDateTime } from '../lib/utils';
import type { QuestionAnswer } from '../types';
import { useApp } from '../hooks/useApp';

export default function Ask() {
  const [params] = useSearchParams();
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [current, setCurrent] = useState<QuestionAnswer | null>(null);
  const [history, setHistory] = useState<QuestionAnswer[]>([]);
  const [showHistory, setShowHistory] = useState(true);
  const { repo } = useApp();

  useEffect(() => {
    questionService.history().then((h) => {
      setHistory(h);
      const id = params.get('q');
      const hit = h.find((x) => x.id === id);
      if (hit) { setCurrent(hit); setQ(hit.question); }
    });
  }, [params]);

  const submit = async () => {
    if (!q.trim() || loading) return;
    setLoading(true); setError(null);
    try {
      const a = await questionService.ask(q.trim(), repo.id);
      setCurrent(a);
      setHistory((h) => [a, ...h.filter((x) => x.question !== a.question)]);
    } catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  };

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title="Ask CodeTrace" desc="Investigate why code exists, backed by linked evidence." demo="Mock answers"
        actions={<button className="btn" onClick={() => setShowHistory(!showHistory)}><History size={14} />History{showHistory ? <ChevronRight size={13} /> : <ChevronLeft size={13} />}</button>} />
      <div className="grid gap-5 xl:grid-cols-[1fr_300px]">
        <div className="min-w-0 space-y-4">
          <QuestionInput value={q} onChange={setQ} onSubmit={submit} onClear={() => { setQ(''); setCurrent(null); setError(null); }} loading={loading} />
          <SuggestedQuestions onPick={setQ} />
          <p className="text-xs text-muted">{repo.isDemo ? 'Demo mode is enabled. Set VITE_USE_MOCKS=false to ask the backend.' : 'Answers cite only indexed evidence and may abstain when support is insufficient.'}</p>
          {loading && <Loading label="Searching sample evidence" />}
          {error && <ErrorMessage message={error} onRetry={submit} />}
          {!loading && !error && (current ? <AnswerPanel qa={current} /> : <EmptyState title="No question yet" desc="Pick a suggestion or type your own question to see an evidence-backed mock answer." action={<MessageSquareText className="text-muted" size={16} />} />)}
        </div>

        <aside className="space-y-4">
          {showHistory && (
            <section className="card p-3">
              <h3 className="mb-2 text-sm font-medium">Recent questions</h3>
              <ul className="space-y-1.5">
                {history.map((h) => (
                  <li key={h.id}><button className="w-full rounded-md border border-line p-2 text-left hover:border-accent/60" onClick={() => { setCurrent(h); setQ(h.question); setError(null); }}>
                    <div className="text-xs">{h.question}</div><div className="mt-1 text-[11px] text-muted">{fmtDateTime(h.timestamp)}</div>
                  </button></li>
                ))}
              </ul>
            </section>
          )}
          <section className="card space-y-3 p-3">
            <h3 className="text-sm font-medium">Context</h3>
            {current ? (
              <>
                <div><div className="mb-1 text-xs text-muted">Evidence strength</div><StatusBadge status={current.status} /></div>
                <div><div className="mb-1 text-xs text-muted">Relevant files</div>{current.relatedFiles.length ? current.relatedFiles.map((f) => <code key={f} className="block truncate text-xs">{f}</code>) : <span className="text-xs text-muted">None found</span>}</div>
                <div><div className="mb-1 text-xs text-muted">Related commits</div><div className="space-y-1.5">{current.relatedCommits.length ? current.relatedCommits.map((c) => <CommitCard key={c.hash} commit={c} compact />) : <span className="text-xs text-muted">None found</span>}</div></div>
                <div><div className="mb-1 text-xs text-muted">Decision history</div><p className="text-xs">{current.history}</p></div>
              </>
            ) : <p className="text-xs text-muted">Context appears after you ask a question.</p>}
          </section>
        </aside>
      </div>
    </div>
  );
}
