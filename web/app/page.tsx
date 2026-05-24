// Root page. Dispatches between project view (when DELTASCI_PROJECT_DIR is
// set) and single-run review (DELTASCI_RUN_DIR or bundled fallback).

import { loadProject } from '@/lib/loadProject';
import { loadRun } from '@/lib/loadRun';
import { ProjectViewSurface } from '@/components/projectView';
import { RunDetail } from '@/components/runDetail';

export const dynamic = 'force-dynamic';

export default async function Page() {
  const project = await loadProject();
  if (project) {
    return <ProjectViewSurface project={project} />;
  }
  const run = await loadRun();
  return <RunDetail run={run} />;
}
