// POST /api/verify — bridge from the browser to the Python `deltasci verify` CLI.
//
// The verifier is Python; this route shells out to it (no shell — args array, text
// piped via stdin, so there's no injection surface) and returns the same `--json`
// payload the CLI emits. Requires the `deltasci` CLI on PATH (it is when the dev
// server is launched by `deltasci view`); override with the DELTASCI_BIN env var.

import { spawn } from 'node:child_process';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const ALLOWED_FORMATS = new Set(['auto', 'tagged', 'text', 'records', 'bibtex']);
const TIMEOUT_MS = 60_000;

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
  const text = typeof b.text === 'string' ? b.text : '';
  const format = typeof b.format === 'string' && ALLOWED_FORMATS.has(b.format) ? b.format : 'auto';
  const checkSupport = b.checkSupport !== false; // default on

  if (!text.trim()) return err('no text to verify', 400);

  const bin = process.env.DELTASCI_BIN || 'deltasci';
  const args = ['verify', '--file', '-', '--format', format, '--json'];
  if (!checkSupport) args.push('--no-support');

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
      resolve(err(`could not launch the verifier: ${e.message}${hint}`, 500));
    });

    child.stdout.on('data', (d) => (out += d));
    child.stderr.on('data', (d) => (stderr += d));

    child.on('close', (code) => {
      clearTimeout(timer);
      const trimmed = out.trim();
      if (!trimmed) {
        resolve(err(stderr.trim() || `verifier exited (code ${code}) with no output`, 500));
        return;
      }
      try {
        // Exit code 2 just means "found a failed audit" — still valid JSON on stdout.
        resolve(Response.json(JSON.parse(trimmed)));
      } catch {
        resolve(err(`could not parse verifier output: ${trimmed.slice(0, 400)}`, 500));
      }
    });

    child.stdin.write(stdin);
    child.stdin.end();
  });
}
