import type { ReactNode } from 'react';
import { useState } from 'react';
import { LogIn, LogOut, UserRound } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/ui';
import { RepositorySelector } from '../components/layout/RepositorySelector';
import { useApp } from '../hooks/useApp';
import { API_BASE_URL, USE_MOCKS } from '../lib/http';

function Section({ title, children }: { title: string; children: ReactNode }) {
  return <section className="card p-4"><h2 className="mb-3 font-medium">{title}</h2><div className="space-y-3 text-sm">{children}</div></section>;
}
function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return <label className="flex items-center justify-between gap-3"><span>{label}</span><input type="checkbox" role="switch" checked={checked} onChange={(e) => onChange(e.target.checked)} /></label>;
}

export default function SettingsPage() {
  const { theme, toggleTheme, prefs, setPrefs, toast } = useApp();
  const navigate = useNavigate();
  const [account, setAccount] = useState<{ name: string; email: string } | null>(() => {
    try { return JSON.parse(localStorage.getItem('ct-account') ?? 'null') as { name: string; email: string } | null; } catch { return null; }
  });
  const logout = () => { localStorage.removeItem('ct-account'); setAccount(null); toast('You have been logged out'); };
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <PageHeader title="Settings" desc="Frontend preferences and API connection status." />
      <Section title="Account"><div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/15 text-accent"><UserRound size={18} /></div><div><div className="font-medium">{account?.name ?? 'Guest workspace'}</div><div className="text-xs text-muted">{account?.email ?? 'No account signed in'}</div></div></div>{account ? <button className="btn" onClick={logout}><LogOut size={14} />Log out</button> : <button className="btn btn-primary" onClick={() => navigate('/login')}><LogIn size={14} />Log in</button>}</div><p className="text-xs text-muted">Account sessions are currently stored locally in this browser. Server authentication will be connected here when the backend auth service is available.</p></Section>
      <Section title="Appearance"><Toggle label="Dark theme" checked={theme === 'dark'} onChange={toggleTheme} />
        <Toggle label="Compact density (preference only)" checked={prefs.compact} onChange={(v) => { setPrefs({ ...prefs, compact: v }); toast('Saved'); }} /></Section>
      <Section title="Repository preferences"><div className="flex items-center justify-between">Default repository<RepositorySelector /></div></Section>
      <Section title="Evidence display"><Toggle label="Show source excerpts in answers" checked={prefs.showSnippets} onChange={(v) => setPrefs({ ...prefs, showSnippets: v })} /></Section>
      <Section title="API connection">
        <p className="rounded-md bg-raised p-2 text-xs text-muted">The API base URL is supplied at build time. Provider credentials remain server-side and are never requested by the browser.</p>
        <label className="block"><span className="text-xs text-muted">API base URL (from VITE_API_BASE_URL)</span><input className="input mt-1" disabled value={API_BASE_URL} /></label>
        <div className="text-xs text-muted">Mock mode: {USE_MOCKS ? 'enabled' : 'disabled'}</div>
      </Section>
      <Section title="Model configuration"><p className="text-xs text-muted">Ollama model selection is configured on the backend, not in the browser.</p>
        <select className="input" disabled><option>Backend-managed</option></select></Section>
    </div>
  );
}
