// Per-run detail route. Resolves <DELTASCI_PROJECT_DIR>/<slug>/ and renders
// the same RunDetail surface as the root page would for that run.

import path from 'node:path';
import { stat } from 'node:fs/promises';
import { notFound } from 'next/navigation';

import { loadRun } from '@/lib/loadRun';
import { RunDetail } from '@/components/runDetail';

export const dynamic = 'force-dynamic';

export default async function RunPage({ params }: { params: Promise<{ slug: string }> }) {
  const projectDir = process.env.DELTASCI_PROJECT_DIR;
  if (!projectDir) {
    // Without a project dir, this route is meaningless — bounce.
    notFound();
  }

  const { slug } = await params;
  // Defense-in-depth against path traversal: slug must not contain ../ or absolute paths.
  if (slug.includes('..') || slug.includes('/') || slug.includes('\\') || slug.startsWith('.')) {
    notFound();
  }

  const runDir = path.join(projectDir, slug);
  const stats = await stat(runDir).catch(() => null);
  if (!stats?.isDirectory()) {
    notFound();
  }

  let run;
  try {
    run = await loadRun(runDir);
  } catch {
    notFound();
  }

  return <RunDetail run={run} projectHref="/" />;
}
