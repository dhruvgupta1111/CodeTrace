import { NavLink } from 'react-router-dom';
import { Activity, BookOpen, Clock, FolderTree, FlaskConical, GitBranch, LayoutDashboard, MessageSquareText, Moon, Network, Settings, Sun, ChevronsUpDown, X, Check } from 'lucide-react';
import { useState } from 'react';
import { useApp } from '../../hooks/useApp';
import { cx } from '../../lib/utils';

export const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/ask', label: 'Ask CodeTrace', icon: MessageSquareText },
  { to: '/graph', label: 'Decision Graph', icon: Network },
  { to: '/timeline', label: 'Decision Timeline', icon: Clock },
  { to: '/explorer', label: 'Repository Explorer', icon: FolderTree },
  { to: '/evidence', label: 'Evidence Library', icon: BookOpen },
  { to: '/evaluation', label: 'Evaluation Lab', icon: Activity },
  { to: '/settings', label: 'Settings', icon: Settings },
];

const workspaces = ['Acme Engineering', 'Personal sandbox'];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { repo, theme, toggleTheme } = useApp();
  const [ws, setWs] = useState(workspaces[0]);
  const [wsOpen, setWsOpen] = useState(false);
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-black/50 lg:hidden" onClick={onClose} />}
      <aside className={cx('fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-line bg-panel transition-transform lg:static lg:translate-x-0', open ? 'translate-x-0' : '-translate-x-full')}>
        <div className="flex items-center justify-between px-4 py-4">
          <div className="flex items-center gap-2"><div className="sidebar-brand flex h-8 w-8 items-center justify-center rounded-lg text-white"><GitBranch size={17} /></div><span className="font-semibold tracking-tight">CodeTrace</span></div>
          <button className="lg:hidden" aria-label="Close menu" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="relative px-3">
          <button className="btn w-full !justify-between" onClick={() => setWsOpen(!wsOpen)} aria-expanded={wsOpen}><span className="truncate">{ws}</span><ChevronsUpDown size={13} className="text-muted" /></button>
          {wsOpen && (
            <ul className="absolute inset-x-3 z-10 mt-1 rounded-md border border-line bg-raised p-1 shadow-xl">
              {workspaces.map((w) => <li key={w}><button className="flex w-full items-center justify-between rounded px-2 py-1.5 text-sm hover:bg-bg" onClick={() => { setWs(w); setWsOpen(false); }}>{w}{w === ws && <Check size={13} className="text-accent" />}</button></li>)}
            </ul>
          )}
        </div>
        <nav className="mt-3 flex-1 space-y-0.5 overflow-y-auto px-3" aria-label="Main">
          {NAV.slice(0, 2).map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === '/'} onClick={onClose} className={({ isActive }) => cx('flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors', isActive ? 'bg-accent/15 text-accent' : 'text-muted hover:bg-raised hover:text-fg')}>
              <n.icon size={16} aria-hidden />{n.label}
            </NavLink>
          ))}
          <div className="mt-5 rounded-md border border-dashed border-line px-3 py-3 text-xs text-muted">Open workspace pages from the Overview launcher.</div>
        </nav>
        <div className="space-y-3 border-t border-line p-3">
          <div className="rounded-md bg-raised p-2 text-xs"><div className="text-muted">Current repository</div><code className="text-fg">{repo.fullName}</code></div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2"><div className="flex h-7 w-7 items-center justify-center rounded-full bg-accent/20 text-xs font-medium text-accent">DV</div><div className="text-xs"><div>Developer</div><div className="text-muted">dev@acme.test</div></div></div>
            <button className="btn !p-1.5" onClick={toggleTheme} aria-label="Toggle theme">{theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}</button>
          </div>
        </div>
      </aside>
    </>
  );
}

export { FlaskConical };
