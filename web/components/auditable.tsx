// DeltaSci-specific review surface components.
// Adapted from biointel's ReproductionScoreboard 4-section human-in-the-loop pattern.

import type { ReactNode } from 'react';
import type { EvidenceItem, FeasibilityScores, KnowledgeGap, NovelSynthesis } from '@/lib/types';
import { categoryGuidance } from '@/lib/categoryGuidance';
import { InlineBadge } from './notebook';

// ----- Evidence trail: AuditableClaim card --------------------------------

const TYPE_LABEL: Record<EvidenceItem['type'], string> = {
  'published-evidence': 'published evidence',
  'established-guideline': 'guideline',
  observation: 'observation',
  'engineering-precedent': 'engineering',
};

export function AuditableClaim({ item }: { item: EvidenceItem }) {
  const isSparse = item.coverage === 'sparse';
  return (
    <li className="py-3">
      <div className="flex items-start gap-4">
        <span
          aria-hidden
          className={
            'mt-1 inline-flex h-5 shrink-0 items-center justify-center rounded-sm px-1.5 font-mono text-[10px] font-semibold tracking-wide ' +
            (isSparse
              ? 'bg-burgundy-soft text-burgundy'
              : 'bg-teal-soft text-teal')
          }
        >
          {item.coverage}
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-serif text-[15px] leading-snug text-ink">{item.claim}</p>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 font-mono text-[11px] text-ink/55">
            <span>{TYPE_LABEL[item.type]}</span>
            {item.source ? (
              <span className="italic">source: {item.source}</span>
            ) : (
              <span className="italic text-ink/45">no source — observation</span>
            )}
          </p>
        </div>
      </div>
    </li>
  );
}

export function AuditableClaimList({ items }: { items: EvidenceItem[] }) {
  if (items.length === 0) return <p className="font-mono text-xs text-ink/55">No claims in this section.</p>;
  return (
    <ul className="divide-y divide-slate-border/15 border-y border-slate-border/15">
      {items.map((item, i) => (
        <AuditableClaim key={i} item={item} />
      ))}
    </ul>
  );
}

// ----- Knowledge gaps: 4-section human-in-the-loop panel -----------------

export function KnowledgeGapPanel({ gap }: { gap: KnowledgeGap }) {
  const g = categoryGuidance(gap.category);
  return (
    <li className="py-4">
      <details className="group">
        <summary className="flex cursor-pointer list-none items-start gap-4 rounded-sm focus-visible:outline-none">
          <span
            aria-hidden
            className="mt-1 inline-flex h-6 w-20 shrink-0 items-center justify-center rounded-sm bg-burgundy-soft px-1.5 font-mono text-[10px] font-semibold tracking-wide text-burgundy"
          >
            researcher
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-serif text-[15px] leading-snug text-ink">{gap.question}</p>
            <p className="mt-1 flex flex-wrap items-center gap-x-3 font-mono text-[11px] text-ink/55">
              <span>category: {gap.category}</span>
              <span className="text-burgundy group-open:hidden">show analysis ▾</span>
              <span className="hidden text-burgundy group-open:inline">hide analysis ▴</span>
            </p>
          </div>
        </summary>

        <div className="ml-[112px] mt-4 max-w-prose space-y-5 text-[13px] leading-relaxed">
          <Section label="Why the AI flagged this" accent="neutral" body={g.whyFlagged} />
          <Section label="Fair concern — is this really uncoverable?" accent="warm" body={g.fairConcern} />
          <Section
            label={`Expert contribution — what would close the gap (asks ${g.expertPersona})`}
            accent="teal"
            body={g.expertPrompt}
          />
        </div>
      </details>
    </li>
  );
}

export function KnowledgeGapList({ gaps }: { gaps: KnowledgeGap[] }) {
  if (gaps.length === 0)
    return <p className="font-mono text-xs text-ink/55">No knowledge gaps flagged.</p>;
  return (
    <ul className="divide-y divide-slate-border/15 border-y border-slate-border/15">
      {gaps.map((gap, i) => (
        <KnowledgeGapPanel key={i} gap={gap} />
      ))}
    </ul>
  );
}

// ----- Novel syntheses: AI-proposed leap card -----------------------------

export function NovelSynthesisCard({ syn }: { syn: NovelSynthesis }) {
  return (
    <li className="py-4">
      <div className="flex items-start gap-4">
        <span
          aria-hidden
          className="mt-1 inline-flex h-6 w-20 shrink-0 items-center justify-center rounded-sm bg-teal-soft px-1.5 font-mono text-[10px] font-semibold tracking-wide text-teal"
        >
          AI-proposed
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-serif text-[15px] leading-snug text-ink">{syn.proposed_connection}</p>
          {syn.rationale && (
            <p className="mt-2 border-l-2 border-teal/40 pl-3 font-serif text-[13px] italic leading-relaxed text-ink/75">
              <span className="not-italic font-sans text-[10px] font-medium uppercase tracking-wider text-teal">
                AI&rsquo;s rationale
              </span>{' '}
              <br />
              {syn.rationale}
            </p>
          )}
          <p className="mt-2 font-mono text-[11px] text-ink/55">
            This is a leap the AI is proposing rather than citing. It needs verification before
            anyone treats it as established.
          </p>
        </div>
      </div>
    </li>
  );
}

export function NovelSynthesisList({ items }: { items: NovelSynthesis[] }) {
  if (items.length === 0)
    return <p className="font-mono text-xs text-ink/55">No novel syntheses proposed.</p>;
  return (
    <ul className="divide-y divide-slate-border/15 border-y border-slate-border/15">
      {items.map((syn, i) => (
        <NovelSynthesisCard key={i} syn={syn} />
      ))}
    </ul>
  );
}

// ----- Feasibility: per-axis row with score + expandable justification ---

function scoreColor(score: number): { bar: string; label: string } {
  if (score >= 4) return { bar: 'bg-teal', label: 'text-teal' };
  if (score >= 3) return { bar: 'bg-ink/60', label: 'text-ink/70' };
  return { bar: 'bg-burgundy', label: 'text-burgundy' };
}

function ScoreBar({ score }: { score: number }) {
  const filled = Math.round((score / 5) * 100);
  const c = scoreColor(score);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 rounded-full bg-slate-border/15">
        <div className={`h-1.5 rounded-full ${c.bar}`} style={{ width: `${filled}%` }} />
      </div>
      <span className={`font-mono text-[11px] font-semibold ${c.label}`}>{score}/5</span>
    </div>
  );
}

export function FeasibilityRow({
  axis,
  score,
  justification,
}: {
  axis: string;
  score: number;
  justification: string;
}) {
  return (
    <li className="py-3">
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 rounded-sm focus-visible:outline-none">
          <div className="min-w-0 flex-1">
            <p className="font-sans text-[14px] font-medium text-ink">
              {axis.replace(/_/g, ' ')}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <ScoreBar score={score} />
            <span className="font-mono text-[11px] text-ink/55 group-open:hidden">▾</span>
            <span className="hidden font-mono text-[11px] text-ink/55 group-open:inline">▴</span>
          </div>
        </summary>
        <p className="mt-3 max-w-prose font-serif text-[13px] leading-relaxed text-ink/75">
          {justification}
        </p>
      </details>
    </li>
  );
}

export function FeasibilityScorecard({ scores }: { scores: FeasibilityScores }) {
  const axes = Object.keys(scores.scores);
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <p className="font-sans text-[12px] font-medium uppercase tracking-wider text-ink/55">
          Feasibility
        </p>
        <p className="font-mono text-[11px] text-ink/55">overall: {scores.overall.toFixed(2)}</p>
      </div>
      <ul className="mt-3 divide-y divide-slate-border/15 border-y border-slate-border/15">
        {axes.map((axis) => (
          <FeasibilityRow
            key={axis}
            axis={axis}
            score={scores.scores[axis]}
            justification={scores.justifications[axis] ?? ''}
          />
        ))}
      </ul>
    </div>
  );
}

// ----- Reusable accent section block (mirrors biointel's Section) ---------

interface SectionProps {
  label: string;
  body: string;
  accent: 'teal' | 'warm' | 'neutral';
}

export function Section({ label, body, accent }: SectionProps) {
  const borderClass =
    accent === 'teal'
      ? 'border-teal/50'
      : accent === 'warm'
        ? 'border-burgundy/40'
        : 'border-slate-border/40';
  const labelClass =
    accent === 'teal'
      ? 'text-teal'
      : accent === 'warm'
        ? 'text-burgundy'
        : 'text-ink/60';
  return (
    <div className={`border-l-2 pl-3 ${borderClass}`}>
      <p
        className={`font-sans text-[10px] font-medium uppercase tracking-wider ${labelClass}`}
      >
        {label}
      </p>
      <p className="mt-1 font-serif text-ink/85">{body}</p>
    </div>
  );
}

// ----- Top-of-page epistemic summary --------------------------------------

export function EpistemicSummaryStrip({
  wellCovered,
  sparse,
  gaps,
  syntheses,
  warnings,
}: {
  wellCovered: number;
  sparse: number;
  gaps: number;
  syntheses: number;
  warnings: string[];
}) {
  return (
    <div className="rounded border border-slate-border/15 bg-white/60 px-5 py-4">
      <p className="font-sans text-[10px] font-medium uppercase tracking-wider text-ink/55">
        Epistemic summary
      </p>
      <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
        <Stat n={wellCovered} label="well-covered claims" intent="teal" />
        <Stat n={sparse} label="sparse-coverage claims" intent="warm" />
        <Stat n={gaps} label="researcher gaps" intent="warm" />
        <Stat n={syntheses} label="novel syntheses" intent="teal" />
      </div>
      {warnings.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2">
          {warnings.map((w, i) => (
            <li
              key={i}
              className="rounded-sm bg-burgundy-soft px-2 py-0.5 font-mono text-[10px] text-burgundy"
            >
              {w}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Stat({
  n,
  label,
  intent,
}: {
  n: number;
  label: string;
  intent: 'teal' | 'warm' | 'neutral';
}) {
  const c =
    intent === 'teal' ? 'text-teal' : intent === 'warm' ? 'text-burgundy' : 'text-ink/70';
  return (
    <div>
      <p className={`font-mono text-[20px] font-semibold ${c}`}>{n}</p>
      <p className="font-sans text-[11px] text-ink/60">{label}</p>
    </div>
  );
}

export function inlineBadgeFor(_unused?: ReactNode) {
  return InlineBadge;
}
