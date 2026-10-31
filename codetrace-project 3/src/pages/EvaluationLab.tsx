import { useEffect, useState } from 'react';
import { Loader2, Play } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ConfirmDialog, DemoBadge, ErrorMessage, Loading, MetricCard, PageHeader } from '../components/ui';
import { evaluationService } from '../services';
import { useApp } from '../hooks/useApp';
import { cx, fmtDateTime } from '../lib/utils';
import type { EvalRun } from '../types';

type Filter = 'all' | 'passed' | 'failed' | 'unsupported' | 'supersession';
const RES = { passed: 'text-ok', failed: 'text-bad', unsupported: 'text-muted' } as const;

export default function EvaluationLab() {
  const { toast } = useApp();
  const [run, setRun] = useState<EvalRun | null>(null);
  const [filter, setFilter] = useState<Filter>('all');
  const [running, setRunning] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { evaluationService.initial().then(setRun); }, []);
  if (!run) return <Loading />;

  const start = async () => {
    setConfirm(false); setRunning(true); setErr(null);
    try { setRun(await evaluationService.runDemo()); toast('Demo evaluation finished (simulated locally)'); }
    catch (e) { setErr((e as Error).message); } finally { setRunning(false); }
  };
  const rows = run.cases.filter((c) => filter === 'all' || (filter === 'supersession' ? c.supersession : c.result === filter));
  const chart = run.metrics.filter((m) => m.unit === '%').map((m) => ({ name: m.label.split(' ')[0], value: m.value }));

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <PageHeader title="Evaluation Lab" desc="Track quality of repository question answering." demo={run.simulated ? 'Simulated run' : 'Illustrative values'}
        actions={<button className="btn btn-primary" disabled={running} onClick={() => setConfirm(true)}>{running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}{running ? 'Simulating...' : 'Run Demo Evaluation'}</button>} />
      {err && <ErrorMessage message={err} />}
      <p className="rounded-md bg-raised p-2 text-xs text-muted">{run.simulated ? `Simulated locally at ${fmtDateTime(run.ranAt!)} using mock cases. No backend tests or models were run.` : 'All initial metrics are illustrative demo values.'}</p>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">{run.metrics.map((m) => <MetricCard key={m.key} label={m.label} value={`${m.value}${m.unit}`} caption={m.caption} icon={<DemoBadge text="Demo" />} />)}</div>
      <section className="card h-56 p-4"><ResponsiveContainer width="100%" height="100%"><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" stroke="#8884" /><XAxis dataKey="name" tick={{ fontSize: 11, fill: '#8a8a9a' }} /><YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#8a8a9a' }} /><Tooltip contentStyle={{ background: '#18181f', border: '1px solid #26262f', fontSize: 12 }} /><Bar dataKey="value" fill="#8b78ff" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></section>
      <section className="card">
        <div className="flex flex-wrap gap-1.5 border-b border-line p-3">
          {(['all', 'passed', 'failed', 'unsupported', 'supersession'] as Filter[]).map((f) => <button key={f} aria-pressed={filter === f} onClick={() => setFilter(f)} className={cx('rounded-full border px-3 py-0.5 text-xs capitalize', filter === f ? 'border-accent text-accent' : 'border-line text-muted')}>{f}</button>)}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-muted"><tr>{['Question', 'Expected evidence', 'Retrieved evidence', 'Result', 'Status'].map((h) => <th key={h} className="px-4 py-2 font-medium">{h}</th>)}</tr></thead>
            <tbody>{rows.map((c) => <tr key={c.id} className="border-t border-line"><td className="px-4 py-2">{c.question}</td><td className="px-4 py-2 text-muted">{c.expected}</td><td className="px-4 py-2 text-muted">{c.retrieved}</td><td className={cx('px-4 py-2 font-medium capitalize', RES[c.result])}>{c.result}</td><td className="px-4 py-2 text-muted">{c.status}</td></tr>)}
              {!rows.length && <tr><td colSpan={5} className="p-6 text-center text-muted">No cases match this filter.</td></tr>}</tbody>
          </table>
        </div>
      </section>
      <ConfirmDialog open={confirm} title="Run demo evaluation?" body="This simulates an evaluation locally with mock cases. It does not call any backend." confirmLabel="Run simulation" onConfirm={start} onCancel={() => setConfirm(false)} />
    </div>
  );
}
