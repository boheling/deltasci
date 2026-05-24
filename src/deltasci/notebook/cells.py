"""ipynb cell helpers — keep pack notebook.py files free of Jupyter JSON noise."""

from __future__ import annotations


def markdown_cell(source: str) -> dict:
    """Build an nbformat 4 markdown cell."""

    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": _to_source_lines(source),
    }


def code_cell(source: str, language: str = "python") -> dict:
    """Build an nbformat 4 code cell. We never produce outputs — generate-only."""

    return {
        "cell_type": "code",
        "metadata": {"language": language},
        "execution_count": None,
        "outputs": [],
        "source": _to_source_lines(source),
    }


def _to_source_lines(text: str) -> list[str]:
    """ipynb stores `source` as either a string or a list of strings.

    We always emit a list with newline-terminated lines — except the last,
    which is unterminated. That matches the convention nbformat 4 documents.
    """

    if not text:
        return []
    lines = text.splitlines(keepends=True)
    return lines
