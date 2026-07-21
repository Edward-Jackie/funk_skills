#!/usr/bin/env bash
# 统计非生成源码文件，作为导航图分层方式的确定依据。

set -uo pipefail

ROOT="${1:-.}"
EXCLUDE_DIRS='/(\.git|node_modules|vendor|dist|build|out|target|coverage|__pycache__|\.venv|venv|\.next|\.nuxt|\.idea|\.vscode|bin|obj)/'
EXCLUDE_FILES='(\.gen\.go|\.pb\.go|_pb2\.py|\.min\.(js|css)|-lock\.(json|ya?ml)|\.lock|\.map)$|/migrations?/'
EXT='\.(go|py|js|jsx|ts|tsx|vue|java|kt|rb|rs|php|c|h|cc|cpp|hpp|cs|swift|scala|m|sh|sql)$'
EXTRA="${MAPCODE_EXCLUDE:-}"

files="$(find "$ROOT" -type f 2>/dev/null \
  | grep -E "$EXT" \
  | grep -Ev "$EXCLUDE_DIRS" \
  | grep -Ev "$EXCLUDE_FILES" || true)"

if [ -n "$EXTRA" ]; then
  files="$(printf '%s\n' "$files" | grep -Ev "$EXTRA" || true)"
fi

count="$(printf '%s\n' "$files" | grep -c . || true)"
[ -z "$count" ] && count=0

echo "'$ROOT' 下非生成源码文件数：$count"
echo
echo "按扩展名统计："
printf '%s\n' "$files" | grep -oE "$EXT" | sort | uniq -c | sort -rn
echo
if [ "$count" -le 50 ]; then
  echo "分层建议：不超过 50 个文件，使用单层 .codex/MAPCODE.md。"
else
  echo "分层建议：超过 50 个文件，使用总览和分模块 MAPCODE 文件。"
fi
