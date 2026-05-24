// Project view — list of all runs under DELTASCI_PROJECT_DIR with summary cards.

import Link from 'next/link';

import type { ProjectView, RunCard } from '@/lib/loadProject';

export function ProjectViewSurface({ project }: { project: ProjectView }) {
  return (
    <main className="mx-auto max-w-3xl px-6 pb-24 pt-12 sm:pt-16">
      <header className="mb-10">
        <p className="font-sans text-sm font-medium tracking-tight text-ink">
          DeltaSci <span className="text-ink/45">project</span>
        </p>
        <p className="mt-2 font-mono text-xs text-ink/55">{project.dir}</p>
        <h1 className="mt-6 font-serif text-3xl text-ink">
          {project.runs.length} runs
        </h1>
      </header>

      {project.runs.length === 0 ? (
        <p className="font-serif text-[15px] text-ink/70">
          No deltasci runs found in this project directory. Each run subdir must
          contain at least <code className="font-mono">summary.json</code>.
        </p>
      ) : (
        <ul className="space-y-5">
          {project.runs.map((run) => (
            <RunCardLi key={run.slug} run={run} />
          ))}
        </ul>
      )}
    </main>
  );
}

function RunCardLi({ run }: { run: RunCard }) {
  const auditOk = run.audit_failed === 0;
  return (
    <li>
      <Link
        href={`/runs/${encodeURIComponent(run.slug)}`}
        className="block rounded border border-slate-border/15 bg-white/60 p-5 transition-colors hover:border-teal/50 hover:bg-white focus:border-teal focus:outline-none"
      >
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="font-mono text-[10px] uppercase tracking-wider text-teal">
            {run.pack}
          </span>
          <span className="font-mono text-[10px] text-ink/55">{run.model}</span>
          {run.iteration_count > 0 && (
            <span className="rounded-sm bg-warm-soft px-1.5 py-0.5 font-mono text-[10px] text-warm">
              iter v{run.iteration_count + 1} · {run.iteration_count} archived
            </span>
          )}
          <span className="ml-auto font-mono text-[10px] text-ink/55">
            {run.generated_at ? run.generated_at.slice(0, 16).replace('T', ' ') : ''}
          </span>
        </div>

        <h2 className="mt-3 font-serif text-[20px] leading-snug text-ink group-hover:text-teal">
          {run.title || '(untitled run)'}
        </h2>
        {run.idea && (
          <p className="mt-2 font-serif text-[14px] leading-relaxed text-ink/70">
            {truncate(run.idea, 280)}
          </p>
        )}

        <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-4">
          <Stat label="well-covered" n={run.evidence_well_covered} intent="teal" />
          <Stat label="sparse" n={run.evidence_sparse} intent="warm" />
          <Stat label="gaps" n={run.knowledge_gaps} intent="warm" />
          <Stat label="syntheses" n={run.novel_syntheses} intent="teal" />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span
            className={
              'rounded-sm px-2 py-1 font-mono text-[11px] font-semibold ' +
              (auditOk ? 'bg-teal text-cream' : 'bg-burgundy text-cream')
            }
          >
            {auditOk
              ? `✓ ${run.audit_verified} audit-verified`
              : `✗ ${run.audit_failed} FAILED AUDIT (${run.audit_verified} verified)`}
          </span>
          {run.has_protocol && <Tag>protocol</Tag>}
          {run.has_risks && <Tag>risks</Tag>}
          {run.has_challenge && <Tag>challenger</Tag>}
          <span className="ml-auto font-sans text-[11px] text-teal">view run →</span>
        </div>
      </Link>
    </li>
  );
}

function Stat({
  label,
  n,
  intent,
}: {
  label: string;
  n: number;
  intent: 'teal' | 'warm' | 'neutral';
}) {
  const c =
    intent === 'teal' ? 'text-teal' : intent === 'warm' ? 'text-burgundy' : 'text-ink/70';
  return (
    <div>
      <p className={`font-mono text-[18px] font-semibold ${c}`}>{n}</p>
      <p className="font-sans text-[10px] uppercase tracking-wider text-ink/55">{label}</p>
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-sm bg-ink/8 px-1.5 py-0.5 font-mono text-[10px] text-ink/70">
      {children}
    </span>
  );
}

function truncate(s: string, n: number): string {
  return s.length <= n ? s : s.slice(0, n).trimEnd() + '…';
}
