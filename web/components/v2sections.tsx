// v0.2.0 review components: Protocol, Risks, Challenge, Audit.
// Each renders the corresponding summary.json section. Visual style consistent
// with the existing auditable.tsx.

import type {
  AuditFinding,
  AuditReport,
  ChallengeFinding,
  ChallengeReport,
  ExperimentPlan,
  ProtocolStep,
  RiskItem,
  RiskRegister,
} from '@/lib/types';

// ---------- Protocol ----------------------------------------------------------

export function ProtocolView({ plan }: { plan: ExperimentPlan }) {
  return (
    <div className="space-y-6">
      <p className="font-serif text-[15px] leading-relaxed text-ink/85">{plan.summary}</p>

      <Subsection label="Data acquisition">
        <KV k="Primary dataset" v={plan.data_acquisition.primary_dataset || '—'} />
        <KV k="Accession / URL" v={plan.data_acquisition.accession_or_url || '—'} mono />
        <KV k="Access constraints" v={plan.data_acquisition.access_constraints || '—'} />
        {plan.data_acquisition.fallback_datasets.length > 0 && (
          <KV k="Fallback datasets" v={plan.data_acquisition.fallback_datasets.join(', ')} />
        )}
      </Subsection>

      <Subsection label="Steps">
        <ol className="space-y-3">
          {plan.steps.map((s) => (
            <Step key={s.order} step={s} />
          ))}
        </ol>
      </Subsection>

      <Subsection label="Evaluation">
        <KV k="Primary metric" v={plan.primary_metric} />
        <KV k="Success threshold" v={plan.success_threshold} />
        <KV k="Null outcome" v={plan.null_outcome} />
        {plan.baselines.length > 0 && (
          <KV k="Baselines" v={plan.baselines.join(', ')} />
        )}
      </Subsection>

      <Subsection label="Compute">
        <KV k="Hardware" v={plan.compute.hardware || '—'} mono />
        <KV k="Estimated runtime" v={plan.compute.estimated_runtime || '—'} />
        <KV k="Storage" v={plan.compute.storage || '—'} />
        <KV k="Cost estimate" v={plan.compute.cost_estimate || '—'} />
      </Subsection>

      <Subsection label="Timeline + sample-size">
        <KV k="Timeline" v={plan.timeline_estimate || '—'} />
        <KV k="Sample-size justification" v={plan.sample_size_justification || '—'} />
      </Subsection>
    </div>
  );
}

function Step({ step }: { step: ProtocolStep }) {
  return (
    <li className="rounded border border-slate-border/15 bg-white/60 p-4">
      <p className="font-sans text-[13px] font-semibold text-ink">
        <span className="font-mono text-teal">{String(step.order).padStart(2, '0')}</span>
        {' · '}
        {step.name}
      </p>
      {step.description && (
        <p className="mt-1 font-serif text-[14px] leading-snug text-ink/85">
          {step.description}
        </p>
      )}
      <div className="mt-2 grid gap-x-4 gap-y-1 sm:grid-cols-2 font-mono text-[11px] text-ink/60">
        {step.inputs.length > 0 && <div>inputs: {step.inputs.join(', ')}</div>}
        {step.outputs.length > 0 && <div>outputs: {step.outputs.join(', ')}</div>}
      </div>
      {step.method_citations.length > 0 && (
        <ul className="mt-2 space-y-0.5 font-mono text-[10px] text-ink/55">
          {step.method_citations.map((c, i) => (
            <li key={i} className="italic">
              method: {c}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

// ---------- Risks -------------------------------------------------------------

const SEVERITY_CLASS: Record<string, string> = {
  critical: 'bg-burgundy text-cream',
  high: 'bg-burgundy-soft text-burgundy',
  medium: 'bg-warm-soft text-warm',
  low: 'bg-teal-soft text-teal',
};

export function RisksView({ register }: { register: RiskRegister }) {
  return (
    <div className="space-y-4">
      <p className="font-serif text-[15px] leading-relaxed text-ink/85">{register.summary}</p>
      <p className="font-mono text-[11px] text-ink/60">{register.items.length} risks identified.</p>
      <ul className="space-y-3">
        {register.items.map((r) => (
          <RiskCard key={r.id} risk={r} />
        ))}
      </ul>
    </div>
  );
}

function RiskCard({ risk }: { risk: RiskItem }) {
  const sev = SEVERITY_CLASS[risk.severity.toLowerCase()] || 'bg-ink/10 text-ink';
  return (
    <li className="rounded border border-slate-border/15 bg-white/60 p-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono text-[12px] font-semibold text-teal">{risk.id}</span>
        <span className={`rounded-sm px-2 py-0.5 font-mono text-[10px] font-semibold uppercase ${sev}`}>
          {risk.severity}
        </span>
        <span className="font-mono text-[11px] text-ink/55">{risk.category}</span>
      </div>
      <p className="mt-2 font-serif text-[14px] leading-snug text-ink">
        <strong>Description.</strong> {risk.description}
      </p>
      <p className="mt-1.5 font-serif text-[14px] leading-snug text-ink/85">
        <strong>Likely failure mode.</strong> {risk.likely_failure_mode}
      </p>
      <p className="mt-1.5 font-serif text-[14px] leading-snug text-ink/85">
        <strong>Mitigation.</strong> {risk.mitigation}
      </p>
      {risk.counter_evidence_citations.length > 0 && (
        <ul className="mt-2 space-y-0.5 font-mono text-[10px] text-ink/55">
          {risk.counter_evidence_citations.map((c, i) => (
            <li key={i}>counter-evidence: {c}</li>
          ))}
        </ul>
      )}
    </li>
  );
}

// ---------- Challenge ---------------------------------------------------------

export function ChallengeView({ report }: { report: ChallengeReport }) {
  return (
    <div className="space-y-4">
      <p className="font-mono text-[11px] text-ink/55">
        Challenger: {report.challenger_provider} / {report.challenger_model}
      </p>
      <p className="font-serif text-[15px] leading-relaxed text-ink/85">{report.summary}</p>
      <p className="font-mono text-[11px] text-ink/60">{report.findings.length} findings.</p>
      <ul className="space-y-3">
        {report.findings.map((f) => (
          <ChallengeCard key={f.id} finding={f} />
        ))}
      </ul>
    </div>
  );
}

function ChallengeCard({ finding }: { finding: ChallengeFinding }) {
  const sev = SEVERITY_CLASS[finding.severity.toLowerCase()] || 'bg-ink/10 text-ink';
  return (
    <li className="rounded border border-slate-border/15 bg-white/60 p-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono text-[12px] font-semibold text-burgundy">{finding.id}</span>
        <span className={`rounded-sm px-2 py-0.5 font-mono text-[10px] font-semibold uppercase ${sev}`}>
          {finding.severity}
        </span>
        <span className="font-mono text-[11px] text-ink/55">{finding.kind}</span>
      </div>
      <p className="mt-2 font-serif text-[14px] leading-snug text-ink">
        <strong>Critique.</strong> {finding.description}
      </p>
      {finding.suggested_response && (
        <p className="mt-1.5 font-serif text-[14px] leading-snug text-ink/85">
          <strong>Suggested response.</strong> {finding.suggested_response}
        </p>
      )}
      {finding.evidence_citations.length > 0 && (
        <ul className="mt-2 space-y-0.5 font-mono text-[10px] text-ink/55">
          {finding.evidence_citations.map((c, i) => (
            <li key={i}>evidence: {c}</li>
          ))}
        </ul>
      )}
    </li>
  );
}

// ---------- Audit -------------------------------------------------------------

const AUDIT_BADGE: Record<string, string> = {
  verified: 'bg-teal-soft text-teal',
  mismatch: 'bg-burgundy text-cream',
  unverifiable: 'bg-ink/10 text-ink/70',
  skipped: 'bg-warm-soft text-warm',
};

export function AuditView({ report }: { report: AuditReport }) {
  if (report.skipped) {
    return (
      <div className="rounded border border-burgundy/30 bg-burgundy-soft/40 p-4 font-mono text-[12px] text-burgundy">
        ⚠ AUDIT SKIPPED — citations not verified ({report.skipped_reason})
      </div>
    );
  }

  const verified = report.findings.filter((f) => f.status === 'verified');
  const mismatches = report.findings.filter((f) => f.status === 'mismatch');
  const skipped = report.findings.filter((f) => f.status === 'skipped');

  return (
    <div className="space-y-6">
      <div className="rounded border border-slate-border/15 bg-white/60 px-5 py-4">
        <p className="font-mono text-[11px] uppercase tracking-wider text-ink/55">Audit summary</p>
        <div className="mt-2 flex flex-wrap items-baseline gap-3">
          <Pill ok>{verified.length} verified</Pill>
          {mismatches.length > 0 && <Pill bad>{mismatches.length} FAILED AUDIT</Pill>}
          {skipped.length > 0 && <Pill neutral>{skipped.length} skipped</Pill>}
        </div>
      </div>

      {mismatches.length > 0 && (
        <div className="rounded border border-burgundy/30 bg-burgundy-soft/30 p-4">
          <p className="font-sans text-[13px] font-semibold text-burgundy">
            ✗ Failed audit — likely hallucinated citations
          </p>
          <p className="mt-1 font-serif text-[13px] leading-snug text-ink/80">
            These citations did not match the records at the cited identifiers. Verify or remove
            before relying on this hypothesis. This is the BioIntel-style failure mode the audit
            pillar exists to surface.
          </p>
          <ul className="mt-3 space-y-2">
            {mismatches.map((f, i) => (
              <FindingCard key={i} finding={f} />
            ))}
          </ul>
        </div>
      )}

      <details className="rounded border border-slate-border/15 bg-white/60 p-4">
        <summary className="cursor-pointer font-sans text-[13px] font-medium text-ink">
          ✓ Verified citations ({verified.length})
        </summary>
        <ul className="mt-3 space-y-2">
          {verified.map((f, i) => (
            <FindingCard key={i} finding={f} />
          ))}
        </ul>
      </details>

      {skipped.length > 0 && (
        <details className="rounded border border-slate-border/15 bg-white/60 p-4">
          <summary className="cursor-pointer font-sans text-[13px] font-medium text-ink">
            … Skipped ({skipped.length})
          </summary>
          <ul className="mt-3 space-y-2">
            {skipped.map((f, i) => (
              <FindingCard key={i} finding={f} />
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function FindingCard({ finding }: { finding: AuditFinding }) {
  const cls = AUDIT_BADGE[finding.status] || 'bg-ink/10 text-ink';
  const md = finding.fetched_metadata as Record<string, unknown>;
  return (
    <li className="rounded-sm border border-slate-border/10 bg-cream/40 px-3 py-2">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className={`rounded-sm px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase ${cls}`}>
          {finding.status}
        </span>
        <span className="font-mono text-[10px] text-ink/55">{finding.auditor_name}</span>
      </div>
      <p className="mt-1 font-serif text-[13px] leading-snug text-ink">
        <span className="font-mono text-[11px] text-ink/60">AI claimed:</span> {finding.target_summary}
      </p>
      {finding.status === 'mismatch' && (
        <div className="mt-1.5 rounded-sm bg-burgundy-soft/50 px-2 py-1.5 font-serif text-[13px] leading-snug text-ink/85">
          <p className="font-mono text-[11px] text-burgundy">Actual at identifier:</p>
          {md.title ? <p>title: {String(md.title)}</p> : null}
          {Array.isArray(md.authors) && (md.authors as unknown[]).length > 0 ? (
            <p>first author: {String((md.authors as unknown[])[0])}</p>
          ) : null}
          {md.year ? <p>year: {String(md.year)}</p> : null}
          {md.journal ? <p>journal: {String(md.journal)}</p> : null}
          {md.url ? (
            <p>
              url:{' '}
              <a href={String(md.url)} target="_blank" rel="noreferrer" className="underline">
                {String(md.url)}
              </a>
            </p>
          ) : null}
        </div>
      )}
      {finding.mismatch_reasons.length > 0 && (
        <ul className="mt-1 space-y-0.5 font-mono text-[10px] text-burgundy">
          {finding.mismatch_reasons.map((r, i) => (
            <li key={i}>→ {r}</li>
          ))}
        </ul>
      )}
      {finding.status === 'verified' && md.url ? (
        <p className="mt-1 font-mono text-[10px] text-ink/55">
          →{' '}
          <a href={String(md.url)} target="_blank" rel="noreferrer" className="underline">
            {String(md.url)}
          </a>
        </p>
      ) : null}
    </li>
  );
}

function Pill({
  children,
  ok,
  bad,
  neutral,
}: {
  children: React.ReactNode;
  ok?: boolean;
  bad?: boolean;
  neutral?: boolean;
}) {
  const cls = ok
    ? 'bg-teal text-cream'
    : bad
    ? 'bg-burgundy text-cream'
    : neutral
    ? 'bg-ink/15 text-ink'
    : 'bg-ink/10 text-ink';
  return (
    <span className={`rounded-sm px-2 py-1 font-mono text-[12px] font-semibold ${cls}`}>
      {children}
    </span>
  );
}

// ---------- Helpers shared across views ---------------------------------------

function Subsection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="font-mono text-[10px] font-medium uppercase tracking-wider text-ink/55">
        {label}
      </p>
      <div className="mt-2 space-y-2">{children}</div>
    </div>
  );
}

function KV({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div>
      <span className="font-sans text-[12px] font-medium text-ink/70">{k}: </span>
      <span className={mono ? 'font-mono text-[12px] text-ink' : 'font-serif text-[14px] text-ink'}>
        {v}
      </span>
    </div>
  );
}
