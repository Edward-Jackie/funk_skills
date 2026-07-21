#!/usr/bin/env bash
# 检查 MAPCODE 文件是否超过行数阈值，只报告大小，不修改文件。

set -uo pipefail

DIR="${1:-.codex}"
THRESHOLD="${2:-200}"

shopt -s nullglob
files=("$DIR"/MAPCODE*.md)
if [ ${#files[@]} -eq 0 ]; then
  echo "目录 '$DIR' 下没有 MAPCODE*.md 文件。"
  exit 0
fi

over=0
printf '%-44s %7s  %s\n' "文件" "行数" "状态"
printf '%-44s %7s  %s\n' "----" "----" "----"
for f in "${files[@]}"; do
  n="$(wc -l < "$f" | tr -d ' ')"
  if [ "$n" -gt "$THRESHOLD" ]; then
    printf '%-44s %7s  超出（大于 %s）\n' "$f" "$n" "$THRESHOLD"
    over=$((over + 1))
  else
    printf '%-44s %7s  正常\n' "$f" "$n"
  fi
done

echo
if [ "$over" -gt 0 ]; then
  echo "$over 个文件超过 ${THRESHOLD} 行。拆分调用链时必须原样保留 <!-- manual --> 块。"
else
  echo "所有文件均未超过阈值。"
fi
