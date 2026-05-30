#!/bin/bash
# DeltaScience grounding-layer skill installer (scan -> gap -> verify).
#
# Usage:
#   bash skill-ground/install.sh                  # symlink to ~/.claude/skills/deltasci-ground
#   bash skill-ground/install.sh /path/to/project # symlink to <project>/.claude/skills/deltasci-ground

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "${1:-}" ]; then
  TARGET="$1/.claude/skills/deltasci-ground"
  mkdir -p "$1/.claude/skills"
else
  TARGET="$HOME/.claude/skills/deltasci-ground"
  mkdir -p "$HOME/.claude/skills"
fi

if [ -e "$TARGET" ]; then
  echo "EXISTS: $TARGET"
  exit 0
fi

ln -s "$SCRIPT_DIR" "$TARGET"
echo "INSTALLED: $TARGET -> $SCRIPT_DIR"
echo
echo "Prereq:  pip install 'deltasci[pdf]'"
echo "Next: open Claude Code and ask:"
echo "  'Ground this idea: <your research idea>'  — or —  'Verify the citations in paper.pdf'"
