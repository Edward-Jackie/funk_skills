#!/usr/bin/env bash
# Report role-aware CODEMAP size limits. This script never edits maps.

set -uo pipefail

DIR="${1:-.map}"
INDEX_LIMIT="${2:-120}"
DOMAIN_LIMIT="${3:-240}"

shopt -s nullglob
files=("$DIR"/CODEMAP*.md)
if [ ${#files[@]} -eq 0 ]; then
  echo "'$DIR' 下没有 CODEMAP*.md。"
  exit 0
fi

over=0
printf '%-44s %7s %7s  %s\n' "文件" "行数" "上限" "状态"
printf '%-44s %7s %7s  %s\n' "----" "----" "----" "----"
for file in "${files[@]}"; do
  lines="$(wc -l < "$file" | tr -d ' ')"
  limit="$DOMAIN_LIMIT"
  [ "$(basename "$file")" = "CODEMAP.md" ] && limit="$INDEX_LIMIT"
  if [ "$lines" -gt "$limit" ]; then
    printf '%-44s %7s %7s  超出\n' "$file" "$lines" "$limit"
    over=$((over + 1))
  else
    printf '%-44s %7s %7s  正常\n' "$file" "$lines" "$limit"
  fi
done

echo
if [ "$over" -gt 0 ]; then
  echo "$over 个文件超限。拆分领域或删除可从源码即时恢复的内容；保留 manual 块。"
  exit 1
fi

echo "所有地图均在限制内。"
