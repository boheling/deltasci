// Inline notebook renderer (v0.3.0). Read-only, no extra npm deps.
// Markdown cells: lightweight md→inline transforms (#, **bold**, `code`, lists).
// Code cells: monospace block with syntax-light styling.

import type * as React from 'react';
import type { NotebookBundle, NotebookCell, NotebookOutput } from '@/lib/types';
import { PlotlyFig, type PlotlyFigure } from './plotly';

export function NotebookView({ bundle }: { bundle: NotebookBundle }) {
  const cells = bundle.notebook.cells || [];
  return (
    <div className="space-y-3">
      <div className="rounded border border-warm/30 bg-warm-soft/40 p-4 font-serif text-[13px] leading-relaxed text-ink">
        <p className="font-sans text-[12px] font-semibold uppercase tracking-wider text-warm">
          Scaffold — not auto-run
        </p>
        <p className="mt-1">
          This notebook is generated from the experiment plan. The AI did not run it. Look for{' '}
          <code className="rounded-sm bg-ink/8 px-1 font-mono text-[12px]">{'# TODO'}</code> markers
          — those mark the substantive customizations the scaffold cannot do for you. Boilerplate
          (imports, data structures, evaluation framing) is correct by construction.
        </p>
      </div>

      <ol className="space-y-3">
        {cells.map((cell, i) => (
          <CellBlock key={i} cell={cell} index={i} />
        ))}
      </ol>

      {bundle.requirements && (
        <details className="rounded border border-slate-border/15 bg-white/60 p-4">
          <summary className="cursor-pointer font-sans text-[13px] font-medium text-ink">
            requirements.txt ({bundle.requirements.split('\n').filter((l) => l.trim() && !l.trim().startsWith('#')).length} packages)
          </summary>
          <pre className="mt-3 overflow-x-auto rounded-sm bg-ink/5 p-3 font-mono text-[12px] leading-relaxed text-ink/85">
            {bundle.requirements}
          </pre>
        </details>
      )}
    </div>
  );
}

function CellBlock({ cell, index }: { cell: NotebookCell; index: number }) {
  const source = Array.isArray(cell.source) ? cell.source.join('') : cell.source ?? '';
  if (cell.cell_type === 'markdown') {
    return (
      <li className="rounded border border-slate-border/10 bg-white/40 p-4">
        <span className="font-mono text-[10px] uppercase tracking-wider text-ink/40">
          [{index + 1}] markdown
        </span>
        <div className="mt-2 font-serif text-[14px] leading-relaxed text-ink">
          <Markdown source={source} />
        </div>
      </li>
    );
  }
  if (cell.cell_type === 'code') {
    const isToDo = source.includes('TODO');
    return (
      <li className={'rounded border bg-white/60 ' + (isToDo ? 'border-warm/40' : 'border-slate-border/15')}>
        <div className="flex items-baseline justify-between border-b border-slate-border/15 px-4 py-2">
          <span className="font-mono text-[10px] uppercase tracking-wider text-ink/40">
            [{index + 1}] code
          </span>
          {isToDo && (
            <span className="rounded-sm bg-warm-soft px-1.5 py-0.5 font-mono text-[10px] text-warm">
              contains TODO
            </span>
          )}
        </div>
        <pre className="overflow-x-auto p-4 font-mono text-[12px] leading-relaxed text-ink/90">
          <code>{highlightPython(source)}</code>
        </pre>
        {cell.outputs && cell.outputs.length > 0 && <CellOutputs outputs={cell.outputs} />}
      </li>
    );
  }
  return (
    <li className="rounded border border-slate-border/10 bg-white/40 p-4 font-mono text-[12px] text-ink/70">
      [{index + 1}] {cell.cell_type}: {source.slice(0, 200)}
    </li>
  );
}

// --- Cell outputs (stream text + display_data PNG + errors) -----------------

function asString(s: string | string[]): string {
  return Array.isArray(s) ? s.join('') : s;
}

function pickPlotlyFigure(
  data: Record<string, unknown> | undefined,
): PlotlyFigure | null {
  if (!data) return null;
  // Jupyter ships plotly figures under either of these MIME types depending on
  // version. Both carry the same `{data, layout, config?}` shape.
  const raw = data['application/vnd.plotly.v1+json'] ?? data['application/json'];
  if (!raw || typeof raw !== 'object') return null;
  const obj = raw as Record<string, unknown>;
  if (!Array.isArray(obj.data)) return null;
  return {
    data: obj.data,
    layout: (obj.layout as Record<string, unknown>) ?? {},
    config: (obj.config as Record<string, unknown>) ?? {},
  };
}

function CellOutputs({ outputs }: { outputs: NotebookOutput[] }) {
  return (
    <div className="border-t border-slate-border/15 bg-white/40 px-4 py-3 space-y-3">
      {outputs.map((out, i) => {
        if (out.output_type === 'stream') {
          const text = asString(out.text);
          if (!text.trim()) return null;
          const isErr = out.name === 'stderr';
          return (
            <pre
              key={i}
              className={
                'overflow-x-auto rounded-sm px-3 py-2 font-mono text-[11px] leading-relaxed ' +
                (isErr ? 'bg-burgundy/8 text-burgundy' : 'bg-ink/5 text-ink/85')
              }
            >
              {text}
            </pre>
          );
        }
        if (out.output_type === 'display_data' || out.output_type === 'execute_result') {
          // Prefer Plotly (interactive) over PNG (static). The cell may emit
          // both as a fallback for non-Plotly viewers; pick the richer one.
          const plotly = pickPlotlyFigure(out.data);
          if (plotly) {
            return <PlotlyFig key={i} figure={plotly} />;
          }
          const png = out.data?.['image/png'];
          if (typeof png === 'string' || Array.isArray(png)) {
            const src = `data:image/png;base64,${asString(png as string | string[]).replace(/\s+/g, '')}`;
            return (
              <img
                key={i}
                src={src}
                alt="cell figure"
                className="max-w-full rounded border border-slate-border/15 bg-white"
              />
            );
          }
          const txt = out.data?.['text/plain'];
          if (typeof txt === 'string' || Array.isArray(txt)) {
            return (
              <pre
                key={i}
                className="overflow-x-auto rounded-sm bg-ink/5 px-3 py-2 font-mono text-[11px] text-ink/85"
              >
                {asString(txt as string | string[])}
              </pre>
            );
          }
          return null;
        }
        if (out.output_type === 'error') {
          return (
            <div
              key={i}
              className="rounded-sm border border-burgundy/30 bg-warm-soft/40 px-3 py-2 font-mono text-[11px] text-burgundy"
            >
              <div className="font-sans text-[11px] font-semibold uppercase tracking-wider">
                {out.ename}: {out.evalue}
              </div>
            </div>
          );
        }
        return null;
      })}
    </div>
  );
}

// --- Markdown renderer (minimal, no deps) ----------------------------------

function Markdown({ source }: { source: string }) {
  // Detect a top-level blockquote — render with a left-bar and recurse.
  const trimmed = source.trim();
  const allBlockquoted =
    trimmed.length > 0 &&
    trimmed.split('\n').every((l) => l.startsWith('>') || l === '');
  if (allBlockquoted) {
    const inner = trimmed
      .split('\n')
      .map((l) => l.replace(/^>\s?/, ''))
      .join('\n');
    return (
      <blockquote className="border-l-2 border-teal/40 pl-4">
        <Markdown source={inner} />
      </blockquote>
    );
  }

  // Tokenize into block-level units by walking lines (so we can recognize
  // fences + tables which are multi-line constructs).
  const blocks = parseBlocks(source);

  return (
    <>
      {blocks.map((block, i) => {
        if (block.kind === 'heading') {
          const cls = block.level === 1 ? 'text-[20px] font-semibold' : block.level === 2 ? 'text-[17px] font-semibold' : 'text-[15px] font-semibold';
          return (
            <p key={i} className={`mb-2 mt-3 first:mt-0 ${cls}`}>
              <Inline text={block.text} />
            </p>
          );
        }
        if (block.kind === 'list') {
          return (
            <ul key={i} className="my-2 list-disc pl-5">
              {block.items.map((line, j) => (
                <li key={j}>
                  <Inline text={line} />
                </li>
              ))}
            </ul>
          );
        }
        if (block.kind === 'fence') {
          return (
            <pre
              key={i}
              className="my-2 overflow-x-auto rounded-sm bg-ink/5 px-3 py-2 font-mono text-[11px] leading-relaxed text-ink/85"
            >
              {block.text}
            </pre>
          );
        }
        if (block.kind === 'table') {
          return (
            <table key={i} className="my-3 border-collapse text-[12px]">
              <thead>
                <tr>
                  {block.header.map((h, j) => (
                    <th key={j} className="border border-slate-border/30 bg-ink/5 px-2 py-1 text-left font-sans font-semibold">
                      <Inline text={h} />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {block.rows.map((row, r) => (
                  <tr key={r}>
                    {row.map((cell, c) => (
                      <td key={c} className="border border-slate-border/20 px-2 py-1 align-top">
                        <Inline text={cell} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          );
        }
        // Paragraph
        return (
          <p key={i} className="my-2">
            <Inline text={block.text} />
          </p>
        );
      })}
    </>
  );
}

type Block =
  | { kind: 'heading'; level: number; text: string }
  | { kind: 'list'; items: string[] }
  | { kind: 'fence'; text: string }
  | { kind: 'table'; header: string[]; rows: string[][] }
  | { kind: 'paragraph'; text: string };

function parseBlocks(source: string): Block[] {
  const lines = source.split('\n');
  const out: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }

    // Fenced code
    if (/^```/.test(line.trim())) {
      const buf: string[] = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i].trim())) {
        buf.push(lines[i]);
        i++;
      }
      i++; // skip closing fence
      out.push({ kind: 'fence', text: buf.join('\n') });
      continue;
    }

    // Table — header line + separator line + zero or more body lines
    if (line.trim().startsWith('|') && i + 1 < lines.length && /^\s*\|?\s*-/.test(lines[i + 1])) {
      const header = parseRow(line);
      i += 2; // header + separator
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        rows.push(parseRow(lines[i]));
        i++;
      }
      out.push({ kind: 'table', header, rows });
      continue;
    }

    // Heading
    const h = line.match(/^(#{1,6})\s+(.+)$/);
    if (h) {
      out.push({ kind: 'heading', level: h[1].length, text: h[2] });
      i++;
      continue;
    }

    // List
    if (/^[\s]*[-*]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[\s]*[-*]\s/.test(lines[i])) {
        items.push(lines[i].replace(/^[\s]*[-*]\s+/, ''));
        i++;
      }
      out.push({ kind: 'list', items });
      continue;
    }

    // Paragraph: collect contiguous non-blank lines that aren't a special block.
    const para: string[] = [line];
    i++;
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^```/.test(lines[i].trim()) &&
      !/^(#{1,6})\s/.test(lines[i]) &&
      !/^[\s]*[-*]\s/.test(lines[i]) &&
      !(lines[i].trim().startsWith('|') && i + 1 < lines.length && /^\s*\|?\s*-/.test(lines[i + 1]))
    ) {
      para.push(lines[i]);
      i++;
    }
    out.push({ kind: 'paragraph', text: para.join(' ') });
  }
  return out;
}

function parseRow(line: string): string[] {
  return line
    .replace(/^\s*\|/, '')
    .replace(/\|\s*$/, '')
    .split('|')
    .map((c) => c.trim());
}

// Inline transforms: **bold**, *italic*, `code`. Done in one pass via tokenizer
// so we don't have to write nested regex.
function Inline({ text }: { text: string }) {
  const tokens = tokenizeInline(text);
  return (
    <>
      {tokens.map((t, i) => {
        if (t.kind === 'code') {
          return (
            <code
              key={i}
              className="rounded-sm bg-ink/8 px-1 font-mono text-[12px] text-ink"
            >
              {t.text}
            </code>
          );
        }
        if (t.kind === 'bold') return <strong key={i}>{t.text}</strong>;
        if (t.kind === 'italic') return <em key={i}>{t.text}</em>;
        return <span key={i}>{t.text}</span>;
      })}
    </>
  );
}

type InlineToken = { kind: 'text' | 'bold' | 'italic' | 'code'; text: string };
const INLINE_RE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*]+\*)/g;

function tokenizeInline(s: string): InlineToken[] {
  const out: InlineToken[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = INLINE_RE.exec(s)) !== null) {
    if (m.index > last) {
      out.push({ kind: 'text', text: s.slice(last, m.index) });
    }
    if (m[1]) out.push({ kind: 'code', text: m[1].slice(1, -1) });
    else if (m[2]) out.push({ kind: 'bold', text: m[2].slice(2, -2) });
    else if (m[3]) out.push({ kind: 'italic', text: m[3].slice(1, -1) });
    last = INLINE_RE.lastIndex;
  }
  if (last < s.length) out.push({ kind: 'text', text: s.slice(last) });
  return out;
}

// --- Tiny Python syntax styling --------------------------------------------
// Keep this trivial: comments + strings + keywords. Anything fancier needs prismjs.

const PY_KEYWORDS = new Set([
  'def', 'class', 'return', 'import', 'from', 'as', 'if', 'elif', 'else',
  'for', 'while', 'try', 'except', 'finally', 'raise', 'with', 'in', 'is',
  'not', 'and', 'or', 'pass', 'break', 'continue', 'lambda', 'yield', 'None',
  'True', 'False', 'self', 'global', 'nonlocal', 'assert', 'async', 'await',
]);

function highlightPython(source: string): React.ReactNode[] {
  // Tokenize line by line. Comments dominate (so a line starting with # has no other tokens).
  const out: React.ReactNode[] = [];
  const lines = source.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim().startsWith('#')) {
      const isTodo = line.includes('TODO');
      out.push(
        <span
          key={i}
          className={isTodo ? 'text-warm font-semibold' : 'text-ink/55'}
        >
          {line}
        </span>,
      );
    } else {
      const parts = tokenizePythonLine(line);
      out.push(
        <span key={i}>
          {parts.map((p, j) => {
            if (p.kind === 'string') {
              return <span key={j} className="text-teal">{p.text}</span>;
            }
            if (p.kind === 'keyword') {
              return <span key={j} className="text-burgundy font-semibold">{p.text}</span>;
            }
            return <span key={j}>{p.text}</span>;
          })}
        </span>,
      );
    }
    if (i < lines.length - 1) out.push(<span key={`nl${i}`}>{'\n'}</span>);
  }
  return out;
}

type PyToken = { kind: 'text' | 'string' | 'keyword'; text: string };
const PY_RE = /('[^'\n]*'|"[^"\n]*")|(\b\w+\b)/g;

function tokenizePythonLine(line: string): PyToken[] {
  const out: PyToken[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = PY_RE.exec(line)) !== null) {
    if (m.index > last) out.push({ kind: 'text', text: line.slice(last, m.index) });
    if (m[1]) out.push({ kind: 'string', text: m[1] });
    else if (m[2] && PY_KEYWORDS.has(m[2])) out.push({ kind: 'keyword', text: m[2] });
    else out.push({ kind: 'text', text: m[0] });
    last = PY_RE.lastIndex;
  }
  if (last < line.length) out.push({ kind: 'text', text: line.slice(last) });
  return out;
}
