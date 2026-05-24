// Reusable cell components for the DeltaSci review surface.
// Ported from biointel's lib/notebook/cells.tsx, extended with role + coverage badges.

import type { ReactNode } from 'react';

export function Cell({
  n,
  title,
  children,
  accent,
  meta,
}: {
  n: number | string;
  title: string;
  children: ReactNode;
  accent?: 'teal' | 'warm' | 'neutral';
  meta?: ReactNode;
}) {
  const accentClass =
    accent === 'teal'
      ? 'border-teal/40'
      : accent === 'warm'
        ? 'border-burgundy/40'
        : 'border-slate-border/30';
  return (
    <section className={`mt-12 border-l-2 pl-5 ${accentClass}`}>
      <h2 className="font-sans text-[11px] font-medium uppercase tracking-wider text-ink/55">
        Cell {n}
      </h2>
      <h3 className="mt-1 font-serif text-[19px] font-semibold leading-snug text-ink">
        {title}
      </h3>
      {meta && <div className="mt-2 flex flex-wrap gap-2">{meta}</div>}
      <div className="mt-4 space-y-4">{children}</div>
    </section>
  );
}

export function Code({ children }: { children: string }) {
  return (
    <pre className="overflow-auto rounded bg-ink/95 px-4 py-3 font-mono text-[12px] leading-relaxed text-cream">
      <code>{children}</code>
    </pre>
  );
}

export function Out({ children }: { children: ReactNode }) {
  return (
    <div className="rounded border border-slate-border/15 bg-white/60 px-4 py-3">
      <p className="font-sans text-[10px] font-medium uppercase tracking-wider text-ink/55">
        Output
      </p>
      <div className="mt-2">{children}</div>
    </div>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return <div className="font-serif text-[14px] leading-relaxed text-ink/80">{children}</div>;
}

export function NotebookHeader({
  title,
  subtitle,
  badges,
}: {
  title: string;
  subtitle: ReactNode;
  badges?: ReactNode;
}) {
  return (
    <>
      <h1 className="font-serif text-3xl font-semibold leading-tight text-ink">{title}</h1>
      <p className="mt-4 max-w-prose font-serif text-[17px] leading-relaxed text-ink/80">
        {subtitle}
      </p>
      {badges && (
        <ul className="mt-4 flex flex-wrap gap-3 font-mono text-[11px] text-ink/65">{badges}</ul>
      )}
    </>
  );
}

export function Badge({
  children,
  intent,
}: {
  children: ReactNode;
  intent?: 'teal' | 'warm' | 'neutral';
}) {
  const cls =
    intent === 'teal'
      ? 'bg-teal-soft text-teal'
      : intent === 'warm'
        ? 'bg-burgundy-soft text-burgundy'
        : 'bg-slate-border/10 text-ink/65';
  return <li className={`rounded-sm px-2 py-0.5 ${cls}`}>{children}</li>;
}

// DeltaSci-specific: a span variant of Badge for inline use (not in a <ul>).
export function InlineBadge({
  children,
  intent,
}: {
  children: ReactNode;
  intent?: 'teal' | 'warm' | 'neutral';
}) {
  const cls =
    intent === 'teal'
      ? 'bg-teal-soft text-teal'
      : intent === 'warm'
        ? 'bg-burgundy-soft text-burgundy'
        : 'bg-slate-border/10 text-ink/65';
  return (
    <span className={`inline-flex items-center rounded-sm px-2 py-0.5 font-mono text-[10px] ${cls}`}>
      {children}
    </span>
  );
}

// DeltaSci-specific: role label for transcript rounds (domain | engineer | synthesis).
export function RoleBadge({ role }: { role: 'domain' | 'engineer' | 'synthesis' | string }) {
  const isDomain = role.startsWith('domain');
  const isEngineer = role.startsWith('engineer');
  const intent: 'teal' | 'warm' | 'neutral' = isDomain ? 'teal' : isEngineer ? 'warm' : 'neutral';
  const label = isDomain
    ? 'domain scientist'
    : isEngineer
      ? 'ml engineer'
      : role === 'synthesis'
        ? 'synthesis'
        : role;
  return <InlineBadge intent={intent}>{label}</InlineBadge>;
}
