#!/bin/bash
# DeltaScience Claude Code skill installer.
#
# Usage:
#   bash skill/install.sh                        # symlink to ~/.claude/skills/deltasci
#   bash skill/install.sh /path/to/project       # symlink to <project>/.claude/skills/deltasci

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "${1:-}" ]; then
  TARGET="$1/.claude/skills/deltasci"
  mkdir -p "$1/.claude/skills"
else
  TARGET="$HOME/.claude/skills/deltasci"
  mkdir -p "$HOME/.claude/skills"
fi

if [ -e "$TARGET" ]; then
  echo "EXISTS: $TARGET"
  exit 0
fi

ln -s "$SCRIPT_DIR" "$TARGET"
echo "INSTALLED: $TARGET -> $SCRIPT_DIR"
echo
echo "Next: open Claude Code and ask:"
echo "  'Use deltasci with the biomed pack to generate a hypothesis for [your idea]'"
