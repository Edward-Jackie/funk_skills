#!/usr/bin/env bash
# 校验地图元数据、链接、代码锚点、Git 跟踪状态和核对基线后的源码变化。

set -uo pipefail

STRICT=0
if [ "${1:-}" = "--strict" ]; then
  STRICT=1
  shift
fi

INDEX="${1:-.codex/MAPCODE.md}"
[ -f "$INDEX" ] || { echo "业务地图不存在：$INDEX" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAP_DIR="$(cd "$(dirname "$INDEX")" && pwd)"
INDEX_ABS="$MAP_DIR/$(basename "$INDEX")"
ROOT="$(git -C "$MAP_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mapcode-check.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

errors=0
warnings=0
strict_issues=0

EXPECTED_INDEX="$ROOT/.codex/MAPCODE.md"
if [ "$INDEX_ABS" != "$EXPECTED_INDEX" ]; then
  echo "[错误] L1 必须位于 .codex/MAPCODE.md，当前为：${INDEX_ABS#$ROOT/}" >&2
  errors=$((errors + 1))
fi

while IFS= read -r nested; do
  [ -n "$nested" ] || continue
  echo "[错误] Mapcode 禁止使用子目录：${nested#$ROOT/}" >&2
  errors=$((errors + 1))
done < <(find "$ROOT/.codex" -mindepth 2 -type f -name 'MAPCODE*.md' 2>/dev/null)

"$SCRIPT_DIR/check_context_links.sh" "$INDEX_ABS" || errors=$((errors + 1))

FILES_LIST="$TMP_DIR/files"
printf '%s\n' "$INDEX_ABS" > "$FILES_LIST"
grep -oE '\]\([^ )#]+\.md\)' "$INDEX_ABS" 2>/dev/null \
  | sed -E 's/^\]\((.*)\)$/\1/' \
  | while IFS= read -r rel; do
      [ -f "$MAP_DIR/$rel" ] && printf '%s\n' "$MAP_DIR/$rel"
    done >> "$FILES_LIST"
sort -u "$FILES_LIST" -o "$FILES_LIST"

echo
echo "地图可信度检查："
while IFS= read -r file; do
  rel="${file#$ROOT/}"
  meta="$(sed -n '/<!-- mapcode-meta/,/-->/p' "$file")"
  role="$(printf '%s\n' "$meta" | sed -n 's/^[[:space:]]*map-role:[[:space:]]*//p' | head -1)"
  status="$(printf '%s\n' "$meta" | sed -n 's/^[[:space:]]*status:[[:space:]]*//p' | head -1)"
  commit="$(printf '%s\n' "$meta" | sed -n 's/^[[:space:]]*verified-commit:[[:space:]]*//p' | head -1)"

  if [ -z "$role" ] || [ -z "$status" ] || [ -z "$commit" ]; then
    echo "[错误] $rel 缺少完整 mapcode-meta。"
    errors=$((errors + 1))
    continue
  fi

  base="$(basename "$file")"
  if [ "$role" = "index" ]; then
    if [ "$file" != "$EXPECTED_INDEX" ]; then
      echo "[错误] index 地图只能命名为 .codex/MAPCODE.md：$rel"
      errors=$((errors + 1))
    fi
  elif [ "$role" = "domain" ]; then
    if [ "$(dirname "$file")" != "$ROOT/.codex" ] || ! printf '%s\n' "$base" | grep -Eq '^MAPCODE-[a-z0-9]+(-[a-z0-9]+)*\.md$'; then
      echo "[错误] domain 地图必须扁平命名为 .codex/MAPCODE-<小写领域>.md：$rel"
      errors=$((errors + 1))
    fi
  else
    echo "[错误] $rel 使用未知 map-role：$role"
    errors=$((errors + 1))
  fi

  limit=240
  [ "$role" = "index" ] && limit=160
  lines="$(wc -l < "$file" | tr -d ' ')"
  if [ "$lines" -gt "$limit" ]; then
    echo "[超限] $rel 共 $lines 行，$role 上限为 $limit 行。"
    warnings=$((warnings + 1))
    strict_issues=$((strict_issues + 1))
  fi

  case "$status" in
    current) ;;
    needs-review|stale|conflict)
      echo "[注意] $rel 状态为 $status。"
      warnings=$((warnings + 1))
      strict_issues=$((strict_issues + 1))
      ;;
    *)
      echo "[错误] $rel 使用未知状态：$status"
      errors=$((errors + 1))
      ;;
  esac

  if git -C "$ROOT" cat-file -e "$commit^{commit}" 2>/dev/null; then
    :
  else
    echo "[错误] $rel 的 verified-commit 不存在：$commit"
    errors=$((errors + 1))
  fi

  if git -C "$ROOT" ls-files --error-unmatch "$rel" >/dev/null 2>&1; then
    :
  else
    echo "[注意] $rel 尚未纳入 Git。"
    warnings=$((warnings + 1))
    strict_issues=$((strict_issues + 1))
  fi

  ANCHORS="$TMP_DIR/anchors.$(basename "$file")"
  grep -oE '`[^`]+ -> [^`]+`' "$file" 2>/dev/null \
    | sed -E 's/^`([^`]+) -> ([^`]+)`$/\1\t\2/' \
    | sort -u > "$ANCHORS"

  while IFS="$(printf '\t')" read -r path symbol; do
    [ -n "$path" ] || continue
    case "$path" in
      *'{'*|*'}'*|*'*'*|*' '*|*'/' | *'->'*) continue ;;
    esac
    case "$path" in
      *.go|*.py|*.js|*.jsx|*.ts|*.tsx|*.vue|*.sh|*.sql|*.md) ;;
      *) continue ;;
    esac

    if [ ! -f "$ROOT/$path" ]; then
      echo "[失效] $rel 的锚点文件不存在：$path"
      warnings=$((warnings + 1))
      strict_issues=$((strict_issues + 1))
      continue
    fi

    case "$symbol" in
      *[!A-Za-z0-9_]*) ;;
      *)
        if [ -n "$symbol" ] && ! grep -Fq "$symbol" "$ROOT/$path"; then
          echo "[失效] $rel 的锚点符号不存在：$path -> $symbol"
          warnings=$((warnings + 1))
          strict_issues=$((strict_issues + 1))
        fi
        ;;
    esac

    if [ -n "$commit" ] && git -C "$ROOT" cat-file -e "$commit^{commit}" 2>/dev/null; then
      if ! git -C "$ROOT" diff --quiet "$commit" -- "$path"; then
        echo "[过期] $rel 核对后锚点已变化：$path"
        warnings=$((warnings + 1))
        strict_issues=$((strict_issues + 1))
      fi
    fi
  done < "$ANCHORS"
done < "$FILES_LIST"

echo
echo "检查结果：错误 $errors，注意 $warnings。"
if [ "$errors" -gt 0 ]; then
  exit 1
fi
if [ "$STRICT" -eq 1 ] && [ "$strict_issues" -gt 0 ]; then
  echo "严格模式未通过：存在待复核、过期、冲突或未跟踪地图。" >&2
  exit 1
fi

echo "地图基础校验通过。"
