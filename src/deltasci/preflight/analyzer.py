"""Static notebook analyzer for the deltasci preflight subcommand."""

from __future__ import annotations

import ast
import builtins
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Names always available in any Python kernel — don't flag these as undefined.
_BUILTIN_NAMES: frozenset[str] = frozenset(dir(builtins)) | frozenset(
    {
        "__name__", "__file__", "__doc__", "Ellipsis", "NotImplemented",
        # Common ipython display names that aren't in builtins
        "display", "get_ipython", "In", "Out",
    }
)


@dataclass
class CellFinding:
    cell_index: int
    cell_type: str  # "code" or "markdown"
    severity: str   # "info" | "warning" | "error"
    kind: str       # "todo" | "placeholder" | "researcher_gate" | "name_error" | "missing_file"
    message: str
    snippet: str = ""


@dataclass
class PreflightReport:
    notebook_path: Path
    cell_count: int
    code_cell_count: int
    findings: list[CellFinding] = field(default_factory=list)

    def by_kind(self, kind: str) -> list[CellFinding]:
        return [f for f in self.findings if f.kind == kind]

    @property
    def has_errors(self) -> bool:
        return any(f.severity == "error" for f in self.findings)

    def to_json(self) -> str:
        return json.dumps(
            {
                "notebook_path": str(self.notebook_path),
                "cell_count": self.cell_count,
                "code_cell_count": self.code_cell_count,
                "summary": {
                    "todo_count": len(self.by_kind("todo")),
                    "placeholder_count": len(self.by_kind("placeholder")),
                    "researcher_gate_count": len(self.by_kind("researcher_gate")),
                    "name_error_count": len(self.by_kind("name_error")),
                    "missing_file_count": len(self.by_kind("missing_file")),
                    "has_errors": self.has_errors,
                },
                "findings": [
                    {
                        "cell_index": f.cell_index,
                        "cell_type": f.cell_type,
                        "severity": f.severity,
                        "kind": f.kind,
                        "message": f.message,
                        "snippet": f.snippet,
                    }
                    for f in self.findings
                ],
            },
            indent=2,
        )

    def render_terminal(self) -> str:
        lines: list[str] = []
        lines.append(f"Preflight: {self.notebook_path}")
        lines.append(f"  cells: {self.cell_count} ({self.code_cell_count} code)")
        c = {k: len(self.by_kind(k)) for k in ("todo", "placeholder", "researcher_gate", "name_error", "missing_file")}
        lines.append(
            f"  TODOs: {c['todo']} · PLACEHOLDERs: {c['placeholder']} · "
            f"researcher gates: {c['researcher_gate']} · name errors: {c['name_error']} · missing files: {c['missing_file']}"
        )
        lines.append("")
        if not self.findings:
            lines.append("  ✓ no findings — notebook is preflight-clean.")
            return "\n".join(lines)

        # Group by severity
        for severity, marker in (("error", "✗"), ("warning", "⚠"), ("info", "ℹ")):
            group = [f for f in self.findings if f.severity == severity]
            if not group:
                continue
            lines.append(f"  {marker} {severity.upper()}S ({len(group)}):")
            for f in group:
                lines.append(f"    cell {f.cell_index} [{f.kind}] {f.message}")
                if f.snippet:
                    lines.append(f"      → {f.snippet[:120]}")
            lines.append("")

        # Researcher checklist
        gates = self.by_kind("researcher_gate")
        if gates:
            lines.append("Researcher checklist (resolve before running):")
            for i, f in enumerate(gates, 1):
                lines.append(f"  {i}. cell {f.cell_index}: {f.message}")
        return "\n".join(lines)


def analyze_notebook(notebook_path: str | Path) -> PreflightReport:
    """Run all preflight checks on a single .ipynb."""

    path = Path(notebook_path)
    nb = json.loads(path.read_text(encoding="utf-8"))
    cells = nb.get("cells", []) or []
    code_cells = [c for c in cells if c.get("cell_type") == "code"]

    report = PreflightReport(
        notebook_path=path,
        cell_count=len(cells),
        code_cell_count=len(code_cells),
    )

    # Collect defined names across cells in order — for cross-cell name analysis
    cumulative_defined: set[str] = set()

    for idx, cell in enumerate(cells):
        cell_type = cell.get("cell_type", "")
        source = _cell_source_string(cell)
        if not source.strip():
            continue

        # 1. TODO / PLACEHOLDER markers (regex; works on both markdown and code)
        for m in re.finditer(r"#\s*(TODO|PLACEHOLDER)\b[:\s]*(.*?)$", source, re.MULTILINE):
            kind = "todo" if m.group(1) == "TODO" else "placeholder"
            report.findings.append(CellFinding(
                cell_index=idx, cell_type=cell_type,
                severity="info" if kind == "todo" else "warning",
                kind=kind, message=m.group(2).strip()[:120] or "(no message)", snippet=m.group(0).strip(),
            ))

        if cell_type != "code":
            continue

        # 2. Researcher-gate detection: explicit `raise NotImplementedError(...)` calls
        for gate in _find_researcher_gates(source):
            report.findings.append(CellFinding(
                cell_index=idx, cell_type=cell_type, severity="error",
                kind="researcher_gate", message=gate,
                snippet="raise NotImplementedError(...)",
            ))

        # 3. Cross-cell name analysis (NameError-prone references)
        defined_in_cell, used_in_cell = _names_defined_and_used(source)
        for name in sorted(used_in_cell):
            if name in cumulative_defined:
                continue
            if name in defined_in_cell:
                continue
            if name in _BUILTIN_NAMES:
                continue
            if _name_is_dotted_attribute_only(name, source):
                continue
            # Skip names that look like imports we've already seen
            report.findings.append(CellFinding(
                cell_index=idx, cell_type=cell_type, severity="error",
                kind="name_error",
                message=f"name {name!r} used but not defined in any prior cell",
                snippet=_first_line_containing(source, name),
            ))
        cumulative_defined |= defined_in_cell

    return report


# ---- helpers ---------------------------------------------------------------


def _cell_source_string(cell: dict) -> str:
    src = cell.get("source", "")
    if isinstance(src, list):
        return "".join(src)
    return src or ""


def _find_researcher_gates(source: str) -> list[str]:
    """Find explicit `raise NotImplementedError(...)` calls + extract their messages."""

    gates: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return gates

    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and node.exc is not None:
            exc = node.exc
            if isinstance(exc, ast.Call) and _is_not_implemented_error(exc.func):
                msg = _extract_call_arg_text(exc) or "(no message)"
                gates.append(msg)
    return gates


def _is_not_implemented_error(node: ast.AST) -> bool:
    if isinstance(node, ast.Name) and node.id == "NotImplementedError":
        return True
    if isinstance(node, ast.Attribute) and node.attr == "NotImplementedError":
        return True
    return False


def _extract_call_arg_text(call: ast.Call) -> str:
    """Best-effort extract of the literal/f-string message arg of a Raise call."""

    if not call.args:
        return ""
    arg = call.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    if isinstance(arg, ast.JoinedStr):
        # f-string: stitch together literal parts; show {var} for FormattedValue
        out: list[str] = []
        for part in arg.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                out.append(part.value)
            elif isinstance(part, ast.FormattedValue):
                out.append("{" + ast.unparse(part.value) + "}")
        return "".join(out)
    if isinstance(arg, ast.BinOp):
        # String concatenation via `+`; collect Constants.
        return _extract_binop_concat(arg)
    return ""


def _extract_binop_concat(node: ast.BinOp) -> str:
    parts: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            parts.append(child.value)
    return "".join(parts)


def _names_defined_and_used(source: str) -> tuple[set[str], set[str]]:
    """Return (names defined anywhere in this cell, names used as Load context)."""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set(), set()

    defined: set[str] = set()
    used: set[str] = set()

    class _Walker(ast.NodeVisitor):
        def visit_Assign(self, node):
            for target in node.targets:
                self._collect_assign_targets(target, defined)
            self.generic_visit(node)

        def visit_AnnAssign(self, node):
            if isinstance(node.target, ast.Name):
                defined.add(node.target.id)
            self.generic_visit(node)

        def visit_AugAssign(self, node):
            if isinstance(node.target, ast.Name):
                defined.add(node.target.id)
            self.generic_visit(node)

        def visit_For(self, node):
            self._collect_assign_targets(node.target, defined)
            self.generic_visit(node)

        def visit_With(self, node):
            for item in node.items:
                if item.optional_vars is not None:
                    self._collect_assign_targets(item.optional_vars, defined)
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            defined.add(node.name)
            # Recurse into body but use the function-local scope cheating:
            # we want defined names visible to subsequent cells, so skip body
            # walking (would over-add locals).

        def visit_AsyncFunctionDef(self, node):
            defined.add(node.name)

        def visit_ClassDef(self, node):
            defined.add(node.name)

        def visit_Import(self, node):
            for alias in node.names:
                defined.add((alias.asname or alias.name).split(".")[0])

        def visit_ImportFrom(self, node):
            for alias in node.names:
                if alias.name == "*":
                    continue
                defined.add(alias.asname or alias.name)

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                used.add(node.id)
            elif isinstance(node.ctx, (ast.Store, ast.Del)):
                defined.add(node.id)

        def visit_Lambda(self, node):
            # Don't recurse — lambda args shouldn't pollute outer scope.
            for arg in node.args.args:
                pass

        def _collect_assign_targets(self, target: ast.AST, into: set[str]) -> None:
            if isinstance(target, ast.Name):
                into.add(target.id)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for elt in target.elts:
                    self._collect_assign_targets(elt, into)
            elif isinstance(target, ast.Starred):
                self._collect_assign_targets(target.value, into)

    _Walker().visit(tree)
    # Names that are defined in this cell shouldn't show up in the cross-cell
    # used-but-not-defined check.
    return defined, used - defined


def _name_is_dotted_attribute_only(name: str, source: str) -> bool:
    """Heuristic: skip names that only ever appear as attributes (e.g. `self.foo`).

    The AST already filters this — `node.attr` isn't an `ast.Name`. Keep this
    helper as a defensive backstop for false positives we haven't caught yet.
    """

    return False


def _first_line_containing(source: str, token: str) -> str:
    for line in source.splitlines():
        if token in line:
            return line.strip()
    return ""
