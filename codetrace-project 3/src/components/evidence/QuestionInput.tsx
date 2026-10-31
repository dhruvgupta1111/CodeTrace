import { CornerDownLeft, Loader2, Search, X } from 'lucide-react';

export const SUGGESTIONS = [
  'Why is the retry limit set to three?',
  'Why was this workaround introduced?',
  'Was this decision later reversed?',
  'What evidence supports this implementation?',
  'Why is this function still using the legacy API?',
  'What changed between these two commits?',
];

interface Props { value: string; onChange: (v: string) => void; onSubmit: () => void; onClear: () => void; loading: boolean }

export function QuestionInput({ value, onChange, onSubmit, onClear, loading }: Props) {
  return (
    <div className="card p-3">
      <label htmlFor="q" className="sr-only">Question</label>
      <textarea id="q" rows={2} value={value} onChange={(e) => onChange(e.target.value)} disabled={loading}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSubmit(); } }}
        placeholder="Ask why a function, configuration, or architectural decision exists..."
        className="w-full resize-none bg-transparent p-1 text-base placeholder:text-muted focus:outline-none" />
      <div className="mt-2 flex items-center justify-between">
        <span className="flex items-center gap-1 text-xs text-muted"><CornerDownLeft size={11} /> Enter to submit · Shift+Enter for newline</span>
        <div className="flex gap-2">
          <button className="btn" onClick={onClear} disabled={!value || loading}><X size={13} />Clear</button>
          <button className="btn btn-primary" onClick={onSubmit} disabled={!value.trim() || loading}>
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}{loading ? 'Searching...' : 'Ask'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function SuggestedQuestions({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2" aria-label="Suggested questions">
      {SUGGESTIONS.map((s) => <button key={s} className="rounded-full border border-line px-3 py-1 text-xs text-muted transition-colors hover:border-accent hover:text-fg" onClick={() => onPick(s)}>{s}</button>)}
    </div>
  );
}
