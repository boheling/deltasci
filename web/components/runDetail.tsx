// Single-run review surface. Used by both the root page (when DELTASCI_RUN_DIR
// is set or as fallback) and the dynamic /runs/[slug] route.

import Link from 'next/link';

import {
  AuditableClaimList,
  EpistemicSummaryStrip,
  FeasibilityScorecard,
  KnowledgeGapList,
  NovelSynthesisList,
  Section,
} from './auditable';
import { Cell, Note, NotebookHeader, Badge, RoleBadge, InlineBadge } from './notebook';
import { AuditView, ChallengeView, ProtocolView, RisksView } from './v2sections';
import { NotebookView } from './notebookView';
import { Mermaid } from './mermaid';
import type { DeltaRun, EvidenceItem } from '@/lib/types';

export function RunDetail({ run, projectHref }: { run: DeltaRun; projectHref?: string | null }) {
  const h = run.hypothesis;
  const es = h.epistemic_summary;

  const wellCovered: EvidenceItem[] = h.evidence_trail.filter((e) => e.coverage === 'well-covered');
  const sparse: EvidenceItem[] = h.evidence_trail.filter((e) => e.coverage === 'sparse');

  return (
    <main id="main" className="mx-auto max-w-3xl px-6 pb-24 pt-12 sm:pt-16 sm:pb-32">
      <header className="mb-10 flex items-baseline justify-between">
        <p className="font-sans text-sm font-medium tracking-tight text-ink">
          <Link href={projectHref ?? '/'} className="hover:text-teal">
            {projectHref ? '← project' : 'DeltaSci'}
          </Link>{' '}
          <span className="text-ink/45">review</span>
        </p>
        <div className="flex items-baseline gap-4">
          <Link href="/verify" className="font-mono text-xs text-teal hover:underline">
            verify text →
          </Link>
          <p className="font-mono text-xs text-ink/55">
            pack: {run.pack} · {h.metadata.llm_provider} / {h.metadata.model}
          </p>
        </div>
      </header>

      <NotebookHeader
        title={h.title}
        subtitle={
          <>
            One hypothesis-stage co-reasoning run on the <code className="font-mono text-[14px]">{run.pack}</code>{' '}
            pack. Every claim labeled by AI-confidence, every gap handed back to the researcher,
            every novel leap explicitly proposed rather than asserted.
          </>
        }
        badges={
          <>
            <Badge>idea: {truncate(run.idea, 90)}</Badge>
            <Badge intent="teal">claims: {run.grounding.total_claims}</Badge>
            <Badge intent="warm">gaps: {run.grounding.total_knowledge_gaps}</Badge>
            <Badge intent="teal">novel: {run.grounding.total_novel_syntheses}</Badge>
            <Badge intent={run.grounding.total_violations === 0 ? 'teal' : 'warm'}>
              violations: {run.grounding.total_violations}
            </Badge>
          </>
        }
      />

      <div className="mt-8">
        <EpistemicSummaryStrip
          wellCovered={es.well_covered_count}
          sparse={es.sparse_count}
          gaps={es.knowledge_gap_count}
          syntheses={es.novel_synthesis_count}
          warnings={es.warnings}
        />
      </div>

      <Cell n="H" title="The hypothesis" accent="teal">
        <Note>
          <p className="text-[15px]">{h.statement}</p>
        </Note>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <Section label="Mechanism" accent="neutral" body={h.domain_grounding.mechanism} />
          <Section label="Unmet need" accent="neutral" body={h.domain_grounding.unmet_need} />
          <Section label="Expected impact" accent="neutral" body={h.domain_grounding.expected_impact} />
        </div>
      </Cell>

      <Cell n="F" title="Falsifiability — what it would take to disbelieve this" accent="warm">
        <div className="space-y-4">
          <Section label="Prediction" accent="teal" body={h.falsifiability.prediction} />
          <Section label="Threshold" accent="neutral" body={h.falsifiability.threshold} />
          <Section label="Null outcome" accent="warm" body={h.falsifiability.null_outcome} />
        </div>
      </Cell>

      <Cell n="T" title="Technical approach">
        <div className="space-y-4">
          <Section label="Core method" accent="neutral" body={h.technical_approach.core_method} />
          <Section label="Key innovation" accent="teal" body={h.technical_approach.key_innovation} />
          <Section label="Implementation path" accent="neutral" body={h.technical_approach.implementation_path} />
        </div>
      </Cell>

      {run.rounds.map((round, i) => (
        <Cell
          key={round.id}
          n={i + 1}
          title={`${round.id} — ${round.speaker.replace(/_/g, ' ')}`}
          accent={round.role === 'domain' ? 'teal' : round.role === 'engineer' ? 'warm' : 'neutral'}
          meta={
            <>
              <RoleBadge role={round.role} />
              {run.grounding.by_round[i] && (
                <>
                  <InlineBadge intent="teal">{run.grounding.by_round[i].claims} claims</InlineBadge>
                  <InlineBadge intent="warm">{run.grounding.by_round[i].knowledge_gaps} gaps</InlineBadge>
                  <InlineBadge intent="neutral">{run.grounding.by_round[i].novel_syntheses} novel</InlineBadge>
                </>
              )}
            </>
          }
        >
          <RoundProse prose={round.prose} />
        </Cell>
      ))}

      <Cell n="E1" title="Evidence trail · AI-confident foundations" accent="teal">
        <Note>
          <p className="text-[13px]">
            Claims the AI cited from well-covered training. Spot-check that the source actually
            says this — that&rsquo;s the audit lever.
          </p>
        </Note>
        <div className="mt-4">
          <AuditableClaimList items={wellCovered} />
        </div>
      </Cell>

      <Cell n="E2" title="Evidence trail · Likely-reliable, please verify" accent="warm">
        <Note>
          <p className="text-[13px]">
            Claims the AI flagged with sparser training coverage. Specific numbers, recent
            publication patterns, exact feature lists — verify before relying on.
          </p>
        </Note>
        <div className="mt-4">
          <AuditableClaimList items={sparse} />
        </div>
      </Cell>

      <Cell n="K" title="Researcher knowledge required" accent="warm">
        <Note>
          <p className="text-[13px]">
            What the AI explicitly does not know. Each gap expands into a four-section panel:
            why the AI flagged it, whether the gap is real or a corpus shortfall, and a specific
            question for the right kind of expert. This is where the AI hands the steering wheel
            back.
          </p>
        </Note>
        <div className="mt-4">
          <KnowledgeGapList gaps={h.knowledge_gaps} />
        </div>
      </Cell>

      <Cell n="N" title="Novel syntheses — the AI&rsquo;s leaps">
        <Note>
          <p className="text-[13px]">
            Connections the AI is proposing rather than citing. These are the parts of the
            hypothesis that need an expert sanity-check before they get treated as established.
          </p>
        </Note>
        <div className="mt-4">
          <NovelSynthesisList items={h.novel_syntheses} />
        </div>
      </Cell>

      <Cell n="S" title="Feasibility scorecard">
        <FeasibilityScorecard scores={h.feasibility_scores} />
      </Cell>

      {run.protocol && (
        <Cell n="P" title="Experiment plan" accent="teal">
          <Note>
            <p className="text-[13px]">
              Concrete, execution-ready protocol generated from the synthesized hypothesis. Data
              acquisition, ordered steps with method citations, evaluation criteria mirroring the
              falsifiability clause, compute requirements, timeline. Method citations have been
              audited against PubMed / Crossref / arXiv / GitHub / GEO — see the audit panel for
              verification status.
            </p>
          </Note>
          <div className="mt-4">
            <ProtocolView plan={run.protocol} />
          </div>
        </Cell>
      )}

      {run.postexec && (
        <Cell n="X" title="Execution Update" accent="teal">
          <Note>
            <p className="text-[13px]">
              Auto-generated by{' '}
              <code className="font-mono">deltasci postexec</code> from the executed
              notebook. Risk badges are deterministic — for {`${run.postexec.report.risk_statuses.filter((r) => r.status === 'resolved').length}`}{' '}
              <strong>resolved</strong>, the table cites the cell that resolved it; for{' '}
              {`${run.postexec.report.risk_statuses.filter((r) => r.status === 'confirmed').length}`}{' '}
              <strong>confirmed</strong>, the failure mode actually happened with the measured
              numbers shown.
            </p>
          </Note>

          <div className="mt-4 space-y-4">
            {run.postexec.report.achievements.length > 0 && (
              <div>
                <h4 className="font-sans text-[12px] font-semibold uppercase tracking-wider text-ink/70">
                  Headline achievements
                </h4>
                <ul className="mt-2 space-y-1 text-[13px]">
                  {run.postexec.report.achievements.map((a, i) => (
                    <li key={i}>
                      <strong>{a.headline}</strong>
                      {a.cell_index !== null && (
                        <span className="text-ink/55"> (cell {a.cell_index})</span>
                      )}
                      {a.detail && <div className="text-ink/70 ml-3">{a.detail}</div>}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {run.postexec.report.risk_statuses.length > 0 && (
              <div>
                <h4 className="font-sans text-[12px] font-semibold uppercase tracking-wider text-ink/70">
                  Risk register · post-execution status
                </h4>
                <table className="mt-2 w-full border-collapse text-[12px]">
                  <thead>
                    <tr>
                      {['ID', 'Severity', 'Status', 'Evidence'].map((h) => (
                        <th key={h} className="border border-slate-border/30 bg-ink/5 px-2 py-1 text-left font-sans font-semibold">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {run.postexec.report.risk_statuses.map((rs) => {
                      const badge =
                        rs.status === 'resolved' ? '✅ resolved'
                        : rs.status === 'confirmed' ? '🔴 confirmed'
                        : rs.status === 'partly_resolved' ? '🟠 partly resolved'
                        : rs.status === 'still_open' ? '🟡 still open'
                        : '❔ unknown';
                      return (
                        <tr key={rs.risk_id}>
                          <td className="border border-slate-border/20 px-2 py-1 font-mono">{rs.risk_id}</td>
                          <td className="border border-slate-border/20 px-2 py-1">{rs.severity}</td>
                          <td className="border border-slate-border/20 px-2 py-1">{badge}</td>
                          <td className="border border-slate-border/20 px-2 py-1 text-ink/75">
                            {rs.evidence_snippet || rs.rationale}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {run.postexec.report.metrics.length > 0 && (
              <details className="rounded border border-slate-border/15 bg-white/60 p-3">
                <summary className="cursor-pointer font-sans text-[12px] font-medium text-ink/70">
                  Measured metrics ({run.postexec.report.metrics.length})
                </summary>
                <table className="mt-3 border-collapse text-[12px]">
                  <thead>
                    <tr>
                      {['Metric', 'Value', 'Cell'].map((h) => (
                        <th key={h} className="border border-slate-border/30 bg-ink/5 px-2 py-1 text-left font-sans font-semibold">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {run.postexec.report.metrics.map((m, i) => (
                      <tr key={i}>
                        <td className="border border-slate-border/20 px-2 py-1 font-mono">{m.name}</td>
                        <td className="border border-slate-border/20 px-2 py-1 font-mono">{m.value.toFixed(4)}</td>
                        <td className="border border-slate-border/20 px-2 py-1 font-mono">{m.cell_index}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            )}

            {run.postexec.report.new_issues.length > 0 && (
              <div>
                <h4 className="font-sans text-[12px] font-semibold uppercase tracking-wider text-ink/70">
                  New issues surfaced
                </h4>
                <ul className="mt-2 space-y-1 text-[13px]">
                  {run.postexec.report.new_issues.map((ni, i) => (
                    <li key={i}>
                      <span className="text-ink/55">(cell {ni.cell_index})</span>{' '}
                      <strong>{ni.kind}</strong> — {ni.message}
                      {ni.snippet && <code className="ml-2 rounded-sm bg-ink/8 px-1 font-mono text-[11px]">{ni.snippet}</code>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Cell>
      )}

      {run.diagrams && (run.diagrams.dataFlow || run.diagrams.protocolSeq || run.diagrams.schema) && (
        <Cell n="D" title="Diagrams" accent="teal">
          <Note>
            <p className="text-[13px]">
              Mermaid sources generated deterministically from the experiment plan
              (<code className="font-mono">deltasci diagrams &lt;run-dir&gt;</code>).
              Concept-only — no AI-generated raster figures, since hallucinated axis labels
              and bands would defeat the audit pillar. Click &ldquo;view mermaid source&rdquo;
              under each diagram to see the text.
            </p>
          </Note>
          <div className="mt-4 space-y-4">
            {run.diagrams.dataFlow && (
              <Mermaid source={run.diagrams.dataFlow} label="Data flow" />
            )}
            {run.diagrams.protocolSeq && (
              <Mermaid source={run.diagrams.protocolSeq} label="Protocol sequence" />
            )}
            {run.diagrams.schema && (
              <Mermaid source={run.diagrams.schema} label="Graph schema" />
            )}
          </div>
        </Cell>
      )}

      {run.notebook && (
        <Cell n="NB" title="Executable scaffold notebook" accent="teal">
          <Note>
            <p className="text-[13px]">
              Generated from the experiment plan above. Each protocol step becomes a
              markdown+code cell pair; the scaffold ends with a falsifiability check that
              raises if your measured metric does not clear the hypothesis threshold.
              <strong> The AI did not run this notebook</strong> — it&rsquo;s a parameterized
              starting point. Run locally with{' '}
              <code className="font-mono">jupyter lab notebook.ipynb</code> after{' '}
              <code className="font-mono">pip install -r requirements.txt</code>.
            </p>
          </Note>
          <div className="mt-4">
            <NotebookView bundle={run.notebook} />
          </div>
        </Cell>
      )}

      {run.risks && (
        <Cell n="R" title="Risk register" accent="warm">
          <Note>
            <p className="text-[13px]">
              Failure modes that would invalidate the hypothesis or experiment plan, ranked by
              severity. Each risk names the failure mode, classifies category and severity, and
              proposes a concrete mitigation. Counter-evidence citations are audit-checked.
            </p>
          </Note>
          <div className="mt-4">
            <RisksView register={run.risks} />
          </div>
        </Cell>
      )}

      {run.challenge && (
        <Cell n="C" title="Adversarial challenge" accent="warm">
          <Note>
            <p className="text-[13px]">
              Independent second-opinion findings. The challenger reads the hypothesis + plan +
              risks and tries to break them. Findings are kind-classified, severity-ranked, with
              evidence citations that flow through the same audit pillar — so a fabricated
              counter-evidence URL gets caught the same way the synthesis stage&rsquo;s citations
              are caught.
            </p>
          </Note>
          <div className="mt-4">
            <ChallengeView report={run.challenge} />
          </div>
        </Cell>
      )}

      {run.iterations.length > 0 && (
        <Cell n="I" title={`Iteration history — ${run.iterations.length} archived`} accent="warm">
          <Note>
            <p className="text-[13px]">
              This run has been re-run via <code className="font-mono">--iterate-on</code>;
              previous versions are archived under <code className="font-mono">09_iterations/</code>{' '}
              with their full audit lineage preserved. The current top-level reflects the latest
              iteration; this section shows what came before.
            </p>
          </Note>
          <ol className="mt-4 space-y-2">
            {run.iterations.map((iter) => (
              <li key={iter.version} className="rounded border border-slate-border/15 bg-white/60 p-3">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span className="font-mono text-[12px] font-semibold text-warm">{iter.version}</span>
                  <span className="font-mono text-[10px] text-ink/55">
                    {iter.generated_at?.slice(0, 16).replace('T', ' ')}
                  </span>
                  {iter.audit_failed > 0 ? (
                    <span className="rounded-sm bg-burgundy text-cream px-1.5 py-0.5 font-mono text-[10px] font-semibold">
                      ✗ {iter.audit_failed} failed audit
                    </span>
                  ) : (
                    <span className="rounded-sm bg-teal text-cream px-1.5 py-0.5 font-mono text-[10px] font-semibold">
                      ✓ {iter.audit_verified} verified
                    </span>
                  )}
                </div>
                <p className="mt-1 font-serif text-[13px] leading-snug text-ink">{iter.title}</p>
                <p className="mt-1 font-mono text-[10px] text-ink/55">
                  evidence: {iter.well_covered} well-covered · {iter.sparse} sparse ·{' '}
                  {iter.knowledge_gaps} gaps · {iter.novel_syntheses} syntheses
                </p>
              </li>
            ))}
          </ol>
        </Cell>
      )}

      {run.audit && (
        <Cell n="A" title="Citation audit" accent="teal">
          <Note>
            <p className="text-[13px]">
              Every PMID, DOI, arXiv ID, GitHub repo, HuggingFace ID, and GEO accession in the
              hypothesis evidence trail, the protocol method citations, the risk counter-evidence,
              and the challenger evidence has been resolved against the real record.{' '}
              <strong>Failed audits surface here</strong>, with both what the AI claimed and what
              was actually at the cited identifier — exactly what the BioIntel{' '}
              <em>faithfulness: ok</em> failure should have shown.
            </p>
          </Note>
          <div className="mt-4">
            <AuditView report={run.audit} />
          </div>
        </Cell>
      )}

      <footer className="mt-16 border-t border-slate-border/20 pt-8 text-xs text-ink/60">
        <p>
          Generated {h.metadata.generated_at} · deltasci v{h.metadata.deltasci_version} · pack{' '}
          {h.metadata.pack_name} v{h.metadata.pack_version} · {h.metadata.num_rounds} rounds ·{' '}
          {h.metadata.llm_provider} / {h.metadata.model}
        </p>
      </footer>
    </main>
  );
}

function truncate(s: string, n: number): string {
  return s.length <= n ? s : s.slice(0, n).trimEnd() + '…';
}

function RoundProse({ prose }: { prose: string }) {
  const paragraphs = prose.split(/\n\n+/).filter((p) => p.trim());
  return (
    <div className="space-y-3 font-serif text-[14px] leading-relaxed text-ink/85">
      {paragraphs.map((para, i) => {
        const parts = para.split(/(\*\*[^*]+\*\*)/g);
        return (
          <p key={i} className="whitespace-pre-wrap">
            {parts.map((part, j) =>
              part.startsWith('**') && part.endsWith('**') ? (
                <strong key={j}>{part.slice(2, -2)}</strong>
              ) : (
                part
              ),
            )}
          </p>
        );
      })}
    </div>
  );
}
