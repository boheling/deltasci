// TypeScript mirrors of deltasci's Pydantic schemas.
// Source of truth: src/deltasci/hypothesis.py + grounding summary in cli output.

export type EvidenceType =
  | 'published-evidence'
  | 'established-guideline'
  | 'observation'
  | 'engineering-precedent';

export type Coverage = 'well-covered' | 'sparse';

export type GapCategory =
  | 'lab-tribal-knowledge'
  | 'paywalled-or-non-OA'
  | 'non-english-literature'
  | 'niche-subfield'
  | 'unpublished-or-pilot-data'
  | 'patent-or-clinical-practice'
  | 'novel-cross-disciplinary-connection'
  | 'other';

export interface EvidenceItem {
  claim: string;
  type: EvidenceType;
  source: string;
  coverage: Coverage;
  verified: boolean;
}

export interface KnowledgeGap {
  question: string;
  category: GapCategory | string;
}

export interface NovelSynthesis {
  proposed_connection: string;
  rationale: string;
}

export interface FalsifiabilityClause {
  prediction: string;
  threshold: string;
  null_outcome: string;
}

export interface FeasibilityScores {
  scores: Record<string, number>;
  justifications: Record<string, string>;
  overall: number;
}

export interface EpistemicSummary {
  well_covered_count: number;
  sparse_count: number;
  knowledge_gap_count: number;
  novel_synthesis_count: number;
  warnings: string[];
}

export interface HypothesisMetadata {
  pack_name: string;
  pack_version: string;
  deltasci_version: string;
  llm_provider: string;
  model: string;
  num_rounds: number;
  generated_at: string;
}

export interface GroundedHypothesis {
  title: string;
  statement: string;
  domain_grounding: {
    mechanism: string;
    unmet_need: string;
    expected_impact: string;
  };
  technical_approach: {
    core_method: string;
    key_innovation: string;
    implementation_path: string;
  };
  evidence_trail: EvidenceItem[];
  knowledge_gaps: KnowledgeGap[];
  novel_syntheses: NovelSynthesis[];
  falsifiability: FalsifiabilityClause;
  feasibility_scores: FeasibilityScores;
  epistemic_summary: EpistemicSummary;
  metadata: HypothesisMetadata;
}

export interface RoundGroundingStat {
  kind: string;
  claims: number;
  knowledge_gaps: number;
  novel_syntheses: number;
  violations: number;
}

export interface GroundingSummary {
  total_claims: number;
  total_knowledge_gaps: number;
  total_novel_syntheses: number;
  total_violations: number;
  by_round: RoundGroundingStat[];
}

// --- v0.2.0 additions ------------------------------------------------------

export interface ProtocolStep {
  order: number;
  name: string;
  description: string;
  inputs: string[];
  outputs: string[];
  method_citations: string[];
}

export interface DataAcquisitionPlan {
  primary_dataset: string;
  accession_or_url: string;
  access_constraints: string;
  fallback_datasets: string[];
}

export interface ComputeRequirements {
  hardware: string;
  estimated_runtime: string;
  storage: string;
  cost_estimate: string;
}

export interface ExperimentPlan {
  title: string;
  summary: string;
  data_acquisition: DataAcquisitionPlan;
  steps: ProtocolStep[];
  primary_metric: string;
  success_threshold: string;
  null_outcome: string;
  baselines: string[];
  compute: ComputeRequirements;
  timeline_estimate: string;
  sample_size_justification: string;
}

export interface RiskItem {
  id: string;
  category: string;
  severity: 'low' | 'medium' | 'high' | 'critical' | string;
  description: string;
  likely_failure_mode: string;
  mitigation: string;
  counter_evidence_citations: string[];
}

export interface RiskRegister {
  summary: string;
  items: RiskItem[];
}

export interface ChallengeFinding {
  id: string;
  kind: string;
  severity: 'low' | 'medium' | 'high' | 'critical' | string;
  description: string;
  evidence_citations: string[];
  suggested_response: string;
}

export interface ChallengeReport {
  summary: string;
  findings: ChallengeFinding[];
  challenger_provider: string;
  challenger_model: string;
}

export type AuditStatus = 'verified' | 'mismatch' | 'unverifiable' | 'skipped';

export interface AuditFinding {
  target_kind: string;
  target_summary: string;
  auditor_name: string;
  status: AuditStatus;
  fetched_metadata: Record<string, unknown>;
  mismatch_reasons: string[];
  confidence: 'high' | 'medium' | 'low' | string;
  audited_at: string;
}

export interface AuditReport {
  findings: AuditFinding[];
  skipped: boolean;
  skipped_reason: string;
}

export interface SummaryJson {
  hypothesis: GroundedHypothesis;
  grounding: GroundingSummary;
  audit?: AuditReport;
  protocol?: ExperimentPlan;
  risks?: RiskRegister;
  challenge?: ChallengeReport;
}

// Per-round transcript view, parsed from transcript.md.
export type Role = 'domain' | 'engineer' | 'unknown';

export interface TranscriptRound {
  id: string; // e.g. "domain_r1"
  speaker: string; // e.g. "domain_scientist"
  role: Role;
  prose: string; // body markdown with [CLAIM]/[KNOWLEDGE_GAP]/[NOVEL_SYNTHESIS] tags stripped to inner text
}

// v0.3.0 — notebook scaffold
export type NotebookCellType = 'markdown' | 'code' | 'raw';

// Cell-output `data` is a MIME-keyed map. Most MIME types ship strings (or
// arrays of strings, à la Jupyter line-split convention); some (notably
// application/vnd.plotly.v1+json) ship structured objects. Hence `unknown` —
// individual renderers narrow the value at the call site.
export type NotebookOutput =
  | { output_type: 'stream'; name: 'stdout' | 'stderr'; text: string | string[] }
  | { output_type: 'display_data' | 'execute_result'; data: Record<string, string | string[] | unknown>; metadata?: Record<string, unknown>; execution_count?: number | null }
  | { output_type: 'error'; ename: string; evalue: string; traceback: string[] };

export interface NotebookCell {
  cell_type: NotebookCellType;
  source: string | string[];
  metadata?: Record<string, unknown>;
  outputs?: NotebookOutput[];
  execution_count?: number | null;
}

export interface NotebookDoc {
  cells: NotebookCell[];
  metadata?: Record<string, unknown>;
  nbformat?: number;
  nbformat_minor?: number;
}

export interface NotebookBundle {
  notebook: NotebookDoc;
  requirements: string;
  readme: string;
}

export interface DiagramBundle {
  dataFlow?: string;       // mermaid source — flowchart of data → steps → metric
  protocolSeq?: string;    // mermaid source — sequenceDiagram of protocol steps
  schema?: string;         // optional mermaid source — explicit graph schema
}

export interface PostExecReport {
  metrics: Array<{ name: string; value: number; pretty: string; cell_index: number; snippet: string }>;
  risk_statuses: Array<{
    risk_id: string;
    severity: string;
    description: string;
    status: 'resolved' | 'still_open' | 'partly_resolved' | 'confirmed' | 'unknown';
    evidence_cell: number | null;
    evidence_snippet: string;
    rationale: string;
  }>;
  next_step_statuses: Array<{
    order: number;
    name: string;
    status: 'done' | 'outstanding' | 'partial';
    evidence_cell: number | null;
    evidence_snippet: string;
  }>;
  new_issues: Array<{ cell_index: number; kind: string; message: string; snippet: string }>;
  achievements: Array<{ headline: string; detail: string; cell_index: number | null }>;
}

export interface PostExecBundle {
  report: PostExecReport;
  addendumMd: string;     // 13_postexec/execution_update.md
}

export interface IterationCard {
  version: string; // "v1", "v2", ...
  title: string;
  generated_at: string;
  well_covered: number;
  sparse: number;
  knowledge_gaps: number;
  novel_syntheses: number;
  audit_failed: number;
  audit_verified: number;
}

export interface DeltaRun {
  pack: string;
  idea: string;
  rounds: TranscriptRound[];
  hypothesis: GroundedHypothesis;
  grounding: GroundingSummary;
  audit?: AuditReport;
  protocol?: ExperimentPlan;
  risks?: RiskRegister;
  challenge?: ChallengeReport;
  iterations: IterationCard[];
  notebook?: NotebookBundle;
  diagrams?: DiagramBundle;
  postexec?: PostExecBundle;
}
