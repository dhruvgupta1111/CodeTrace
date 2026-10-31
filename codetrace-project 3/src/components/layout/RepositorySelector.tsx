import { useEffect, useRef, useState } from 'react';
import { Check, ChevronsUpDown } from 'lucide-react';
import { useApp } from '../../hooks/useApp';
import { cx } from '../../lib/utils';

export function RepositorySelector({ large }: { large?: boolean }) {
  const { repo, repositories, setRepo } = useApp();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const k = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', h); document.addEventListener('keydown', k);
    return () => { document.removeEventListener('mousedown', h); document.removeEventListener('keydown', k); };
  }, []);
  return (
    <div ref={ref} className="relative">
      <button className={cx('btn', large && '!px-4 !py-2')} aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(!open)}>
        {large ? <span className="text-sm">Change repository</span> : <code className="text-xs">{repo.fullName}</code>}<ChevronsUpDown size={13} className="text-muted" />
      </button>
      {open && (
        <ul role="listbox" className="dropdown-in absolute left-0 z-40 mt-1 w-64 rounded-md border border-line bg-raised p-1 shadow-xl">
          {repositories.length ? repositories.map((r) => (
            <li key={r.id}>
              <button role="option" aria-selected={r.id === repo.id} onClick={() => { setRepo(r); setOpen(false); }} className="flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm hover:bg-bg">
                <span><code className="text-xs">{r.fullName}</code><span className="block text-xs text-muted">{r.language} · {r.indexStatus}</span></span>
                {r.id === repo.id && <Check size={14} className="text-accent" />}
              </button>
            </li>
          )) : <li className="px-2 py-2 text-xs text-muted">No repositories connected.</li>}
        </ul>
      )}
    </div>
  );
}
