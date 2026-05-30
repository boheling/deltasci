"""DeltaScience verifier — Hugging Face Space backend (FastAPI).

A thin wrapper over the `deltasci verify` CLI. Because the record-API calls (Crossref /
PubMed / OpenAlex / arXiv) happen **server-side**, there is no CORS limit and full coverage
is available — including the PubMed claim-to-abstract support check and Crossref title
resolution — with **no LLM and no API key**.

POST /verify  {"text": "...", "checkSupport": true, "format": "auto"}
  -> the same JSON `deltasci verify --json` emits: {summary, verdicts, findings[], coverage}
"""

from __future__ import annotations

import json
import os
import subprocess

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

DELTASCI_BIN = os.environ.get("DELTASCI_BIN", "deltasci")
ALLOWED_FORMATS = {"auto", "tagged", "text", "records", "bibtex"}
TIMEOUT_S = 120

app = FastAPI(title="DeltaScience verifier", docs_url="/docs")

# Public, read-only verifier — open CORS is fine. Tighten `allow_origins` to your Pages
# origin (e.g. ["https://boheling.github.io"]) if you'd rather lock it down.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/")
def health() -> dict:
    return {"ok": True, "service": "deltasci-verify", "no_llm": True, "no_api_key": True}


@app.post("/verify")
async def verify(req: Request) -> dict:
    try:
        body = await req.json()
    except Exception:
        return {"error": "request body must be JSON"}

    b = body if isinstance(body, dict) else {}
    text = b.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return {"error": "no text to verify"}

    fmt = b.get("format") if b.get("format") in ALLOWED_FORMATS else "auto"
    args = [DELTASCI_BIN, "verify", "--file", "-", "--format", fmt, "--json"]
    if b.get("checkSupport") is False:
        args.append("--no-support")

    try:
        proc = subprocess.run(args, input=text, capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"error": "verification timed out"}
    except FileNotFoundError:
        return {"error": f"deltasci CLI not found ({DELTASCI_BIN})"}

    out = proc.stdout.strip()
    if not out:
        return {"error": proc.stderr.strip() or f"verifier exited (code {proc.returncode})"}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"error": "could not parse verifier output", "raw": out[:400]}
