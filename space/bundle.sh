#!/usr/bin/env bash
# Copy the current deltasci source into ./pkg so the Space image is self-contained
# (and carries this session's code: coverage + Crossref title-resolution). Run before push.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf pkg
mkdir -p pkg
cp -R ../src pkg/src
cp ../pyproject.toml pkg/pyproject.toml
[ -f ../README.md ] && cp ../README.md pkg/README.md || true
echo "bundled deltasci source into space/pkg/  (run this before pushing to HF)"
