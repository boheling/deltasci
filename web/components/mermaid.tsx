'use client';

// Renders a mermaid diagram from its source string.
// Mermaid is heavy (~1 MB) — dynamic-imported on the client only.

import { useEffect, useId, useRef, useState } from 'react';

export function Mermaid({ source, label }: { source: string; label?: string }) {
  const id = useId().replace(/[^a-zA-Z0-9]/g, '');
  const ref = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    let cancelled = false;
    if (!source.trim()) return;
    (async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'default' });
        const { svg } = await mermaid.render(`mmd-${id}`, source);
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [source, id]);

  if (error) {
    return (
      <div className="rounded border border-burgundy/40 bg-warm-soft/40 p-4 font-mono text-[12px] text-burgundy">
        <div className="font-sans text-[11px] uppercase tracking-wider">mermaid render error</div>
        <pre className="mt-2 whitespace-pre-wrap">{error}</pre>
        <details className="mt-2">
          <summary className="cursor-pointer text-ink/70">source</summary>
          <pre className="mt-1 whitespace-pre-wrap text-ink/80">{source}</pre>
        </details>
      </div>
    );
  }

  return (
    <figure className="rounded border border-slate-border/15 bg-white/60 p-4">
      {label && (
        <figcaption className="mb-2 font-sans text-[11px] font-medium uppercase tracking-wider text-ink/55">
          {label}
        </figcaption>
      )}
      <div ref={ref} className="overflow-x-auto" aria-label={label} />
      <details className="mt-3">
        <summary className="cursor-pointer font-sans text-[11px] text-ink/55">view mermaid source</summary>
        <pre className="mt-2 overflow-x-auto rounded-sm bg-ink/5 p-3 font-mono text-[11px] leading-relaxed text-ink/80">
          {source}
        </pre>
      </details>
    </figure>
  );
}
