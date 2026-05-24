'use client';

// Renders a Plotly figure from its JSON spec (the same shape Jupyter writes
// under `application/vnd.plotly.v1+json`). Vanilla-JS interactivity comes
// from plotly.js — zoom, pan, hover, legend filtering, double-click reset,
// download-as-PNG, lasso/box select. The library is heavy (~3 MB minified),
// so it's dynamic-imported on the client only.

import { useEffect, useRef, useState } from 'react';

type PlotlyData = unknown[];                // plotly trace shape — typed loosely on purpose
type PlotlyLayout = Record<string, unknown>;
type PlotlyConfig = Record<string, unknown>;

export interface PlotlyFigure {
  data: PlotlyData;
  layout?: PlotlyLayout;
  config?: PlotlyConfig;
}

export function PlotlyFig({
  figure,
  label,
}: {
  figure: PlotlyFigure;
  label?: string;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    let cancelled = false;
    if (!ref.current) return;
    (async () => {
      try {
        const Plotly = (await import('plotly.js-dist-min')).default;
        if (cancelled || !ref.current) return;
        const config: PlotlyConfig = {
          responsive: true,
          displaylogo: false,
          modeBarButtonsToRemove: ['sendDataToCloud'],
          ...(figure.config ?? {}),
        };
        await Plotly.react(ref.current, figure.data, figure.layout ?? {}, config);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })();
    return () => {
      cancelled = true;
      if (ref.current) {
        // Best-effort cleanup; plotly.purge is sync.
        import('plotly.js-dist-min')
          .then((m) => m.default.purge(ref.current!))
          .catch(() => undefined);
      }
    };
  }, [figure]);

  if (error) {
    return (
      <div className="rounded border border-burgundy/40 bg-warm-soft/40 p-4 font-mono text-[12px] text-burgundy">
        <div className="font-sans text-[11px] uppercase tracking-wider">plotly render error</div>
        <pre className="mt-2 whitespace-pre-wrap">{error}</pre>
      </div>
    );
  }

  return (
    <figure className="rounded border border-slate-border/15 bg-white p-2">
      {label && (
        <figcaption className="mb-1 px-2 pt-1 font-sans text-[11px] font-medium uppercase tracking-wider text-ink/55">
          {label}
        </figcaption>
      )}
      <div ref={ref} className="w-full" style={{ minHeight: 320 }} aria-label={label} />
    </figure>
  );
}
