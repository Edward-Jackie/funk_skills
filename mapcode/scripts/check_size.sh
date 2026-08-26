#!/usr/bin/env bash
# 检查业务地图文件是否超过行数阈值，只报告大小，不修改文件。

set -uo pipefail

TARGET="${1:-docs/ai}"
THRESHOLD="${2:-200}"

shopt -s nullglob
if [ -f "$TARGET" ]; then
  DIR="$(dirname "$TARGET")"
  BASE="$(basename "$TARGET" .md)"
  files=("$TARGET" "$DIR"/"$BASE"-*.md "$DIR"/business/*.md)
else
  DIR="$TARGET"
  files=("$DIR"/BUSINESS_MAP*.md "$DIR"/MAPCODE*.md "$DIR"/business/*.md)
fi
if [ ${#files[@]} -eq 0 ]; then
  echo "'$TARGET' 下没有业务地图文件。"
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
  echo "$over 个文件超过 ${THRESHOLD} 行。拆分业务域时必须原样保留 <!-- manual --> 块。"
else
  echo "所有文件均未超过阈值。"
fi
