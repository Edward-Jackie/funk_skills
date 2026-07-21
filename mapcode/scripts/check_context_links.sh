#!/usr/bin/env bash
# 校验任务路由索引和领域上下文包的链接是否存在。

set -euo pipefail

MAP_FILE="${1:-docs/ai/BUSINESS_MAP.md}"
[ -f "$MAP_FILE" ] || { echo "业务地图不存在：$MAP_FILE" >&2; exit 1; }

for heading in "任务路由索引" "业务域与核心链"; do
  grep -Fq "## $heading" "$MAP_FILE" || {
    echo "缺少章节：$heading" >&2
    exit 1
  }
done

MAP_DIR="$(dirname "$MAP_FILE")"
missing=0
links="$(grep -oE '\]\([^ )#]+\.md\)' "$MAP_FILE" || true)"

while IFS= read -r link; do
  [ -n "$link" ] || continue
  target="${link#](}"
  target="${target%)}"
  case "$target" in
    http://*|https://*) continue ;;
  esac
  if [ ! -f "$MAP_DIR/$target" ]; then
    echo "上下文包不存在：$target" >&2
    missing=1
  fi
done <<< "$links"

if [ "$missing" -ne 0 ]; then
  exit 1
fi

echo "任务路由索引和上下文包链接校验通过。"
