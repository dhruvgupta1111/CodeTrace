import { useEffect, type ReactNode } from 'react';
import { AlertTriangle, CheckCircle2, CircleDashed, GitCommit, HelpCircle, Loader2, Inbox, X, FlaskConical, ExternalLink } from 'lucide-react';
import type { AnswerStatus, Commit, Evidence, EvidenceStatus } from '../types';
import { cx, fmtDate } from '../lib/utils';

const STATUS = {
  strong: { label: 'Strong evidence', cls: 'text-ok border-ok/40 bg-ok/10', Icon: CheckCircle2, tip: 'Multiple linked sources (commit, PR, or ADR) explicitly state the rationale.' },
  partial: { label: 'Partial evidence', cls: 'text-warn border-warn/40 bg-warn/10', Icon: CircleDashed, tip: 'Some sources are related but do not fully confirm the reasoning. Treat as uncertain.' },
  insufficient: { label: 'Insufficient evidence', cls: 'text-muted border-line bg-raised', Icon: HelpCircle, tip: 'No indexed source establishes the reasoning.' },
  conflicting: { label: 'Conflicting evidence', cls: 'text-bad border-bad/40 bg-bad/10', Icon: AlertTriangle, tip: 'Indexed sources disagree or supersession is unresolved.' },
  insufficient_evidence: { label: 'Insufficient evidence', cls: 'text-muted border-line bg-raised', Icon: HelpCircle, tip: 'No indexed source establishes the reasoning.' },
  conflicting_evidence: { label: 'Conflicting evidence', cls: 'text-bad border-bad/40 bg-bad/10', Icon: AlertTriangle, tip: 'Indexed sources disagree or supersession is unresolved.' },
  supported: { label: 'Supported answer', cls: 'text-ok border-ok/40 bg-ok/10', Icon: CheckCircle2, tip: 'The answer is backed by relevant, non-conflicting evidence.' },
  partially_supported: { label: 'Partially supported', cls: 'text-warn border-warn/40 bg-warn/10', Icon: CircleDashed, tip: 'Some rationale is supported, but important evidence or verification is missing.' },
} as const;

export function StatusBadge({ status }: { status: EvidenceStatus | AnswerStatus }) {
  const s = STATUS[status];
  return (
    <span title={s.tip} aria-label={`${s.label}. ${s.tip}`} tabIndex={0} className={cx('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium', s.cls)}>
      <s.Icon size={12} aria-hidden /> {s.label}
    </span>
  );
}

export function DemoBadge({ text = 'Demo data' }: { text?: string }) {
  return <span className="inline-flex items-center gap-1 rounded-full border border-accent/40 bg-accent/10 px-2 py-0.5 text-xs text-accent"><FlaskConical size={11} aria-hidden />{text}</span>;
}

export function PageHeader({ title, desc, actions, demo }: { title: string; desc: string; actions?: ReactNode; demo?: string }) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="flex items-center gap-2"><h1 className="text-lg font-semibold">{title}</h1>{demo && <DemoBadge text={demo} />}</div>
        <p className="mt-0.5 text-sm text-muted">{desc}</p>
      </div>
      {actions}
    </div>
  );
}

export function MetricCard({ label, value, caption, icon }: { label: string; value: string; caption: string; icon: ReactNode }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between text-muted"><span className="text-xs">{label}</span>{icon}</div>
      <div className="mt-2 text-2xl font-semibold tabular-nums">{value}</div>
      <div className="mt-1 text-xs text-muted">{caption}</div>
    </div>
  );
}

export function EmptyState({ title, desc, action }: { title: string; desc: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-line p-8 text-center">
      <Inbox className="text-muted" size={22} aria-hidden />
      <div className="font-medium">{title}</div>
      <div className="max-w-sm text-sm text-muted">{desc}</div>
      {action}
    </div>
  );
}

export function Loading({ label = 'Loading' }: { label?: string }) {
  return <div className="flex items-center gap-2 p-6 text-sm text-muted" role="status"><Loader2 size={16} className="animate-spin" />{label}...</div>;
}

export function ErrorMessage({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-2 rounded-lg border border-bad/40 bg-bad/10 p-3 text-sm text-bad">
      <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden />
      <div className="flex-1">{message}</div>
      {onRetry && <button className="btn !py-0.5" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Drawer({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50" onClick={onClose}>
      <aside role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()} className="h-full w-full max-w-md overflow-y-auto border-l border-line bg-panel p-5">
        <div className="mb-4 flex items-start justify-between gap-2"><h2 className="font-semibold">{title}</h2><button aria-label="Close" className="btn !p-1" onClick={onClose}><X size={14} /></button></div>
        {children}
      </aside>
    </div>
  );
}

export function ConfirmDialog({ open, title, body, confirmLabel = 'Confirm', onConfirm, onCancel }: { open: boolean; title: string; body: string; confirmLabel?: string; onConfirm: () => void; onCancel: () => void }) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onCancel();
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [open, onCancel]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4" onClick={onCancel}>
      <div role="alertdialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()} className="card w-full max-w-sm p-5">
        <h2 className="font-semibold">{title}</h2>
        <p className="mt-1 text-sm text-muted">{body}</p>
        <div className="mt-4 flex justify-end gap-2"><button className="btn" onClick={onCancel}>Cancel</button><button autoFocus className="btn btn-primary" onClick={onConfirm}>{confirmLabel}</button></div>
      </div>
    </div>
  );
}

export function CommitCard({ commit, compact }: { commit: Commit; compact?: boolean }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-line bg-bg p-2.5">
      <GitCommit size={14} className="mt-0.5 shrink-0 text-cyan" aria-hidden />
      <div className="min-w-0">
        <div className="truncate text-sm">{commit.message}</div>
        <div className="text-xs text-muted"><code className="text-cyan">{commit.hash}</code> · {commit.author} · {fmtDate(commit.date)}</div>
        {!compact && <div className="mt-1 truncate text-xs text-muted">{commit.files.join(', ')}</div>}
      </div>
    </div>
  );
}

export function EvidenceCard({ ev, onOpen }: { ev: Evidence; onOpen: (e: Evidence) => void }) {
  return (
    <button onClick={() => onOpen(ev)} className="card w-full p-4 text-left transition-colors hover:border-accent/60">
      <div className="flex items-start justify-between gap-2">
        <div className="font-medium">{ev.title}</div><StatusBadge status={ev.status} />
      </div>
      <div className="mt-1 text-xs text-muted">{ev.type.replace('_', ' ')} · {ev.author} · {fmtDate(ev.date)}</div>
      <p className="mt-2 line-clamp-2 text-sm text-muted">{ev.excerpt}</p>
      <div className="mt-2 flex flex-wrap gap-1">{ev.entities.map((e) => <code key={e} className="rounded bg-raised px-1.5 py-0.5 text-xs">{e}</code>)}</div>
    </button>
  );
}

export function SourceLink({ url }: { url: string }) {
  return <a href={url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-cyan hover:underline">Open source <ExternalLink size={12} aria-hidden /></a>;
}
