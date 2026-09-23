#!/usr/bin/env bash
# Count non-generated source files as one layering signal, not the decision itself.
#
# Usage:
#   scripts/count_sources.sh [ROOT]                          # ROOT defaults to "."
#   CODEMAP_EXCLUDE='regex' scripts/count_sources.sh [ROOT]  # add project-specific excludes
#
# Prints a count, per-extension breakdown, and a size hint. Business-chain count,
# cross-domain coupling, and the 120-line L1 budget can still require L2 packages.

set -uo pipefail

ROOT="${1:-.}"

# Dependency / build-output / VCS dirs — never hand-written source.
EXCLUDE_DIRS='/(\.git|node_modules|vendor|dist|build|out|target|coverage|__pycache__|\.venv|venv|\.next|\.nuxt|\.idea|\.vscode|bin|obj)/'
# Generated / lock / minified files.
EXCLUDE_FILES='(\.gen\.go|\.pb\.go|_pb2\.py|\.min\.(js|css)|-lock\.(json|ya?ml)|\.lock|\.map)$|/migrations?/'
# Source extensions worth counting.
EXT='\.(go|py|js|jsx|ts|tsx|vue|java|kt|rb|rs|php|c|h|cc|cpp|hpp|cs|swift|scala|m|sh|sql)$'
# Optional project-specific extra exclude pattern.
EXTRA="${CODEMAP_EXCLUDE:-}"

files="$(find "$ROOT" -type f 2>/dev/null \
  | grep -E "$EXT" \
  | grep -Ev "$EXCLUDE_DIRS" \
  | grep -Ev "$EXCLUDE_FILES" || true)"

if [ -n "$EXTRA" ]; then
  files="$(printf '%s\n' "$files" | grep -Ev "$EXTRA" || true)"
fi

count="$(printf '%s\n' "$files" | grep -c . || true)"
[ -z "$count" ] && count=0

echo "Non-generated source files under '$ROOT': $count"
echo
echo "By extension:"
printf '%s\n' "$files" | grep -oE "$EXT" | sort | uniq -c | sort -rn
echo
if [ "$count" -le 50 ]; then
  echo "Layering hint: <=50 files may fit one .map/CODEMAP.md if business complexity and the 120-line budget also fit."
else
  echo "Layering hint: >50 files usually needs .map/CODEMAP-<domain>.md packages."
fi
