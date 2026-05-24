// Load a DeltaSci run from disk.
// Run dir contains: transcript.md + summary.json (+ optional hypothesis.md, ignored — same data is in summary.json).

import { readFile, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import type {
  DeltaRun,
  DiagramBundle,
  IterationCard,
  NotebookBundle,
  NotebookDoc,
  PostExecBundle,
  Role,
  SummaryJson,
  TranscriptRound,
} from './types';

const TAG_PATTERN =
  /\[(CLAIM|KNOWLEDGE_GAP|NOVEL_SYNTHESIS)(?:\s+[^\]]*)?\]([\s\S]*?)\[\/\1\]/g;

const ROUND_HEADER_PATTERN = /^##\s+([a-z0-9_]+)\s+—\s+([a-z_]+)/i;

function inferRole(speaker: string): Role {
  if (speaker.includes('domain')) return 'domain';
  if (speaker.includes('engineer')) return 'engineer';
  return 'unknown';
}

function stripTags(body: string): string {
  // Replace each tag with its inner text. The auto-generated `### Evidence collected`
  // / `### Knowledge gaps flagged for researcher` / `### Novel syntheses proposed`
  // footers are also stripped — those are re-rendered from summary.json.
  let out = body.replace(TAG_PATTERN, (_, _kind, inner) => inner.trim());
  out = out.replace(/###\s+Evidence collected[\s\S]*?(?=\n##\s|\n*$)/g, '').trimEnd();
  out = out.replace(/###\s+Knowledge gaps flagged for researcher[\s\S]*?(?=\n##\s|\n*$)/g, '').trimEnd();
  out = out.replace(/###\s+Novel syntheses proposed[\s\S]*?(?=\n##\s|\n*$)/g, '').trimEnd();
  return out.trim();
}

function parseTranscript(md: string): { idea: string; rounds: TranscriptRound[] } {
  const ideaMatch = md.match(/\*\*Idea:\*\*\s*(.+?)\n/);
  const idea = ideaMatch ? ideaMatch[1].trim() : '';

  // Split on `## ` headers, keeping each round's header + body together.
  const lines = md.split(/\r?\n/);
  const rounds: TranscriptRound[] = [];
  let currentId: string | null = null;
  let currentSpeaker: string | null = null;
  let currentBody: string[] = [];

  const flush = () => {
    if (currentId && currentSpeaker) {
      rounds.push({
        id: currentId,
        speaker: currentSpeaker,
        role: inferRole(currentSpeaker),
        prose: stripTags(currentBody.join('\n')),
      });
    }
  };

  for (const line of lines) {
    const headerMatch = line.match(ROUND_HEADER_PATTERN);
    if (headerMatch) {
      flush();
      currentId = headerMatch[1];
      currentSpeaker = headerMatch[2];
      currentBody = [];
    } else if (currentId) {
      currentBody.push(line);
    }
  }
  flush();

  return { idea, rounds };
}

export async function loadRun(runDir?: string): Promise<DeltaRun> {
  const dir =
    runDir ??
    process.env.DELTASCI_RUN_DIR ??
    path.join(process.cwd(), 'data', 'biomed_run');

  const [transcriptRaw, summaryRaw] = await Promise.all([
    readFile(path.join(dir, 'transcript.md'), 'utf8'),
    readFile(path.join(dir, 'summary.json'), 'utf8'),
  ]);

  const summary: SummaryJson = JSON.parse(summaryRaw);
  const { idea, rounds } = parseTranscript(transcriptRaw);

  const iterations = await loadIterations(dir);
  const notebook = await loadNotebook(dir);
  const diagrams = await loadDiagrams(dir);
  const postexec = await loadPostExec(dir);

  return {
    pack: summary.hypothesis.metadata.pack_name,
    idea,
    rounds,
    hypothesis: summary.hypothesis,
    grounding: summary.grounding,
    audit: summary.audit,
    protocol: summary.protocol,
    risks: summary.risks,
    challenge: summary.challenge,
    iterations,
    notebook,
    diagrams,
    postexec,
  };
}


async function loadPostExec(runDir: string): Promise<PostExecBundle | undefined> {
  const stage = path.join(runDir, '13_postexec');
  const stats = await stat(stage).catch(() => null);
  if (!stats?.isDirectory()) return undefined;
  const [reportRaw, addendumMd] = await Promise.all([
    readFile(path.join(stage, 'report.json'), 'utf8').catch(() => ''),
    readFile(path.join(stage, 'execution_update.md'), 'utf8').catch(() => ''),
  ]);
  if (!reportRaw && !addendumMd) return undefined;
  try {
    const report = JSON.parse(reportRaw);
    return { report, addendumMd };
  } catch {
    return undefined;
  }
}


async function loadDiagrams(runDir: string): Promise<DiagramBundle | undefined> {
  const stage = path.join(runDir, '12_diagrams');
  const stats = await stat(stage).catch(() => null);
  if (!stats?.isDirectory()) return undefined;
  const [dataFlow, protocolSeq, schema] = await Promise.all([
    readFile(path.join(stage, 'data_flow.mmd'), 'utf8').catch(() => ''),
    readFile(path.join(stage, 'protocol_seq.mmd'), 'utf8').catch(() => ''),
    readFile(path.join(stage, 'schema.mmd'), 'utf8').catch(() => ''),
  ]);
  if (!dataFlow && !protocolSeq && !schema) return undefined;
  return {
    dataFlow: dataFlow || undefined,
    protocolSeq: protocolSeq || undefined,
    schema: schema || undefined,
  };
}


async function loadNotebook(runDir: string): Promise<NotebookBundle | undefined> {
  const stage = path.join(runDir, '10_notebook');
  const stats = await stat(stage).catch(() => null);
  if (!stats?.isDirectory()) return undefined;
  let notebook: NotebookDoc;
  try {
    const raw = await readFile(path.join(stage, 'notebook.ipynb'), 'utf8');
    notebook = JSON.parse(raw);
  } catch {
    return undefined;
  }
  const requirements = await readFile(path.join(stage, 'requirements.txt'), 'utf8').catch(() => '');
  const readme = await readFile(path.join(stage, 'README.md'), 'utf8').catch(() => '');
  return { notebook, requirements, readme };
}


async function loadIterations(runDir: string): Promise<IterationCard[]> {
  const iterDir = path.join(runDir, '09_iterations');
  const stats = await stat(iterDir).catch(() => null);
  if (!stats?.isDirectory()) return [];

  const entries = await readdir(iterDir);
  const cards: IterationCard[] = [];
  for (const name of entries.sort()) {
    if (!/^v\d+$/.test(name)) continue;
    const subdir = path.join(iterDir, name);
    let summary: SummaryJson | null = null;
    try {
      const raw = await readFile(path.join(subdir, 'summary.json'), 'utf8');
      summary = JSON.parse(raw);
    } catch {
      try {
        const raw = await readFile(path.join(subdir, '05_synthesis', 'summary.json'), 'utf8');
        summary = JSON.parse(raw);
      } catch {
        continue;
      }
    }
    if (!summary?.hypothesis) continue;
    const h = summary.hypothesis;
    cards.push({
      version: name,
      title: h.title,
      generated_at: h.metadata?.generated_at ?? '',
      well_covered: h.epistemic_summary?.well_covered_count ?? 0,
      sparse: h.epistemic_summary?.sparse_count ?? 0,
      knowledge_gaps: h.epistemic_summary?.knowledge_gap_count ?? 0,
      novel_syntheses: h.epistemic_summary?.novel_synthesis_count ?? 0,
      audit_failed: summary.audit?.findings?.filter((f) => f.status === 'mismatch').length ?? 0,
      audit_verified: summary.audit?.findings?.filter((f) => f.status === 'verified').length ?? 0,
    });
  }
  return cards;
}
