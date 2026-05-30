'use client';

// /workflow — the goal-first front door to the verify·scan·gap suite.
// You pick what you're doing; the right components run underneath in one pass:
//   grant  → verify + scan + gap        paper  → verify + scan
//   review → verify + scan + draft      ideate → scan + gap + directions
// Talks to /api/workflow, which shells out to `deltasci workflow <goal> --json`.

import Link from 'next/link';
import { useState } from 'react';

type Goal = 'grant' | 'paper' | 'review' | 'ideate';
type Verdict = 'PASS' | 'FABRICATED' | 'METADATA-MISMATCH' | 'UNSUPPORTED' | 'UNVERIFIABLE' | 'SKIPPED';

interface ScanHit {
  source: string;
  title: string;
  authors: string[];
  year: string;
  venue: string;
  url: string;
  score: number;
}
interface ScanPayload {
  query: string;
  terms: string[];
  counts: Record<string, number>;
  hits: ScanHit[];
}
interface GapPayload {
  classification: 'CROWDED' | 'CONTESTED' | 'OPEN' | 'INCONCLUSIVE';
  label: string;
  top_overlap: number;
  n_close: number;
  thin: boolean;
  retrieval_ok: boolean;
  failed_sources: string[];
  covered_terms: string[];
  novel_terms: string[];
  narrative: string | null;
  scan: ScanPayload;
}
interface SnippetFinding {
  target_summary: string;
  auditor_name: string;
  verdict: Verdict;
}
interface SnippetVerify {
  summary: string;
  verdicts: Record<string, number>;
  findings: SnippetFinding[];
}
interface PaperCitation {
  number: number | null;
  verdict: Verdict;
  reference: string;
  resolved_title: string | null;
}
interface PaperVerify {
  counts: Record<string, number>;
  reference_count: number;
  citations: PaperCitation[];
}
interface WorkflowPayload {
  goal: Goal;
  goal_label: string;
  steps: string[];
  headline: string;
  generated: { review?: string; ideate?: string };
  notes: string[];
  verify?: SnippetVerify | PaperVerify;
  gap?: GapPayload;
  scan?: ScanPayload;
  error?: string;
}

const GOALS: { id: Goal; label: string; steps: string; blurb: string; needsLlm: boolean }[] = [
  {
    id: 'grant',
    label: 'Writing a grant',
    steps: 'verify · scan · gap',
    blurb: 'Are my citations real, is the space still open, and what prior art must I cite?',
    needsLlm: false,
  },
  {
    id: 'paper',
    label: 'Submitting a paper',
    steps: 'verify · scan',
    blurb: 'Are my citations real, and what will reviewers compare me against?',
    needsLlm: false,
  },
  {
    id: 'review',
    label: 'Reviewing a paper',
    steps: 'verify · scan · draft review',
    blurb: 'Audit their citations, surface missing prior art, draft a structured review.',
    needsLlm: true,
  },
  {
    id: 'ideate',
    label: 'Ideating',
    steps: 'scan · gap · directions',
    blurb: 'Where is the white space, and what concrete directions are worth trying?',
    needsLlm: true,
  },
];

const RANK: Record<Verdict, number> = {
  FABRICATED: 0,
  'METADATA-MISMATCH': 1,
  UNSUPPORTED: 2,
  UNVERIFIABLE: 3,
  SKIPPED: 4,
  PASS: 5,
};
const PROBLEM = new Set<Verdict>(['FABRICATED', 'METADATA-MISMATCH', 'UNSUPPORTED']);
const VERDICT_PILL: Record<Verdict, string> = {
  PASS: 'bg-teal-soft text-teal',
  FABRICATED: 'bg-burgundy-soft text-burgundy',
  'METADATA-MISMATCH': 'bg-burgundy-soft text-burgundy',
  UNSUPPORTED: 'bg-burgundy-soft text-burgundy',
  UNVERIFIABLE: 'bg-slate-quote text-ink/60',
  SKIPPED: 'bg-slate-quote text-ink/60',
};
const GAP_PILL: Record<GapPayload['classification'], string> = {
  CROWDED: 'bg-burgundy-soft text-burgundy',
  CONTESTED: 'bg-amber-100 text-amber-800',
  OPEN: 'bg-teal-soft text-teal',
  INCONCLUSIVE: 'bg-slate-quote text-ink/60',
};

function isPaperVerify(v: SnippetVerify | PaperVerify): v is PaperVerify {
  return 'citations' in v;
}

function verifyCounts(v: SnippetVerify | PaperVerify): Record<string, number> {
  return isPaperVerify(v) ? v.counts : v.verdicts;
}

function verifyProblems(v: SnippetVerify | PaperVerify): { verdict: Verdict; text: string }[] {
  if (isPaperVerify(v)) {
    return v.citations
      .filter((c) => PROBLEM.has(c.verdict))
      .map((c) => ({ verdict: c.verdict, text: (c.resolved_title || c.reference).slice(0, 150) }))
      .sort((a, b) => RANK[a.verdict] - RANK[b.verdict]);
  }
  const seen = new Map<string, { verdict: Verdict; text: string }>();
  for (const f of v.findings) {
    if (!PROBLEM.has(f.verdict)) continue;
    const prev = seen.get(f.target_summary);
    if (!prev || RANK[f.verdict] < RANK[prev.verdict])
      seen.set(f.target_summary, { verdict: f.verdict, text: f.target_summary.slice(0, 200) });
  }
  return [...seen.values()].sort((a, b) => RANK[a.verdict] - RANK[b.verdict]);
}

function CountPills({ counts }: { counts: Record<string, number> }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {Object.entries(counts)
        .sort((a, b) => (RANK[a[0] as Verdict] ?? 9) - (RANK[b[0] as Verdict] ?? 9))
        .map(([v, n]) => (
          <span
            key={v}
            className={
              'inline-flex items-center rounded-sm px-1.5 py-0.5 font-mono text-[10px] font-semibold ' +
              (VERDICT_PILL[v as Verdict] ?? 'bg-slate-quote text-ink/60')
            }
          >
            {v}: {n}
          </span>
        ))}
    </div>
  );
}

function CitationsPanel({ verify }: { verify: SnippetVerify | PaperVerify }) {
  const counts = verifyCounts(verify);
  const problems = verifyProblems(verify);
  const failed = (counts.FABRICATED ?? 0) + (counts['METADATA-MISMATCH'] ?? 0) + (counts.UNSUPPORTED ?? 0);
  return (
    <section className="mt-7">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-border/15 pb-2">
        <h2 className="font-sans text-[13px] font-semibold uppercase tracking-wider text-ink/70">
          ▶ Citations
        </h2>
        <CountPills counts={counts} />
      </div>
      <p className="mt-2 font-sans text-[13px] text-ink/75">
        {failed ? (
          <span className="font-semibold text-burgundy">{failed} citation{failed === 1 ? '' : 's'} failed audit</span>
        ) : (
          <span className="font-semibold text-teal">no failed audits</span>
        )}
        {'  '}
        <Link href="/verify" className="ml-2 font-mono text-[11px] text-teal hover:underline">
          open full verifier ↗
        </Link>
      </p>
      {problems.length > 0 && (
        <ul className="mt-2 space-y-2">
          {problems.slice(0, 8).map((p, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className={'mt-0.5 shrink-0 rounded-sm px-1.5 font-mono text-[10px] font-semibold ' + VERDICT_PILL[p.verdict]}>
                {p.verdict}
              </span>
              <span className="min-w-0 flex-1 font-serif text-[14px] leading-snug text-ink">{p.text}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function PriorArtPanel({ gap, scan }: { gap?: GapPayload; scan?: ScanPayload }) {
  const hits = gap ? gap.scan.hits : (scan?.hits ?? []);
  return (
    <section className="mt-7">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-border/15 pb-2">
        <h2 className="font-sans text-[13px] font-semibold uppercase tracking-wider text-ink/70">
          ▶ Prior art{gap ? ' + gap' : ''}
        </h2>
        {gap && (
          <span className={'rounded-sm px-2 py-0.5 font-mono text-[11px] font-semibold ' + GAP_PILL[gap.classification]}>
            {gap.classification}
          </span>
        )}
      </div>

      {gap && (
        <div className="mt-2 space-y-1.5">
          <p className="font-serif text-[14px] text-ink/80">{gap.label}</p>
          <p className="font-mono text-[11px] text-ink/55">
            closest overlap {Math.round(gap.top_overlap * 100)}% · {gap.n_close} close · {hits.length} retrieved
            {gap.thin && <span className="text-burgundy"> · ⚠ thin evidence</span>}
          </p>
          {gap.failed_sources?.length > 0 && (
            <p className="font-mono text-[11px] text-burgundy">
              ⚠ incomplete coverage — no response from {gap.failed_sources.join(', ')}
              {gap.classification === 'INCONCLUSIVE' ? '; held back from calling the space open.' : '.'}
            </p>
          )}
          {gap.novel_terms.length > 0 && (
            <p className="font-sans text-[12px] text-ink/70">
              <span className="text-ink/45">distinguishing terms: </span>
              {gap.novel_terms.slice(0, 8).join(', ')}
            </p>
          )}
          {gap.narrative && (
            <p className="mt-1.5 whitespace-pre-wrap border-l-2 border-teal/40 pl-3 font-serif text-[13px] leading-relaxed text-ink/75">
              {gap.narrative}
            </p>
          )}
        </div>
      )}

      {hits.length > 0 ? (
        <ol className="mt-3 space-y-2.5">
          {hits.slice(0, 8).map((h, i) => (
            <li key={i} className="flex gap-3">
              <span className="mt-0.5 font-mono text-[11px] text-ink/40">{i + 1}.</span>
              <div className="min-w-0 flex-1">
                <p className="font-serif text-[14px] leading-snug text-ink">
                  <a href={h.url} target="_blank" rel="noreferrer" className="hover:text-teal hover:underline">
                    {h.title}
                  </a>{' '}
                  <span className="font-mono text-[10px] text-ink/45">({Math.round(h.score * 100)}%)</span>
                </p>
                <p className="font-mono text-[11px] text-ink/50">
                  {[h.source, h.authors.slice(0, 2).join(', '), h.year, h.venue].filter(Boolean).join(' · ')}
                </p>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-3 font-serif text-[13px] italic text-ink/55">
          No prior art retrieved — your terms may be very niche, or the public APIs were rate-limited.
        </p>
      )}
    </section>
  );
}

function GeneratedPanel({ title, text }: { title: string; text: string }) {
  return (
    <section className="mt-7">
      <h2 className="border-b border-slate-border/15 pb-2 font-sans text-[13px] font-semibold uppercase tracking-wider text-ink/70">
        ▶ {title}
      </h2>
      <div className="mt-2 whitespace-pre-wrap font-serif text-[14px] leading-relaxed text-ink/85">{text}</div>
    </section>
  );
}

export default function WorkflowPage() {
  const [goal, setGoal] = useState<Goal | null>(null);
  const [text, setText] = useState('');
  const [isPaper, setIsPaper] = useState(false);
  const [useLlm, setUseLlm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WorkflowPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const goalMeta = GOALS.find((g) => g.id === goal);

  async function run() {
    if (!goal) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch('/api/workflow', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          goal,
          text,
          paper: isPaper,
          llm: useLlm ? 'anthropic' : undefined,
          limit: 8,
        }),
      });
      const payload: WorkflowPayload = await res.json();
      if (!res.ok || payload.error) setError(payload.error ?? `request failed (${res.status})`);
      else setResult(payload);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'request failed');
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setGoal(null);
    setText('');
    setIsPaper(false);
    setUseLlm(false);
    setResult(null);
    setError(null);
  }

  return (
    <main id="main" className="mx-auto max-w-3xl px-6 pb-24 pt-12 sm:pt-16 sm:pb-32">
      <header className="mb-8 flex items-baseline justify-between">
        <p className="font-sans text-sm font-medium tracking-tight text-ink">
          <Link href="/" className="hover:text-teal">
            DeltaSci
          </Link>{' '}
          <span className="text-ink/45">workflow</span>
        </p>
        <p className="font-mono text-xs text-ink/55">verify · scan · gap</p>
      </header>

      {/* Step 1 — pick a goal */}
      {!goal && (
        <>
          <h1 className="font-serif text-3xl font-bold leading-tight text-ink">What are you working on?</h1>
          <p className="mt-3 max-w-prose font-serif text-[15px] leading-relaxed text-ink/75">
            Pick a goal and the right checks run together in one pass — your citations against the real
            record, the closest existing work, and where the white space is. Verify, scan, and gap need no
            API key.
          </p>
          <div className="mt-7 grid gap-3 sm:grid-cols-2">
            {GOALS.map((g) => (
              <button
                key={g.id}
                onClick={() => setGoal(g.id)}
                className="group rounded-lg border border-slate-border/20 bg-white/60 p-5 text-left transition hover:border-teal hover:bg-white/90 hover:shadow-sm"
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-sans text-base font-semibold text-ink group-hover:text-teal">{g.label}</span>
                  <span className="font-mono text-[10px] text-ink/45">{g.steps}</span>
                </div>
                <p className="mt-1.5 font-serif text-[13px] leading-relaxed text-ink/70">{g.blurb}</p>
              </button>
            ))}
          </div>
        </>
      )}

      {/* Step 2 — input + run */}
      {goal && (
        <>
          <div className="flex items-baseline justify-between">
            <h1 className="font-serif text-3xl font-bold leading-tight text-ink">{goalMeta?.label}</h1>
            <button onClick={reset} className="font-mono text-xs text-ink/50 hover:text-ink">
              ← change goal
            </button>
          </div>
          <p className="mt-2 font-mono text-xs text-ink/55">runs: {goalMeta?.steps}</p>

          <div className="mt-5">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={8}
              placeholder={
                goal === 'ideate'
                  ? 'Describe your research idea or hypothesis…'
                  : goal === 'review'
                    ? "Paste the paper's abstract + body (with its references) to review…"
                    : 'Paste your proposal / abstract with its citations…'
              }
              className="w-full resize-y rounded border border-slate-border/20 bg-white/70 p-4 font-serif text-[15px] leading-relaxed text-ink shadow-sm focus:border-teal focus:outline-none"
            />
            <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-3">
              <button
                onClick={run}
                disabled={loading || !text.trim()}
                className="rounded bg-teal px-4 py-2 font-sans text-sm font-medium text-cream transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {loading ? 'Running…' : 'Run ▶'}
              </button>
              {goal !== 'ideate' && (
                <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-ink/65">
                  <input type="checkbox" checked={isPaper} onChange={(e) => setIsPaper(e.target.checked)} className="accent-teal" />
                  input is a whole paper (parse its bibliography)
                </label>
              )}
              {goalMeta?.needsLlm && (
                <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-ink/65">
                  <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} className="accent-teal" />
                  {goal === 'review' ? 'draft the review' : 'generate directions'} with an LLM (needs a key on the server)
                </label>
              )}
            </div>
            {goalMeta?.needsLlm && !useLlm && (
              <p className="mt-2 font-serif text-[12px] italic text-ink/50">
                Without an LLM, the deterministic steps still run — you just won&apos;t get the generated{' '}
                {goal === 'review' ? 'review draft' : 'directions'}.
              </p>
            )}
          </div>

          {error && (
            <div className="mt-6 rounded border border-burgundy/30 bg-burgundy-soft px-4 py-3 font-mono text-[13px] text-burgundy">
              {error}
            </div>
          )}

          {result && (
            <div className="mt-8">
              <div className="rounded-lg border border-slate-border/20 bg-ink/[0.02] px-4 py-3">
                <p className="font-sans text-[11px] font-semibold uppercase tracking-wider text-ink/50">
                  {result.goal_label} · {result.steps.join(' + ')}
                </p>
                <p className="mt-1 font-serif text-[15px] text-ink">{result.headline}</p>
              </div>

              {result.verify && <CitationsPanel verify={result.verify} />}
              {(result.gap || result.scan) && <PriorArtPanel gap={result.gap} scan={result.scan} />}
              {result.generated.review && <GeneratedPanel title="Draft review" text={result.generated.review} />}
              {result.generated.ideate && <GeneratedPanel title="New directions" text={result.generated.ideate} />}

              {result.notes.length > 0 && (
                <ul className="mt-6 space-y-1">
                  {result.notes.map((n, i) => (
                    <li key={i} className="font-mono text-[11px] text-ink/50">
                      ⓘ {n}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
    </main>
  );
}
