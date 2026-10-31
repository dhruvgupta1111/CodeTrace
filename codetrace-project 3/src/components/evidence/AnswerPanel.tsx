import { FileCode2, GitPullRequest, Info } from 'lucide-react';
import { CommitCard, SourceLink, StatusBadge } from '../ui';
import { fmtDateTime } from '../../lib/utils';
import type { QuestionAnswer } from '../../types';
import { useApp } from '../../hooks/useApp';

export function AnswerPanel({ qa }: { qa: QuestionAnswer }) {
  const { prefs } = useApp();
  const related = qa.relatedDecisionIds ?? [];
  const unsupported = qa.status === 'insufficient_evidence';
  return (
    <article className="card p-5" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <StatusBadge status={qa.status} />
        <span className="text-xs text-muted">{fmtDateTime(qa.timestamp)}</span>
      </div>
      <h2 className="mt-3 font-medium">{qa.question}</h2>
      <p className="mt-2 leading-relaxed">{qa.answer}</p>
      {qa.warnings?.length ? <p className="mt-3 flex items-start gap-1.5 rounded-md bg-raised p-2 text-xs text-muted"><Info size={13} className="mt-0.5 shrink-0" />{qa.warnings.join(' · ')}</p> : qa.evidenceFacts?.length ? <p className="mt-3 flex items-start gap-1.5 rounded-md bg-raised p-2 text-xs text-muted"><Info size={13} className="mt-0.5 shrink-0" />Source facts are shown separately from interpretation. Review each linked evidence record.</p> : null}

      {unsupported ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {([['Evidence searched', qa.searched], ['Evidence missing', qa.missing], ['Suggested follow-ups', qa.followUps]] as const).map(([t, items]) => (
            <div key={t} className="rounded-md border border-line p-3"><div className="mb-1 text-xs font-medium">{t}</div><ul className="list-disc space-y-1 pl-4 text-xs text-muted">{items?.map((i) => <li key={i}>{i}</li>)}</ul></div>
          ))}
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex items-center gap-2 text-sm"><FileCode2 size={14} className="text-cyan" /><code className="text-xs">{qa.file}</code></div>
            <div className="flex items-center gap-2 text-sm"><GitPullRequest size={14} className="text-cyan" />{qa.pullRequest}</div>
          </div>
          {qa.commit && <div><div className="mb-1 text-xs font-medium text-muted">Supporting commit</div><CommitCard commit={qa.commit} compact /></div>}
          {prefs.showSnippets && qa.excerpt && <div><div className="mb-1 text-xs font-medium text-muted">Source excerpt</div><pre className="overflow-x-auto rounded-md border border-line bg-bg p-3 text-xs">{qa.excerpt}</pre></div>}
          {qa.sourceUrl && <SourceLink url={qa.sourceUrl} />}
          {qa.sources?.length ? <div><div className="mb-1 text-xs font-medium text-muted">Supporting evidence</div><div className="space-y-2">{qa.sources.map((source) => <div key={source.id} className="rounded-md border border-line p-2 text-xs"><div className="font-medium">{source.type.replace('_', ' ')}</div><code className="text-muted">{source.id}</code>{source.excerpt && <p className="mt-1 text-muted">{source.excerpt}</p>}{source.url && <div className="mt-1"><SourceLink url={source.url} /></div>}</div>)}</div></div> : null}
          {qa.interpretation && <div className="rounded-md border border-warn/40 bg-warn/5 p-3 text-sm"><div className="mb-1 text-xs font-medium text-warn">Interpretation</div>{qa.interpretation}</div>}
          <div>
            <div className="mb-1 text-xs font-medium text-muted">Related decisions</div>
            <ul className="space-y-1.5">
              {related.map((d) => (
                <li key={d} className="flex items-center justify-between gap-2 rounded-md border border-line p-2 text-sm">
                  <span><code>{d}</code><span className="block text-xs text-muted">Decision record linked by the backend</span></span>
                  <StatusBadge status="partial" />
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </article>
  );
}
