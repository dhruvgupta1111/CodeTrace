import { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Bell, Menu, Search, CornerDownLeft, UserRound } from 'lucide-react';
import { RepositorySelector } from './RepositorySelector';
import { NAV } from './Sidebar';
import { useApp } from '../../hooks/useApp';

const statusStyle = { indexed: 'bg-ok', indexing: 'bg-warn animate-pulse', running: 'bg-warn animate-pulse', pending: 'bg-warn animate-pulse', stale: 'bg-muted', failed: 'bg-bad', not_indexed: 'bg-muted' } as const;

function SearchPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState('');
  const nav = useNavigate();
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { if (open) { setQ(''); setTimeout(() => ref.current?.focus(), 0); } }, [open]);
  if (!open) return null;
  const results = NAV.filter((n) => n.label.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center bg-black/60 p-4 pt-24" onClick={onClose}>
      <div role="dialog" aria-label="Search" className="card w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <input ref={ref} className="input !rounded-b-none !border-0 !border-b" placeholder="Jump to page..." value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Escape') onClose(); if (e.key === 'Enter' && results[0]) { nav(results[0].to); onClose(); } }} />
        <ul className="p-1">
          {results.map((r) => <li key={r.to}><button className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-raised" onClick={() => { nav(r.to); onClose(); }}><r.icon size={14} className="text-muted" />{r.label}</button></li>)}
          {!results.length && <li className="px-2 py-3 text-sm text-muted">No pages match.</li>}
        </ul>
        <div className="flex items-center gap-1 border-t border-line px-3 py-1.5 text-xs text-muted"><CornerDownLeft size={11} /> to open · Esc to close</div>
      </div>
    </div>
  );
}

export function TopBar({ onMenu }: { onMenu: () => void }) {
  const { repo } = useApp();
  const loc = useLocation();
  const [search, setSearch] = useState(false);
  const [bell, setBell] = useState(false);
  const page = NAV.find((n) => (n.to === '/' ? loc.pathname === '/' : loc.pathname.startsWith(n.to)));
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setSearch(true); } };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, []);
  return (
    <header className="app-chrome flex items-center gap-3 border-b border-line px-4 py-2.5">
      <button className="lg:hidden" aria-label="Open menu" onClick={onMenu}><Menu size={18} /></button>
      <nav aria-label="Breadcrumb" className="hidden min-w-0 text-sm sm:block">
        <Link to="/" className="text-muted hover:text-fg">CodeTrace</Link><span className="mx-1.5 text-muted">/</span><span className="font-medium">{page?.label ?? 'Page'}</span>
      </nav>
      <div className="ml-auto flex items-center gap-2">
        <RepositorySelector />
        <span className="hidden items-center gap-1.5 text-xs text-muted md:flex"><span className={`h-2 w-2 rounded-full ${statusStyle[repo.indexStatus]}`} />{repo.indexStatus === 'indexed' ? 'Indexed' : repo.indexStatus === 'indexing' || repo.indexStatus === 'running' ? 'Indexing' : repo.indexStatus === 'not_indexed' ? 'Not indexed' : repo.indexStatus === 'failed' ? 'Failed' : 'Stale'}</span>
        <button className="btn" onClick={() => setSearch(true)} aria-label="Search"><Search size={14} /><span className="hidden sm:inline text-muted">Search</span><kbd className="hidden rounded border border-line px-1 text-[10px] text-muted sm:inline">Ctrl K</kbd></button>
        <div className="relative">
          <button className="btn !p-1.5" aria-label="Notifications" aria-expanded={bell} onClick={() => setBell(!bell)}><Bell size={14} /><span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-accent" /></button>
          {bell && (
            <div className="absolute right-0 z-40 mt-1 w-64 rounded-md border border-line bg-raised p-3 text-sm shadow-xl">
              <div className="font-medium">Notifications</div>
              <p className="mt-1 text-xs text-muted">Sample: acme/web-checkout re-indexing started. (Demo notification.)</p>
            </div>
          )}
        </div>
        <Link to="/settings" aria-label="Account settings" className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/15 text-accent transition-transform hover:scale-105"><UserRound size={15} /></Link>
      </div>
      <SearchPalette open={search} onClose={() => setSearch(false)} />
    </header>
  );
}
