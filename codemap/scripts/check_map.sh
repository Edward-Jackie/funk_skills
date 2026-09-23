#!/usr/bin/env bash
# Validate the CODEMAP contract: structure, metadata, links, evidence, anchors,
# freshness, conflicts, Git tracking, and size.

set -uo pipefail

STRICT=0
if [ "${1:-}" = "--strict" ]; then
  STRICT=1
  shift
fi

INDEX="${1:-.map/CODEMAP.md}"
[ -f "$INDEX" ] || { echo "CODEMAP 不存在：$INDEX" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
MAP_DIR="$(cd "$(dirname "$INDEX")" && pwd -P)"
INDEX_ABS="$MAP_DIR/$(basename "$INDEX")"
ROOT_RAW="$(git -C "$MAP_DIR" rev-parse --show-toplevel 2>/dev/null || pwd -P)"
ROOT="$(cd "$ROOT_RAW" && pwd -P)"
EXPECTED_INDEX="$ROOT/.map/CODEMAP.md"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/codemap-check.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

FILES_LIST="$TMP_DIR/files"
ANCHORS="$TMP_DIR/anchors"
GRAPH_REFS="$TMP_DIR/graph-refs"
GRAPH_VIEWS="$TMP_DIR/graph-views"
: > "$FILES_LIST"
: > "$ANCHORS"
: > "$GRAPH_REFS"
: > "$GRAPH_VIEWS"

errors=0
warnings=0
strict_issues=0

error() {
  echo "[错误] $*"
  errors=$((errors + 1))
}

warn() {
  echo "[注意] $*"
  warnings=$((warnings + 1))
}

strict_warn() {
  warn "$*"
  strict_issues=$((strict_issues + 1))
}

meta_value() {
  local file="$1"
  local key="$2"
  sed -n '/<!-- codemap-meta/,/-->/p' "$file" \
    | sed -n "s/^[[:space:]]*${key}:[[:space:]]*//p" \
    | head -1
}

echo "== CODEMAP 校验 =="
echo "root: $ROOT"
echo

if [ "$INDEX_ABS" != "$EXPECTED_INDEX" ]; then
  error "L1 必须位于 .map/CODEMAP.md，当前为：${INDEX_ABS#$ROOT/}"
fi

while IFS= read -r legacy; do
  [ -n "$legacy" ] || continue
  error "发现旧地图，必须迁移到 .map 后删除旧文件：${legacy#$ROOT/}"
done < <(
  find "$ROOT/.claude" -type f \( -name 'CODEMAP*.md' -o -name 'MAPCODE*.md' \) 2>/dev/null
  find "$ROOT/.codex" -type f \( -name 'CODEMAP*.md' -o -name 'MAPCODE*.md' \) 2>/dev/null
)

for heading in "任务路由" "核心领域"; do
  grep -Fq "## $heading" "$INDEX_ABS" || error "L1 缺少章节：$heading"
done

while IFS= read -r nested; do
  [ -n "$nested" ] || continue
  error "CODEMAP 文件禁止嵌套：${nested#$ROOT/}"
done < <(find "$ROOT/.map" -mindepth 2 -type f -name 'CODEMAP*.md' 2>/dev/null)

# Check every CODEMAP-looking link, including malformed and missing targets.
while IFS= read -r target; do
  [ -n "$target" ] || continue
  if ! printf '%s\n' "$target" | grep -Eq '^CODEMAP-[a-z0-9]+(-[a-z0-9]+)*\.md$'; then
    error "领域包链接必须为扁平的 CODEMAP-<小写领域>.md：$target"
  elif [ ! -f "$MAP_DIR/$target" ]; then
    error "领域包不存在：$target"
  fi
done < <(grep -oE '\]\([^ )#]*CODEMAP[^ )#]*\.md\)' "$INDEX_ABS" 2>/dev/null \
  | sed -E 's/^\]\((.*)\)$/\1/' || true)

find "$MAP_DIR" -maxdepth 1 -type f -name 'CODEMAP*.md' -print | sort > "$FILES_LIST"

# Every L2 is routed from L1; otherwise it becomes undiscoverable stale context.
while IFS= read -r file; do
  [ "$file" = "$INDEX_ABS" ] && continue
  base="$(basename "$file")"
  grep -Fq "($base)" "$INDEX_ABS" || strict_warn "$base 未被 L1 路由引用"
done < "$FILES_LIST"

echo "== 结构与证据 =="
while IFS= read -r file; do
  rel="${file#$ROOT/}"
  base="$(basename "$file")"
  role="$(meta_value "$file" map-role)"
  mode="$(meta_value "$file" map-mode)"
  status="$(meta_value "$file" status)"
  verified_at="$(meta_value "$file" verified-at)"
  commit="$(meta_value "$file" verified-commit)"

  if [ "$base" = "CODEMAP.md" ]; then
    [ "$role" = "index" ] || error "$rel 的 map-role 必须为 index"
  elif printf '%s\n' "$base" | grep -Eq '^CODEMAP-[a-z0-9]+(-[a-z0-9]+)*\.md$'; then
    [ "$role" = "domain" ] || error "$rel 的 map-role 必须为 domain"
  else
    error "$rel 命名不合规"
  fi

  case "$mode" in
    navigation|business) ;;
    *) error "$rel 的 map-mode 必须为 navigation 或 business" ;;
  esac

  case "$status" in
    current) ;;
    needs-review|stale|conflict) strict_warn "${rel} 状态为 ${status}，只能作为线索" ;;
    *) error "$rel 的 status 必须为 current、needs-review、stale 或 conflict" ;;
  esac

  if ! printf '%s\n' "$verified_at" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
    error "$rel 的 verified-at 必须为 YYYY-MM-DD"
  fi

  if [ -z "$commit" ] || ! git -C "$ROOT" cat-file -e "$commit^{commit}" 2>/dev/null; then
    error "$rel 的 verified-commit 不存在：${commit:-<空>}"
    commit=""
  fi

  if ! git -C "$ROOT" ls-files --error-unmatch "$rel" >/dev/null 2>&1; then
    strict_warn "$rel 尚未纳入 Git"
  fi

  if grep -Fq '```mermaid' "$file"; then
    error "$rel 包含手写 Mermaid；关系图必须来自 Graph YAML 并只链接生成视图"
  fi

  if [ "$mode" = "business" ]; then
    for heading in "业务契约" "状态与真相来源" "关键规则与不变量" "副作用、失败与补偿" "代码、测试与观测证据"; do
      grep -Fq "## $heading" "$file" || error "$rel 为 business 模式但缺少章节：$heading"
    done
  fi

  bad_rules="$(grep -nE '^[[:space:]|*-]*\[RULE\]' "$file" 2>/dev/null | grep -vF '[RULE][human-confirmed]' || true)"
  [ -z "$bad_rules" ] || error "$rel 存在未使用 [RULE][human-confirmed] 的规则条目"

  bad_human="$(grep -nE '^[[:space:]|*-]*\[[A-Z]+\]\[human-confirmed\]' "$file" 2>/dev/null | grep -vF '[RULE][human-confirmed]' || true)"
  [ -z "$bad_human" ] || error "$rel 将 human-confirmed 用在了 RULE 之外"

  conflicts="$(grep -cF '[CONFLICT][conflict]' "$file" 2>/dev/null || true)"
  conflicts="${conflicts:-0}"
  if [ "$conflicts" -gt 0 ]; then
    strict_issues=$((strict_issues + 1))
    warn "$rel 有 $conflicts 条未决冲突"
    [ "$status" = "conflict" ] || error "$rel 有冲突条目，但 status 不是 conflict"
  elif [ "$status" = "conflict" ]; then
    error "$rel 的 status 为 conflict，但没有 [CONFLICT][conflict] 条目"
  fi

  grep -oE '`[^`]+ -> [^`]+`' "$file" 2>/dev/null \
    | sed -E 's/^`([^`]+) -> ([^`]+)`$/\1\t\2/' \
    | while IFS="$(printf '\t')" read -r path symbol; do
        printf '%s\t%s\t%s\t%s\n' "$path" "$symbol" "$rel" "$commit"
      done >> "$ANCHORS"

  lines="$(wc -l < "$file" | tr -d ' ')"
  limit=240
  [ "$role" = "index" ] && limit=120
  if [ "$lines" -gt "$limit" ]; then
    strict_warn "$rel 共 $lines 行，超过 $role 上限 $limit"
  fi
done < "$FILES_LIST"

echo
echo "== Graph =="
GRAPH_DIR="$MAP_DIR/graphs"
if [ ! -d "$GRAPH_DIR" ]; then
  error "缺少 .map/graphs；关系结构必须使用 Graph YAML"
else
  graph_args=(--root "$ROOT" --refs-out "$GRAPH_REFS" --views-out "$GRAPH_VIEWS")
  [ "$STRICT" -eq 1 ] && graph_args=(--strict "${graph_args[@]}")
  if ! "$SCRIPT_DIR/check_graph" "${graph_args[@]}" "$GRAPH_DIR"; then
    error "Graph 校验未通过"
  fi
  cat "$GRAPH_REFS" >> "$ANCHORS"

  while IFS="$(printf '\t')" read -r graph view; do
    [ -n "$view" ] || continue
    linked=0
    while IFS= read -r map_file; do
      if grep -Fq "($view)" "$map_file"; then
        linked=1
        break
      fi
    done < "$FILES_LIST"
    [ "$linked" -eq 1 ] || error "$graph 的生成视图未被任何 CODEMAP 引用：$view"
  done < "$GRAPH_VIEWS"
fi

echo
echo "== 锚点与新鲜度 =="
sort -u "$ANCHORS" -o "$ANCHORS"
checked=0
stale=0

while IFS="$(printf '\t')" read -r path symbol source commit; do
  [ -n "$path" ] || continue
  case "$path" in
    *'{'*|*'}'*|*'*'*|*' '*|*'<'*|*'>'*|*'->'*|*/) continue ;;
  esac

  checked=$((checked + 1))
  if [ ! -f "$ROOT/$path" ]; then
    strict_warn "$source 的锚点文件不存在：$path"
    continue
  fi

  case "$path" in
    *.sql|*.yaml|*.yml|*.json|*.toml)
      if [ "$symbol" != "-" ]; then
        grep -Fq "$symbol" "$ROOT/$path" 2>/dev/null \
          || strict_warn "$source 的 SQL/配置键未找到：$path -> $symbol"
      fi
      ;;
    *)
      if [ "$symbol" = "-" ]; then
        :
      elif printf '%s\n' "$symbol" | grep -Eq '^[A-Za-z_][A-Za-z0-9_]*$'; then
        hits="$("$SCRIPT_DIR/where.sh" "$ROOT/$path" "$symbol" 2>/dev/null \
          | awk '/^\(no definition match/ { next } /^[0-9]+:/ { print }')"
        if [ -z "$hits" ]; then
          if grep -Fq "$symbol" "$ROOT/$path" 2>/dev/null; then
            strict_warn "$source 的符号只有普通引用、没有定义式匹配：$path -> $symbol"
          else
            strict_warn "$source 的锚点符号不存在：$path -> $symbol"
          fi
        fi
      elif ! grep -Fq "$symbol" "$ROOT/$path" 2>/dev/null; then
        strict_warn "$source 的复杂锚点无法匹配：$path -> $symbol"
      fi
      ;;
  esac

  if [ -n "$commit" ] && ! git -C "$ROOT" diff --quiet "$commit" -- "$path" 2>/dev/null; then
    strict_warn "$source 的证据文件自 $commit 后已变化：$path -> $symbol"
    stale=$((stale + 1))
  fi
done < "$ANCHORS"

[ "$checked" -gt 0 ] || warn "未发现任何可校验锚点"
echo "已检查 ${checked} 条锚点，其中 ${stale} 条需要重新核对。"

echo
echo "== 结论：错误 ${errors}，注意 ${warnings} =="
if [ "${errors}" -gt 0 ]; then
  exit 1
fi
if [ "$STRICT" -eq 1 ] && [ "$strict_issues" -gt 0 ]; then
  echo "严格模式未通过。" >&2
  exit 1
fi

echo "CODEMAP 校验通过。"
