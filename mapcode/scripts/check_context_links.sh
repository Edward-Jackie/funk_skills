#!/usr/bin/env bash
# 校验任务路由索引和领域上下文包的链接是否存在。

set -euo pipefail

MAP_FILE="${1:-.codex/MAPCODE.md}"
[ -f "$MAP_FILE" ] || { echo "业务地图不存在：$MAP_FILE" >&2; exit 1; }

MAP_DIR="$(cd "$(dirname "$MAP_FILE")" && pwd)"
ROOT="$(git -C "$MAP_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
MAP_ABS="$MAP_DIR/$(basename "$MAP_FILE")"
if [ "$MAP_ABS" != "$ROOT/.codex/MAPCODE.md" ]; then
  echo "L1 必须位于 .codex/MAPCODE.md：${MAP_ABS#$ROOT/}" >&2
  exit 1
fi

for heading in "任务路由索引" "业务域与核心链"; do
  grep -Fq "## $heading" "$MAP_FILE" || {
    echo "缺少章节：$heading" >&2
    exit 1
  }
done

missing=0
links="$(grep -oE '\]\([^ )#]+\.md\)' "$MAP_FILE" || true)"

while IFS= read -r link; do
  [ -n "$link" ] || continue
  target="${link#](}"
  target="${target%)}"
  case "$target" in
    http://*|https://*) continue ;;
  esac
  if ! printf '%s\n' "$target" | grep -Eq '^MAPCODE-[a-z0-9]+(-[a-z0-9]+)*\.md$'; then
    echo "领域包必须扁平命名为 MAPCODE-<小写领域>.md：$target" >&2
    missing=1
  elif [ ! -f "$MAP_DIR/$target" ]; then
    echo "上下文包不存在：$target" >&2
    missing=1
  fi
done <<< "$links"

if [ "$missing" -ne 0 ]; then
  exit 1
fi

echo "任务路由索引和上下文包链接校验通过。"
