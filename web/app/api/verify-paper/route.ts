// POST /api/verify-paper — accept a PDF upload and verify every citation in the paper.
//
// Writes the upload to a temp file and shells out to `deltasci verify --pdf … --json`
// (paper mode: parse bibliography → resolve each reference → verify each citation in the
// context of the sentence citing it). Caps references for web responsiveness; the CLI
// can verify all. Requires `deltasci` on PATH with the PDF extra installed.

import { spawn } from 'node:child_process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const MAX_BYTES = 25 * 1024 * 1024; // 25 MB
const MAX_REFERENCES = 30; // keep the web demo responsive against rate-limited APIs
const TIMEOUT_MS = 240_000;

function err(message: string, status: number) {
  return Response.json({ error: message }, { status });
}

export async function POST(req: Request) {
  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return err('expected a multipart/form-data upload', 400);
  }
  const file = form.get('file');
  if (!(file instanceof File)) return err('no PDF uploaded (form field "file")', 400);
  if (file.size === 0) return err('uploaded file is empty', 400);
  if (file.size > MAX_BYTES) return err('PDF too large (max 25 MB)', 400);

  const buf = Buffer.from(await file.arrayBuffer());
  if (!buf.subarray(0, 5).toString('latin1').startsWith('%PDF')) {
    return err('that does not look like a PDF file', 400);
  }

  const dir = await mkdtemp(path.join(tmpdir(), 'deltasci-'));
  const pdfPath = path.join(dir, 'paper.pdf');
  await writeFile(pdfPath, buf);

  const bin = process.env.DELTASCI_BIN || 'deltasci';
  const args = ['verify', '--pdf', pdfPath, '--json', '--max-references', String(MAX_REFERENCES)];
  try {
    return await runCli(bin, args);
  } finally {
    rm(dir, { recursive: true, force: true }).catch(() => {});
  }
}

function runCli(bin: string, args: string[]): Promise<Response> {
  return new Promise((resolve) => {
    const child = spawn(bin, args, { env: process.env });
    let out = '';
    let stderr = '';
    const timer = setTimeout(() => child.kill('SIGKILL'), TIMEOUT_MS);

    child.on('error', (e: NodeJS.ErrnoException) => {
      clearTimeout(timer);
      const hint =
        e.code === 'ENOENT'
          ? ` — '${bin}' not found. Install deltasci with the PDF extra (pip install 'deltasci[pdf]') or set DELTASCI_BIN.`
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
        resolve(Response.json(JSON.parse(trimmed)));
      } catch {
        resolve(err(`could not parse verifier output: ${(stderr || trimmed).slice(0, 400)}`, 500));
      }
    });
  });
}
