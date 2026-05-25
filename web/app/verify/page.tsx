'use client';

// /verify — paste any LLM-generated scientific text and verify its citations live
// against the real literature record (PubMed/Crossref/OpenAlex/arXiv/GitHub).
// Talks to /api/verify, which shells out to the `deltasci verify --json` CLI.
//
// Findings are grouped into ONE card per cited identifier: multiple verifiers
// (PubMed + OpenAlex both resolve a PMID, etc.) collapse into a single verdict with
// the individual checks shown as sub-rows — agreement is a confidence signal, not noise.

import Link from 'next/link';
import { useState } from 'react';

type Verdict =
  | 'PASS'
  | 'FABRICATED'
  | 'METADATA-MISMATCH'
  | 'UNSUPPORTED'
  | 'UNVERIFIABLE'
  | 'SKIPPED';

interface Finding {
  target_kind: string;
  target_summary: string;
  auditor_name: string;
  status: string;
  fetched_metadata: Record<string, unknown>;
  mismatch_reasons: string[];
  confidence: string;
  verdict: Verdict;
}

interface Payload {
  summary: string;
  verdicts: Record<string, number>;
  findings: Finding[];
  error?: string;
}

interface Group {
  key: string;
  claim: string;
  verdict: Verdict; // most-severe verdict across the citation's checks
  findings: Finding[];
}

interface PaperCitation {
  number: number | null;
  verdict: Verdict;
  claim: string;
  reference: string;
  resolved_title: string | null;
  note: string;
  findings: Finding[];
}

interface PaperPayload {
  counts: Record<string, number>;
  reference_count: number;
  citations: PaperCitation[];
  error?: string;
}

const FORMAT = 'text';

// A curated "AI-generated related work" snippet that exercises all three verdicts
// against real PubMed records (each with a real abstract, so the support check is vivid):
//  - PMID 34265844 — AlphaFold; the claim matches its abstract → PASS
//  - PMID 32015508 — a real SARS-CoV-2 paper, cited for an osteosarcoma-macrophage
//    claim it has nothing to do with → UNSUPPORTED (shows the actual coronavirus abstract)
//  - PMID 99999999 — no such record → FABRICATED
const DEMO_TEXT =
  'AlphaFold predicts protein three-dimensional structure directly from amino-acid ' +
  'sequence with near-experimental accuracy (PMID 34265844). M2-polarized ' +
  'tumor-associated macrophages drive osteosarcoma metastasis and immune evasion ' +
  '(PMID 32015508). Checkpoint-blockade immunotherapy doubles five-year survival in ' +
  'TFE3-fusion sarcoma (PMID 99999999).';

const VERDICT_RANK: Record<Verdict, number> = {
  FABRICATED: 0,
  'METADATA-MISMATCH': 1,
  UNSUPPORTED: 2,
  UNVERIFIABLE: 3,
  SKIPPED: 4,
  PASS: 5,
};

const VERDICT_STYLE: Record<Verdict, { sym: string; pill: string }> = {
  PASS: { sym: '✓', pill: 'bg-teal-soft text-teal' },
  FABRICATED: { sym: '✗', pill: 'bg-burgundy-soft text-burgundy' },
  'METADATA-MISMATCH': { sym: '✗', pill: 'bg-burgundy-soft text-burgundy' },
  UNSUPPORTED: { sym: '⚠', pill: 'bg-burgundy-soft text-burgundy' },
  UNVERIFIABLE: { sym: '⊘', pill: 'bg-slate-quote text-ink/60' },
  SKIPPED: { sym: '…', pill: 'bg-slate-quote text-ink/60' },
};

const MUTED_VERDICTS: Verdict[] = ['UNVERIFIABLE', 'SKIPPED'];

function str(meta: Record<string, unknown>, key: string): string {
  const v = meta[key];
  return typeof v === 'string' ? v : typeof v === 'number' ? String(v) : '';
}

function identifierLabel(f: Finding): string {
  const m = f.fetched_metadata;
  return (
    str(m, 'pmid') || str(m, 'doi') || str(m, 'arxiv') || str(m, 'id') || str(m, 'repo') || str(m, 'accession')
  );
}

// Collapse findings into one group per cited identifier; headline = most-severe verdict.
function groupFindings(findings: Finding[]): Group[] {
  const map = new Map<string, Finding[]>();
  for (const f of findings) {
    const key = identifierLabel(f) || f.target_summary;
    const arr = map.get(key);
    if (arr) arr.push(f);
    else map.set(key, [f]);
  }
  const groups: Group[] = [...map.entries()].map(([key, fs]) => ({
    key,
    // the longest target_summary is the claim sentence (vs the bare identifier string)
    claim: fs.reduce((a, f) => (f.target_summary.length > a.length ? f.target_summary : a), ''),
    verdict: fs.reduce<Verdict>(
      (best, f) => (VERDICT_RANK[f.verdict] < VERDICT_RANK[best] ? f.verdict : best),
      fs[0].verdict,
    ),
    findings: fs,
  }));
  groups.sort((a, b) => VERDICT_RANK[a.verdict] - VERDICT_RANK[b.verdict]);
  return groups;
}

function GroupCard({ g }: { g: Group }) {
  const style = VERDICT_STYLE[g.verdict] ?? VERDICT_STYLE.UNVERIFIABLE;
  const support = g.findings.find((f) => f.target_kind === 'support');
  const reasons = [...new Set(g.findings.flatMap((f) => f.mismatch_reasons))];
  // The record any verifier actually resolved (title + canonical URL) — shown on every
  // card that resolved, so the user can click straight through to the *real* page
  // (PubMed, not PMC) instead of searching the wrong database by hand.
  const resolved = g.findings.find((f) => str(f.fetched_metadata, 'url') && str(f.fetched_metadata, 'title'));
  const recordTitle = resolved ? str(resolved.fetched_metadata, 'title') : '';
  const recordUrl = resolved ? str(resolved.fetched_metadata, 'url') : '';
  const excerpt = support ? str(support.fetched_metadata, 'abstract_excerpt') : '';
  // The excerpt leads with the title (already shown in "cited record"); only surface it
  // when there's real abstract text beyond the title, so abstract-less papers don't repeat.
  const showExcerpt = excerpt.trim().length > recordTitle.trim().length + 15;

  return (
    <li className="py-4">
      <div className="flex items-start gap-4">
        <span
          aria-hidden
          className={
            'mt-0.5 inline-flex h-6 shrink-0 items-center justify-center rounded-sm px-2 font-mono text-[10px] font-semibold tracking-wide ' +
            style.pill
          }
        >
          {style.sym} {g.verdict}
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-serif text-[15px] leading-snug text-ink">{g.claim}</p>

          {/* one compact line listing every check that ran for this citation */}
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 font-mono text-[11px] text-ink/55">
            {g.findings.map((f, i) => (
              <span key={i} title={f.verdict}>
                {VERDICT_STYLE[f.verdict]?.sym} {f.auditor_name}
              </span>
            ))}
          </p>

          {reasons.map((r, i) => (
            <p key={i} className="mt-1.5 font-sans text-[13px] leading-snug text-burgundy">
              → {r}
            </p>
          ))}

          {recordTitle && recordUrl && (
            <p className="mt-1.5 font-serif text-[13px] italic leading-snug text-ink/70">
              {g.verdict === 'PASS' ? 'actual: ' : 'cited record: '}
              {recordTitle}{' '}
              <a
                href={recordUrl}
                target="_blank"
                rel="noreferrer"
                className="whitespace-nowrap font-mono text-[11px] not-italic text-teal hover:underline"
              >
                ↗ view record
              </a>
            </p>
          )}

          {g.verdict === 'UNSUPPORTED' && showExcerpt && (
            <p className="mt-1.5 border-l-2 border-burgundy/40 pl-3 font-serif text-[13px] leading-relaxed text-ink/70">
              <span className="font-sans text-[10px] font-medium uppercase tracking-wider text-burgundy">
                what the cited paper is actually about
              </span>
              <br />
              {excerpt}…
            </p>
          )}
        </div>
      </div>
    </li>
  );
}

function PaperCitationCard({ c }: { c: PaperCitation }) {
  const style = VERDICT_STYLE[c.verdict] ?? VERDICT_STYLE.UNVERIFIABLE;
  const reasons = [...new Set(c.findings.flatMap((f) => f.mismatch_reasons))];
  const resolved = c.findings.find((f) => str(f.fetched_metadata, 'url') && str(f.fetched_metadata, 'title'));
  const recordTitle = c.resolved_title || (resolved ? str(resolved.fetched_metadata, 'title') : '');
  const recordUrl = resolved ? str(resolved.fetched_metadata, 'url') : '';
  return (
    <li className="py-4">
      <div className="flex items-start gap-4">
        <span
          aria-hidden
          className={
            'mt-0.5 inline-flex h-6 shrink-0 items-center justify-center rounded-sm px-2 font-mono text-[10px] font-semibold tracking-wide ' +
            style.pill
          }
        >
          {style.sym} {c.verdict}
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-serif text-[15px] leading-snug text-ink">
            {c.number !== null && <span className="font-mono text-ink/45">[{c.number}] </span>}
            {recordTitle || c.reference.slice(0, 140)}
          </p>
          {c.findings.length > 0 && (
            <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 font-mono text-[11px] text-ink/55">
              {c.findings.map((f, i) => (
                <span key={i}>
                  {VERDICT_STYLE[f.verdict]?.sym} {f.auditor_name}
                </span>
              ))}
            </p>
          )}
          {reasons.map((r, i) => (
            <p key={i} className="mt-1.5 font-sans text-[13px] leading-snug text-burgundy">
              → {r}
            </p>
          ))}
          {c.note && <p className="mt-1.5 font-mono text-[11px] text-ink/45">{c.note}</p>}
          {c.claim && c.claim !== c.reference && (
            <p className="mt-1.5 font-serif text-[13px] italic leading-snug text-ink/60">
              cited in: “{c.claim.slice(0, 200)}{c.claim.length > 200 ? '…' : ''}”
            </p>
          )}
          {recordUrl && (
            <p className="mt-1 font-mono text-[11px]">
              <a href={recordUrl} target="_blank" rel="noreferrer" className="text-teal hover:underline">
                ↗ view record
              </a>
            </p>
          )}
        </div>
      </div>
    </li>
  );
}

function PaperResults({ payload }: { payload: PaperPayload }) {
  const rank = (v: Verdict) => VERDICT_RANK[v] ?? 9;
  const citations = [...payload.citations].sort((a, b) => rank(a.verdict) - rank(b.verdict));
  const failed =
    (payload.counts['FABRICATED'] ?? 0) +
    (payload.counts['METADATA-MISMATCH'] ?? 0) +
    (payload.counts['UNSUPPORTED'] ?? 0);
  const actionable = citations.filter((c) => !MUTED_VERDICTS.includes(c.verdict));
  const muted = citations.filter((c) => MUTED_VERDICTS.includes(c.verdict));

  return (
    <section className="mt-8">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-border/15 pb-3">
        <p className="font-sans text-[13px] text-ink/75">
          <span className={failed ? 'font-semibold text-burgundy' : 'font-semibold text-teal'}>
            {failed ? `${failed} failed audit${failed === 1 ? '' : 's'}` : 'no failed audits'}
          </span>{' '}
          across {payload.reference_count} reference{payload.reference_count === 1 ? '' : 's'}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(payload.counts)
            .sort((a, b) => rank(a[0] as Verdict) - rank(b[0] as Verdict))
            .map(([v, n]) => (
              <span
                key={v}
                className={
                  'inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 font-mono text-[10px] font-semibold ' +
                  (VERDICT_STYLE[v as Verdict]?.pill ?? 'bg-slate-quote text-ink/60')
                }
              >
                {VERDICT_STYLE[v as Verdict]?.sym} {v}: {n}
              </span>
            ))}
        </div>
      </div>

      {actionable.length > 0 && (
        <ul className="divide-y divide-slate-border/15">
          {actionable.map((c, i) => (
            <PaperCitationCard key={i} c={c} />
          ))}
        </ul>
      )}

      {muted.length > 0 && (
        <details className="group mt-4">
          <summary className="cursor-pointer list-none font-mono text-[11px] text-ink/50 hover:text-ink/70">
            <span className="group-open:hidden">+ </span>
            {muted.length} reference{muted.length === 1 ? '' : 's'} skipped or inconclusive — rate-limits,
            cap, or unresolved{' '}
            <span className="group-open:hidden">▾</span>
            <span className="hidden group-open:inline">▴</span>
          </summary>
          <ul className="mt-2 divide-y divide-slate-border/10 border-t border-slate-border/10">
            {muted.map((c, i) => (
              <li key={i} className="flex items-start gap-3 py-2">
                <span
                  aria-hidden
                  className={
                    'mt-0.5 inline-flex h-5 shrink-0 items-center rounded-sm px-1.5 font-mono text-[10px] ' +
                    (VERDICT_STYLE[c.verdict]?.pill ?? 'bg-slate-quote text-ink/60')
                  }
                >
                  {VERDICT_STYLE[c.verdict]?.sym} {c.verdict}
                </span>
                <span className="min-w-0 flex-1 font-mono text-[11px] leading-snug text-ink/55">
                  {c.number !== null ? `[${c.number}] ` : ''}
                  {(c.resolved_title || c.reference).slice(0, 100)}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

export default function VerifyPage() {
  const [text, setText] = useState('');
  const [checkSupport, setCheckSupport] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paperResult, setPaperResult] = useState<PaperPayload | null>(null);
  const [paperError, setPaperError] = useState<string | null>(null);
  const [paperLoading, setPaperLoading] = useState(false);
  const [fileName, setFileName] = useState('');

  async function verifyPaper(file: File) {
    setPaperLoading(true);
    setPaperError(null);
    setPaperResult(null);
    setResult(null);
    setError(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/api/verify-paper', { method: 'POST', body: fd });
      const payload: PaperPayload = await res.json();
      if (!res.ok || payload.error) setPaperError(payload.error ?? `request failed (${res.status})`);
      else setPaperResult(payload);
    } catch (e) {
      setPaperError(e instanceof Error ? e.message : 'upload failed');
    } finally {
      setPaperLoading(false);
    }
  }

  async function verify() {
    setLoading(true);
    setError(null);
    setResult(null);
    setPaperResult(null);
    setPaperError(null);
    try {
      const res = await fetch('/api/verify', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text, format: FORMAT, checkSupport }),
      });
      const payload: Payload = await res.json();
      if (!res.ok || payload.error) {
        setError(payload.error ?? `request failed (${res.status})`);
      } else {
        setResult(payload);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'request failed');
    } finally {
      setLoading(false);
    }
  }

  const groups = result ? groupFindings(result.findings) : [];
  const actionable = groups.filter((g) => !MUTED_VERDICTS.includes(g.verdict));
  const muted = groups.filter((g) => MUTED_VERDICTS.includes(g.verdict));
  const failedCount = groups.filter((g) =>
    (['FABRICATED', 'METADATA-MISMATCH', 'UNSUPPORTED'] as Verdict[]).includes(g.verdict),
  ).length;
  const passedCount = groups.filter((g) => g.verdict === 'PASS').length;

  const verdictCounts: Record<string, number> = {};
  for (const g of groups) verdictCounts[g.verdict] = (verdictCounts[g.verdict] ?? 0) + 1;

  return (
    <main id="main" className="mx-auto max-w-3xl px-6 pb-24 pt-12 sm:pt-16 sm:pb-32">
      <header className="mb-8 flex items-baseline justify-between">
        <p className="font-sans text-sm font-medium tracking-tight text-ink">
          <Link href="/" className="hover:text-teal">
            DeltaSci
          </Link>{' '}
          <span className="text-ink/45">verify</span>
        </p>
        <p className="font-mono text-xs text-ink/55">citation &amp; claim audit</p>
      </header>

      <h1 className="font-serif text-3xl font-bold leading-tight text-ink">
        Verify citations in any text
      </h1>
      <p className="mt-3 max-w-prose font-serif text-[15px] leading-relaxed text-ink/75">
        Paste any LLM-generated scientific text. Every cited PMID, DOI, arXiv ID, or GitHub repo is
        checked against the real record: does it exist, does its metadata match, and does the cited
        paper actually <em>support</em> the claim? No API key required.
      </p>

      <div className="mt-6">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={7}
          placeholder="Paste a related-work paragraph, hypothesis, or experiment plan with inline citations…"
          className="w-full resize-y rounded border border-slate-border/20 bg-white/70 p-4 font-serif text-[15px] leading-relaxed text-ink shadow-sm focus:border-teal focus:outline-none"
        />

        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-3">
          <button
            onClick={verify}
            disabled={loading || !text.trim()}
            className="rounded bg-teal px-4 py-2 font-sans text-sm font-medium text-cream transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? 'Verifying…' : 'Verify ▶'}
          </button>
          <button
            onClick={() => {
              setText(DEMO_TEXT);
              setResult(null);
              setError(null);
            }}
            className="font-mono text-xs text-teal hover:underline"
          >
            load demo snippet
          </button>
          {text && (
            <button
              onClick={() => {
                setText('');
                setResult(null);
                setError(null);
              }}
              className="font-mono text-xs text-ink/50 hover:text-ink"
            >
              clear
            </button>
          )}
          <label className="ml-auto flex cursor-pointer items-center gap-2 font-mono text-xs text-ink/65">
            <input
              type="checkbox"
              checked={checkSupport}
              onChange={(e) => setCheckSupport(e.target.checked)}
              className="accent-teal"
            />
            check claim-to-abstract support
          </label>
        </div>
      </div>

      <div className="mt-5 rounded border border-dashed border-slate-border/30 bg-white/40 p-4">
        <p className="font-sans text-[13px] font-medium text-ink">Or verify a whole paper (PDF)</p>
        <p className="mt-1 max-w-prose font-serif text-[13px] leading-relaxed text-ink/65">
          Real papers cite by number, with the references at the bottom. Upload a PDF and every
          numbered reference is resolved to a real record and checked in the context of the sentence
          that cites it. (First 30 references; large bibliographies are rate-limited by the public APIs.)
        </p>
        <label
          className={
            'mt-3 inline-flex items-center gap-2 rounded border border-slate-border/25 bg-ink/[0.03] px-3 py-2 font-mono text-xs text-ink ' +
            (paperLoading ? 'cursor-wait opacity-60' : 'cursor-pointer hover:bg-ink/[0.06]')
          }
        >
          {paperLoading ? 'Verifying paper…' : fileName ? `↻ ${fileName}` : '↥ Choose PDF…'}
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            disabled={paperLoading}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) {
                setFileName(f.name);
                verifyPaper(f);
              }
            }}
          />
        </label>
      </div>

      {paperError && (
        <div className="mt-6 rounded border border-burgundy/30 bg-burgundy-soft px-4 py-3 font-mono text-[13px] text-burgundy">
          {paperError}
        </div>
      )}

      {paperResult && <PaperResults payload={paperResult} />}

      {error && (
        <div className="mt-6 rounded border border-burgundy/30 bg-burgundy-soft px-4 py-3 font-mono text-[13px] text-burgundy">
          {error}
        </div>
      )}

      {result && (
        <section className="mt-8">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-border/15 pb-3">
            <p className="font-sans text-[13px] text-ink/75">
              {groups.length === 0 ? (
                'No verifiable citations found in the text.'
              ) : failedCount ? (
                <>
                  <span className="font-semibold text-burgundy">
                    {failedCount} failed audit{failedCount === 1 ? '' : 's'}
                  </span>{' '}
                  across {groups.length} citation{groups.length === 1 ? '' : 's'}
                </>
              ) : passedCount ? (
                <>
                  <span className="font-semibold text-teal">all {groups.length} citations passed</span>
                </>
              ) : (
                'No failed audits — but nothing could be positively verified either.'
              )}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(verdictCounts)
                .sort((a, b) => VERDICT_RANK[a[0] as Verdict] - VERDICT_RANK[b[0] as Verdict])
                .map(([v, n]) => (
                  <span
                    key={v}
                    className={
                      'inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 font-mono text-[10px] font-semibold ' +
                      (VERDICT_STYLE[v as Verdict]?.pill ?? 'bg-slate-quote text-ink/60')
                    }
                  >
                    {VERDICT_STYLE[v as Verdict]?.sym} {v}: {n}
                  </span>
                ))}
            </div>
          </div>

          {actionable.length > 0 && (
            <ul className="divide-y divide-slate-border/15">
              {actionable.map((g) => (
                <GroupCard key={g.key} g={g} />
              ))}
            </ul>
          )}

          {muted.length > 0 && (
            <details className="group mt-4">
              <summary className="cursor-pointer list-none font-mono text-[11px] text-ink/50 hover:text-ink/70">
                <span className="group-open:hidden">+ </span>
                {muted.length} citation{muted.length === 1 ? '' : 's'} skipped or inconclusive —
                rate-limits, network, or too little to judge{' '}
                <span className="group-open:hidden">▾</span>
                <span className="hidden group-open:inline">▴</span>
              </summary>
              <ul className="mt-2 divide-y divide-slate-border/10 border-t border-slate-border/10">
                {muted.map((g) => (
                  <li key={g.key} className="flex items-start gap-3 py-2">
                    <span
                      aria-hidden
                      className={
                        'mt-0.5 inline-flex h-5 shrink-0 items-center rounded-sm px-1.5 font-mono text-[10px] ' +
                        (VERDICT_STYLE[g.verdict]?.pill ?? 'bg-slate-quote text-ink/60')
                      }
                    >
                      {VERDICT_STYLE[g.verdict]?.sym} {g.verdict}
                    </span>
                    <span className="min-w-0 flex-1 font-mono text-[11px] leading-snug text-ink/55">
                      {g.key} — {g.claim.slice(0, 90)}
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}
    </main>
  );
}
