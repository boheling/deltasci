// POST /api/workflow — bridge from the browser to the Python `deltasci workflow` CLI.
//
// The user picks a goal (grant / paper / review / ideate); the CLI composes the right
// components and emits the unified `--json` payload. Same no-shell, args-array, stdin-piped
// pattern as /api/verify (no injection surface). Requires `deltasci` on PATH (it is when the
// dev server is launched by `deltasci view`); override with DELTASCI_BIN.

import { spawn } from 'node:child_process';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const ALLOWED_GOALS = new Set(['grant', 'paper', 'review', 'ideate']);
const ALLOWED_LLM = new Set(['anthropic', 'openai', 'mock']);
const TIMEOUT_MS = 120_000; // workflow fans out to several APIs and maybe an LLM

function err(message: string, status: number) {
  return Response.json({ error: message }, { status });
}

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return err('request body must be JSON', 400);
  }

  const b = (body ?? {}) as Record<string, unknown>;
  const goal = typeof b.goal === 'string' ? b.goal : '';
  const text = typeof b.text === 'string' ? b.text : '';
  const isPaper = b.paper === true;
  const llm = typeof b.llm === 'string' && ALLOWED_LLM.has(b.llm) ? b.llm : '';
  const limit = Number.isInteger(b.limit) ? (b.limit as number) : 0;

  if (!ALLOWED_GOALS.has(goal)) return err(`unknown goal '${goal}'`, 400);
  if (!text.trim()) return err('no text provided', 400);

  const bin = process.env.DELTASCI_BIN || 'deltasci';
  const args = ['workflow', goal, '--file', '-', '--json'];
  if (isPaper) args.push('--paper');
  if (llm) args.push('--llm', llm);
  if (limit > 0 && limit <= 25) args.push('--limit', String(limit));

  return runCli(bin, args, text);
}

function runCli(bin: string, args: string[], stdin: string): Promise<Response> {
  return new Promise((resolve) => {
    const child = spawn(bin, args, { env: process.env });

    let out = '';
    let stderr = '';
    const timer = setTimeout(() => child.kill('SIGKILL'), TIMEOUT_MS);

    child.on('error', (e: NodeJS.ErrnoException) => {
      clearTimeout(timer);
      const hint =
        e.code === 'ENOENT'
          ? ` — '${bin}' not found on PATH. Install deltasci (pip install -e .) or set DELTASCI_BIN.`
          : '';
      resolve(err(`could not launch the workflow: ${e.message}${hint}`, 500));
    });

    child.stdout.on('data', (d) => (out += d));
    child.stderr.on('data', (d) => (stderr += d));

    child.on('close', (code) => {
      clearTimeout(timer);
      const trimmed = out.trim();
      if (!trimmed) {
        resolve(err(stderr.trim() || `workflow exited (code ${code}) with no output`, 500));
        return;
      }
      try {
        // Exit code 2 just means "found a failed audit" — still valid JSON on stdout.
        resolve(Response.json(JSON.parse(trimmed)));
      } catch {
        resolve(err(`could not parse workflow output: ${trimmed.slice(0, 400)}`, 500));
      }
    });

    child.stdin.write(stdin);
    child.stdin.end();
  });
}
