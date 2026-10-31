import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, Check, Eye, EyeOff, GitBranch, ShieldCheck } from 'lucide-react';

export default function AuthPage() {
  const [params] = useSearchParams();
  const [mode, setMode] = useState<'login' | 'signup'>(params.get('mode') === 'signup' ? 'signup' : 'login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const submit = (event: FormEvent) => {
    event.preventDefault(); setError('');
    if (mode === 'signup' && name.trim().length < 2) return setError('Enter your name to create an account.');
    if (!email.includes('@')) return setError('Enter a valid email address.');
    if (password.length < 8) return setError('Use at least 8 characters for your password.');
    localStorage.setItem('ct-account', JSON.stringify({ name: name.trim() || email.split('@')[0], email }));
    navigate('/');
  };

  return <main className="min-h-screen bg-bg px-4 py-8 text-fg sm:px-6">
    <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-5xl items-center gap-10 lg:grid-cols-[1.05fr_.95fr]">
      <section className="hidden lg:block">
        <Link to="/" className="mb-10 inline-flex items-center gap-2 font-semibold"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-bg"><GitBranch size={17} /></span>CodeTrace</Link>
        <p className="max-w-lg text-4xl font-semibold leading-tight">Understand the history behind every line of code.</p>
        <p className="mt-4 max-w-md text-muted">Connect a repository, trace decisions through evidence, and ask better questions about the codebase.</p>
        <div className="mt-8 space-y-3 text-sm text-muted"><div className="flex items-center gap-2"><Check size={15} className="text-ok" />Evidence-linked answers</div><div className="flex items-center gap-2"><Check size={15} className="text-ok" />Repository history in one workspace</div><div className="flex items-center gap-2"><Check size={15} className="text-ok" />Honest uncertainty when history is incomplete</div></div>
      </section>
      <section className="mx-auto w-full max-w-md">
        <div className="mb-8 flex items-center gap-2 font-semibold lg:hidden"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-bg"><GitBranch size={17} /></span>CodeTrace</div>
        <div className="card p-6 shadow-xl sm:p-8">
          <div className="mb-6"><h1 className="text-2xl font-semibold">{mode === 'login' ? 'Welcome back' : 'Create your account'}</h1><p className="mt-1 text-sm text-muted">{mode === 'login' ? 'Sign in to continue to your workspace.' : 'Start building a clearer history of your codebase.'}</p></div>
          <form onSubmit={submit} className="space-y-4">
            {mode === 'signup' && <label className="block text-sm"><span className="text-muted">Full name</span><input className="input mt-1.5" value={name} onChange={(e) => setName(e.target.value)} placeholder="Alex Morgan" autoComplete="name" /></label>}
            <label className="block text-sm"><span className="text-muted">Email address</span><input className="input mt-1.5" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" autoComplete="email" /></label>
            <label className="block text-sm"><span className="text-muted">Password</span><div className="relative mt-1.5"><input className="input pr-10" type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} /><button type="button" className="absolute right-2 top-1.5 rounded p-1 text-muted hover:text-fg" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={15} /> : <Eye size={15} />}</button></div></label>
            {mode === 'login' && <div className="text-right"><button type="button" className="text-xs text-cyan hover:underline" onClick={() => setError('Password recovery will be available when server authentication is connected.')}>Forgot password?</button></div>}
            {error && <p className="rounded-md border border-bad/40 bg-bad/10 p-2.5 text-sm text-bad" role="alert">{error}</p>}
            <button className="btn btn-primary w-full py-2.5" type="submit">{mode === 'login' ? 'Sign in' : 'Create account'}<ArrowRight size={15} /></button>
          </form>
          <div className="my-5 flex items-center gap-3 text-xs text-muted"><span className="h-px flex-1 bg-line" />or<span className="h-px flex-1 bg-line" /></div>
          <button className="btn w-full" onClick={() => setError('GitHub sign-in will be available when OAuth is connected.')}>Continue with GitHub</button>
          <p className="mt-6 text-center text-sm text-muted">{mode === 'login' ? "Don't have an account?" : 'Already have an account?'} <button className="font-medium text-cyan hover:underline" onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); }}>{mode === 'login' ? 'Create one' : 'Sign in'}</button></p>
        </div>
        <p className="mt-4 flex items-center justify-center gap-1.5 text-center text-xs text-muted"><ShieldCheck size={13} />Your repository credentials stay server-side.</p>
      </section>
    </div>
  </main>;
}
