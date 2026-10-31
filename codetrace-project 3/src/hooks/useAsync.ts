import { useEffect, useState } from 'react';

export function useAsync<T>(fn: () => Promise<T>, dependency?: unknown) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    setLoading(true);
    fn().then((d) => live && (setData(d), setError(null)))
      .catch((e: Error) => live && setError(e.message))
      .finally(() => live && setLoading(false));
    return () => { live = false; };
  }, [tick, dependency]);
  return { data, error, loading, reload: () => setTick((t) => t + 1) };
}
