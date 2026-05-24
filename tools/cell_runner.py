"""Cell-by-cell notebook runner with persistent kernel + observation insertion.

Used to dogfood the v0.6 design: walks an existing .ipynb, executes each code cell
in a long-lived ipykernel, captures outputs, writes them back into the notebook,
and inserts a markdown 'Observation' cell after each executed code cell. Designed
to be driven from a single shell process so the kernel stays alive between
invocations.

Subcommands:
  start      -- launch a kernel, write connection_file path to STATE_FILE
  exec N     -- execute cell index N against the running kernel; write outputs
                + an Observation markdown cell into the notebook
  patch N    -- replace cell N's source with the contents of a file (for iterate)
  stop       -- shut the kernel down

Designed to live under tools/ for the duration of the session; the polished
version lands in deltasci/execute/ when we ship v0.6.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from jupyter_client.manager import KernelManager

DEFAULT_NOTEBOOK = Path("docs/examples/marco_dr_dq/10_notebook/notebook.ipynb")
STATE_FILE = Path("/tmp/deltasci_runner_state.json")
TIMEOUT_S = 300


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _load_state() -> dict:
    if not STATE_FILE.exists():
        sys.exit("no kernel running (state file missing). run: cell_runner.py start")
    return json.loads(STATE_FILE.read_text())


def cmd_start(args: argparse.Namespace) -> None:
    """Start a kernel and BLOCK forever, holding it alive.

    ipykernel monitors its parent and quits when the parent dies, so this
    process must remain alive for the kernel to stay reachable. Run with
    `nohup ... &` (or claude-code's run_in_background) to detach.
    """
    km = KernelManager(kernel_name="python3")
    km.start_kernel()
    pid = km.provisioner.process.pid if km.provisioner else km.kernel.pid
    state = {
        "connection_file": km.connection_file,
        "started_at": time.time(),
        "notebook": str(args.notebook),
        "kernel_pid": pid,
    }
    _save_state(state)
    print(f"kernel started; connection_file={km.connection_file}", flush=True)
    print(f"kernel PID={pid}", flush=True)
    # Block forever, polling. Exit cleanly if kernel dies.
    while True:
        time.sleep(5)
        if not km.is_alive():
            print("kernel process exited; supervisor exiting", flush=True)
            if STATE_FILE.exists():
                STATE_FILE.unlink()
            return


def _client_from_state() -> tuple:
    state = _load_state()
    from jupyter_client.blocking import BlockingKernelClient

    kc = BlockingKernelClient()
    kc.load_connection_file(state["connection_file"])
    kc.start_channels()
    kc.wait_for_ready(timeout=10)
    return kc, state


def _execute(kc, code: str, timeout: float = TIMEOUT_S) -> dict:
    """Run code on the kernel, return {status, stdout, stderr, displays, error}."""
    msg_id = kc.execute(code, store_history=True)
    out = {"status": "unknown", "stdout": "", "stderr": "", "displays": [], "error": None}
    deadline = time.time() + timeout
    # Poll iopub for messages relating to msg_id
    while time.time() < deadline:
        try:
            msg = kc.get_iopub_msg(timeout=1)
        except Exception:
            continue
        parent = msg.get("parent_header", {})
        if parent.get("msg_id") != msg_id:
            continue
        msg_type = msg["msg_type"]
        content = msg["content"]
        if msg_type == "stream":
            if content["name"] == "stdout":
                out["stdout"] += content["text"]
            else:
                out["stderr"] += content["text"]
        elif msg_type in ("display_data", "execute_result"):
            # Preserve ALL MIME types — plotly figures come back as
            # `application/vnd.plotly.v1+json` (or `application/json`); also
            # forward image/png and text/plain for backwards compat.
            data = content.get("data", {})
            if data:
                out["displays"].append({"all_mime": data})
        elif msg_type == "error":
            out["error"] = {
                "ename": content["ename"],
                "evalue": content["evalue"],
                "traceback": content["traceback"],
            }
        elif msg_type == "status" and content.get("execution_state") == "idle":
            break
    out["status"] = "error" if out["error"] else "ok"
    return out


def _make_outputs(result: dict) -> list[dict]:
    outputs: list[dict] = []
    if result["stdout"]:
        outputs.append({"output_type": "stream", "name": "stdout", "text": result["stdout"]})
    if result["stderr"]:
        outputs.append({"output_type": "stream", "name": "stderr", "text": result["stderr"]})
    for d in result["displays"]:
        if "all_mime" in d:
            outputs.append({
                "output_type": "display_data",
                "data": d["all_mime"],
                "metadata": {},
            })
        elif d.get("type") == "image/png":
            outputs.append({
                "output_type": "display_data",
                "data": {"image/png": d["data"]},
                "metadata": {},
            })
        else:
            outputs.append({
                "output_type": "execute_result",
                "data": {"text/plain": d["data"]},
                "metadata": {},
                "execution_count": None,
            })
    if result["error"]:
        outputs.append({
            "output_type": "error",
            "ename": result["error"]["ename"],
            "evalue": result["error"]["evalue"],
            "traceback": result["error"]["traceback"],
        })
    return outputs


_KV_LINE_RE = re.compile(r"^\s{0,4}([A-Za-z][A-Za-z0-9 _\-\(\)/+%]{1,40}?)\s*[:=]\s+(.{1,200}?)\s*$")
_HEADLINE_PATTERNS = [
    (re.compile(r"falsifiability check\s+PASSED", re.I),  "✅ Falsifiability gate **PASSED**"),
    (re.compile(r"falsifiability check\s+FAILED", re.I),  "❌ Falsifiability gate **FAILED**"),
    (re.compile(r"NotImplementedError",          re.I),  "⛔️ Researcher gate hit (`NotImplementedError`) — needs human action or iteration"),
    (re.compile(r"\bSpearman\s*ρ\s*=\s*([-\d.]+)", re.I), "📈 Spearman ρ = `\\1`"),
    (re.compile(r"pooled-rho range:\s*([-\d.]+)\s*[–\-]\s*([\d.]+)"), "📈 pooled-ρ range `\\1`–`\\2`"),
    (re.compile(r"after locus filter:\s+([\d,]+) pairs"), "🔍 after locus filter: **\\1** pairs"),
    (re.compile(r"pair coverage\s*:\s*([\d,/]+)"), "📊 eplet coverage: **\\1**"),
    (re.compile(r"falsifiability check"), None),  # suppress generic
]


def _try_render_kv_table(stdout: str) -> str | None:
    """If stdout consists mostly of `key: value` lines, render as markdown table."""
    rows: list[tuple[str, str]] = []
    other = 0
    for raw_line in stdout.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        m = _KV_LINE_RE.match(line)
        if m:
            rows.append((m.group(1).strip(), m.group(2).strip()))
        else:
            other += 1
    if len(rows) < 3 or len(rows) < other:
        return None
    out = ["| Field | Value |", "|---|---|"]
    for k, v in rows:
        # Escape pipes inside values
        out.append(f"| `{k}` | {v.replace('|', '&#124;')} |")
    return "\n".join(out)


def _extract_headlines(stdout: str) -> list[str]:
    headlines: list[str] = []
    for pat, repl in _HEADLINE_PATTERNS:
        if repl is None:
            continue
        m = pat.search(stdout)
        if m:
            headlines.append(pat.sub(repl, m.group(0)))
    return headlines


def _summarize_result(result: dict, max_chars: int = 1500) -> str:
    """Human-readable observation drawn from the cell result.

    Format (markdown):
      ✅ / ❌ / ⛔️  Status line
      📈 / 🔍 / 📊  One-line headlines extracted from stdout
      🖼  N figure(s) rendered above (when display_data has images)
      stdout — rendered as a markdown table when it's mostly key:value, else as
              a fenced block (truncated to max_chars).
      stderr — fenced block when present.
    """
    lines: list[str] = []
    if result["status"] == "ok":
        lines.append("**Status:** ✅ executed cleanly")
    else:
        err = result["error"]
        lines.append(f"**Status:** ❌ failed — `{err['ename']}: {err['evalue']}`")

    headlines = _extract_headlines(result["stdout"]) if result["stdout"] else []
    for h in headlines:
        lines.append(h)

    n_plotly = 0
    n_imgs = 0
    for d in result.get("displays") or []:
        mime_map = d.get("all_mime") or ({} if d.get("type") != "image/png" else {"image/png": d.get("data")})
        if any(k.startswith("application/vnd.plotly") for k in mime_map):
            n_plotly += 1
        elif "image/png" in mime_map or d.get("type") == "image/png":
            n_imgs += 1
    if n_plotly:
        lines.append(f"📊  **{n_plotly} interactive Plotly figure(s)** rendered above (zoom · pan · hover · legend filtering)")
    if n_imgs:
        lines.append(f"🖼  **{n_imgs} figure(s)** rendered above")

    if result["stdout"]:
        body = result["stdout"].strip()
        if len(body) > max_chars:
            body = body[:max_chars] + "\n…(truncated)"
        table = _try_render_kv_table(body)
        if table:
            lines.append("")
            lines.append(table)
        else:
            lines.append("")
            lines.append("```")
            lines.append(body)
            lines.append("```")
    if result["stderr"]:
        body = result["stderr"].strip()
        if len(body) > max_chars:
            body = body[:max_chars] + "\n…(truncated)"
        lines.append("")
        lines.append("**stderr**:")
        lines.append("```")
        lines.append(body)
        lines.append("```")
    return "\n".join(lines)


def _load_notebook(path: Path) -> dict:
    return json.loads(path.read_text())


def _save_notebook(path: Path, nb: dict) -> None:
    path.write_text(json.dumps(nb, indent=1))


def _is_observation_cell(cell: dict) -> bool:
    if cell.get("cell_type") != "markdown":
        return False
    src = "".join(cell.get("source") or [])
    return src.lstrip().startswith("> **Observation")


def cmd_exec(args: argparse.Namespace) -> None:
    kc, state = _client_from_state()
    nb_path = Path(state.get("notebook") or DEFAULT_NOTEBOOK)
    nb = _load_notebook(nb_path)
    cells = nb["cells"]
    if not (0 <= args.cell < len(cells)):
        sys.exit(f"cell index {args.cell} out of range (0..{len(cells)-1})")
    cell = cells[args.cell]
    if cell["cell_type"] != "code":
        sys.exit(f"cell {args.cell} is {cell['cell_type']}, not code")

    src = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
    print(f"=== executing cell [{args.cell}] ({len(src.splitlines())} lines) ===")
    result = _execute(kc, src)

    cell["outputs"] = _make_outputs(result)
    cell["execution_count"] = (cell.get("execution_count") or 0) + 1

    obs_md = (
        f"> **Observation (cell {args.cell})** — {time.strftime('%Y-%m-%d %H:%M:%S')}\n>\n"
        + "\n".join("> " + ln for ln in _summarize_result(result).splitlines())
    )
    obs_cell = {
        "cell_type": "markdown",
        "metadata": {"deltasci": {"kind": "observation", "of_cell": args.cell}},
        "source": obs_md.splitlines(keepends=True),
    }

    next_idx = args.cell + 1
    if next_idx < len(cells) and _is_observation_cell(cells[next_idx]):
        cells[next_idx] = obs_cell
        action = "replaced"
    else:
        cells.insert(next_idx, obs_cell)
        action = "inserted"

    _save_notebook(nb_path, nb)

    print(f"  status: {result['status']}")
    print(f"  stdout: {len(result['stdout'])} chars · stderr: {len(result['stderr'])} chars · displays: {len(result['displays'])}")
    print(f"  observation: {action} at cell {next_idx}")
    if result["error"]:
        print(f"  error: {result['error']['ename']}: {result['error']['evalue']}")
    kc.stop_channels()


def cmd_patch(args: argparse.Namespace) -> None:
    """Replace the source of cell N with the contents of a file (used to iterate)."""
    state = _load_state()
    nb_path = Path(state.get("notebook") or DEFAULT_NOTEBOOK)
    nb = _load_notebook(nb_path)
    if not (0 <= args.cell < len(nb["cells"])):
        sys.exit(f"cell index {args.cell} out of range")
    new_src = Path(args.source).read_text()
    cells = nb["cells"]
    cells[args.cell]["source"] = new_src.splitlines(keepends=True)
    cells[args.cell]["outputs"] = []
    cells[args.cell]["execution_count"] = None
    _save_notebook(nb_path, nb)
    print(f"patched cell {args.cell} from {args.source}")


def cmd_stop(args: argparse.Namespace) -> None:
    state = _load_state()
    from jupyter_client.blocking import BlockingKernelClient

    kc = BlockingKernelClient()
    kc.load_connection_file(state["connection_file"])
    kc.start_channels()
    try:
        kc.shutdown(restart=False)
    except Exception:
        pass
    kc.stop_channels()
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("kernel stopped")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pstart = sub.add_parser("start")
    pstart.add_argument("--notebook", default=str(DEFAULT_NOTEBOOK))
    pstart.set_defaults(func=cmd_start)
    pexec = sub.add_parser("exec")
    pexec.add_argument("cell", type=int)
    pexec.set_defaults(func=cmd_exec)
    ppatch = sub.add_parser("patch")
    ppatch.add_argument("cell", type=int)
    ppatch.add_argument("source", help="path to a file containing new cell source")
    ppatch.set_defaults(func=cmd_patch)
    pstop = sub.add_parser("stop")
    pstop.set_defaults(func=cmd_stop)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
