import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { repositories } from '../data/mock';
import { repositoryService } from '../services';
import { USE_MOCKS } from '../lib/http';
import type { Repository } from '../types';
import { CheckCircle2, Info } from 'lucide-react';

interface Toast { id: number; text: string }
interface Ctx {
  repo: Repository;
  repositories: Repository[];
  setRepo: (r: Repository) => void;
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  toast: (t: string) => void;
  prefs: { compact: boolean; showSnippets: boolean };
  setPrefs: (p: { compact: boolean; showSnippets: boolean }) => void;
}
const AppCtx = createContext<Ctx | null>(null);
export const useApp = () => {
  const c = useContext(AppCtx);
  if (!c) throw new Error('useApp outside provider');
  return c;
};

export function AppProvider({ children }: { children: ReactNode }) {
  const empty: Repository = { id: '', fullName: 'No repository connected', defaultBranch: '—', language: '—', commitsAnalyzed: 0, filesIndexed: 0, lastIndexed: '', indexStatus: 'not_indexed', isDemo: false };
  const [repo, setRepoState] = useState<Repository>(USE_MOCKS ? repositories[0] : empty);
  const [repoList, setRepoList] = useState<Repository[]>(USE_MOCKS ? repositories : []);
  const [theme, setTheme] = useState<'dark' | 'light'>(() => (localStorage.getItem('ct-theme-v2') as 'dark' | 'light') ?? 'light');
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [prefs, setPrefs] = useState({ compact: false, showSnippets: true });

  useEffect(() => {
    if (!USE_MOCKS) repositoryService.list().then((items) => { setRepoList(items); if (items[0]) setRepoState(items[0]); }).catch(() => setRepoList([]));
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('ct-theme-v2', theme);
  }, [theme]);

  const toast = useCallback((text: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3000);
  }, []);

  const setRepo = (r: Repository) => { setRepoState(r); toast(`Switched to ${r.fullName}`); };

  return (
    <AppCtx.Provider value={{ repo, repositories: repoList, setRepo, theme, toggleTheme: () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')), toast, prefs, setPrefs }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="flex items-center gap-2 rounded-md border border-line bg-raised px-3 py-2 text-sm shadow-lg">
            {t.text.startsWith('Switched') ? <Info size={14} className="text-cyan" /> : <CheckCircle2 size={14} className="text-ok" />}
            {t.text}
          </div>
        ))}
      </div>
    </AppCtx.Provider>
  );
}
