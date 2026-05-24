// Load a "project" view — multiple deltasci runs under a parent directory.
// A project dir contains many <timestamp>_<slug>/ run subdirectories, each
// with its own manifest.json + summary.json. v0.2.1.

import { readdir, readFile, stat } from 'node:fs/promises';
import path from 'node:path';

import type { GroundedHypothesis, GroundingSummary, AuditReport } from './types';

export interface RunCard {
  /** absolute run-dir path */
  dir: string;
  /** path relative to the project dir, used as a stable id */
  slug: string;
  title: string;
  idea: string;
  generated_at: string;
  pack: string;
  model: string;
  evidence_well_covered: number;
  evidence_sparse: number;
  knowledge_gaps: number;
  novel_syntheses: number;
  audit_verified: number;
  audit_failed: number;
  has_protocol: boolean;
  has_risks: boolean;
  has_challenge: boolean;
  iteration_count: number;
}

export interface ProjectView {
  dir: string;
  runs: RunCard[];
}

interface ManifestShape {
  deltasci_version?: string;
  pack?: string;
  model?: string;
  stages?: Record<string, string | null>;
  counts?: {
    evidence_well_covered?: number;
    evidence_sparse?: number;
    knowledge_gaps?: number;
    novel_syntheses?: number;
    audit_verified?: number;
    audit_failed?: number;
    challenge_findings?: number;
  };
}

interface SummaryShape {
  hypothesis?: GroundedHypothesis;
  grounding?: GroundingSummary;
  audit?: AuditReport;
  protocol?: unknown;
  risks?: unknown;
  challenge?: unknown;
}

async function readJsonOrNull<T>(p: string): Promise<T | null> {
  try {
    return JSON.parse(await readFile(p, 'utf8')) as T;
  } catch {
    return null;
  }
}

async function readIdeaText(runDir: string): Promise<string> {
  try {
    const text = await readFile(path.join(runDir, '00_idea.md'), 'utf8');
    return text.replace(/^#\s*Research idea\s*\n+/, '').trim();
  } catch {
    return '';
  }
}

async function countIterations(runDir: string): Promise<number> {
  try {
    const entries = await readdir(path.join(runDir, '09_iterations'));
    let n = 0;
    for (const name of entries) {
      if (/^v\d+$/.test(name)) n += 1;
    }
    return n;
  } catch {
    return 0;
  }
}

async function loadCard(projectDir: string, runDirName: string): Promise<RunCard | null> {
  const runDir = path.join(projectDir, runDirName);
  const manifest = await readJsonOrNull<ManifestShape>(path.join(runDir, 'manifest.json'));
  const summary = await readJsonOrNull<SummaryShape>(path.join(runDir, 'summary.json'));
  if (!summary?.hypothesis) {
    // 05_synthesis/summary.json fallback (staged layout without top-level copy)
    const stagedSummary = await readJsonOrNull<SummaryShape>(
      path.join(runDir, '05_synthesis', 'summary.json'),
    );
    if (!stagedSummary?.hypothesis) {
      return null;
    }
    Object.assign(summary ?? {}, stagedSummary);
    if (!summary?.hypothesis) {
      return null;
    }
  }
  const h = summary.hypothesis as GroundedHypothesis;
  const idea = await readIdeaText(runDir);
  const iterations = await countIterations(runDir);

  const stages = manifest?.stages ?? {};
  return {
    dir: runDir,
    slug: runDirName,
    title: h.title,
    idea,
    generated_at: h.metadata?.generated_at ?? '',
    pack: manifest?.pack ?? h.metadata?.pack_name ?? '',
    model: manifest?.model ?? h.metadata?.model ?? '',
    evidence_well_covered: manifest?.counts?.evidence_well_covered ?? h.epistemic_summary?.well_covered_count ?? 0,
    evidence_sparse: manifest?.counts?.evidence_sparse ?? h.epistemic_summary?.sparse_count ?? 0,
    knowledge_gaps: manifest?.counts?.knowledge_gaps ?? h.epistemic_summary?.knowledge_gap_count ?? 0,
    novel_syntheses: manifest?.counts?.novel_syntheses ?? h.epistemic_summary?.novel_synthesis_count ?? 0,
    audit_verified: manifest?.counts?.audit_verified ?? 0,
    audit_failed: manifest?.counts?.audit_failed ?? 0,
    has_protocol: Boolean(stages.protocol) || Boolean(summary.protocol),
    has_risks: Boolean(stages.risks) || Boolean(summary.risks),
    has_challenge: Boolean(summary.challenge),
    iteration_count: iterations,
  };
}

export async function loadProject(projectDir?: string): Promise<ProjectView | null> {
  const dir =
    projectDir ?? process.env.DELTASCI_PROJECT_DIR ?? null;
  if (!dir) return null;
  const stats = await stat(dir).catch(() => null);
  if (!stats?.isDirectory()) return null;

  const entries = await readdir(dir);
  const cards: RunCard[] = [];
  for (const name of entries) {
    if (name.startsWith('.') || name.startsWith('_')) continue;
    const child = path.join(dir, name);
    const cstat = await stat(child).catch(() => null);
    if (!cstat?.isDirectory()) continue;
    const card = await loadCard(dir, name);
    if (card) cards.push(card);
  }
  // Newest first
  cards.sort((a, b) => (b.generated_at ?? '').localeCompare(a.generated_at ?? ''));
  return { dir, runs: cards };
}
