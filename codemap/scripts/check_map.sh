#!/usr/bin/env bash
# 校验 CODEMAP 的结构、元数据、链接、证据、锚点、新鲜度、冲突、Git 状态和规模。

set -uo pipefail

STRICT=0
AGE=0
MAP_ROOT=""
ROOT_ARG=""
BRANCH_ARG=""
INDEX_ARG=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --strict)
      STRICT=1
      shift
      ;;
    --age)
      AGE=1
      shift
      ;;
    --root)
      [ "$#" -ge 2 ] || { echo "--root 缺少项目根目录" >&2; exit 2; }
      ROOT_ARG="$2"
      shift 2
      ;;
    --branch)
      [ "$#" -ge 2 ] || { echo "--branch 缺少分支名" >&2; exit 2; }
      BRANCH_ARG="$2"
      shift 2
      ;;
    --map-root)
      [ "$#" -ge 2 ] || { echo "--map-root 缺少目录" >&2; exit 2; }
      MAP_ROOT="$2"
      shift 2
      ;;
    -*)
      echo "未知参数：$1" >&2
      exit 2
      ;;
    *)
      [ -z "$INDEX_ARG" ] || { echo "只能指定一个 CODEMAP 入口" >&2; exit 2; }
      INDEX_ARG="$1"
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"

# 地图可能来自 ~/.codemap/maps 或旧项目内 .map；先确定 MAP_DIR，再从 repo.json 反查项目根。
if [ -n "$ROOT_ARG" ]; then
  ROOT="$(cd "$ROOT_ARG" && pwd -P)"
fi

if [ -n "$INDEX_ARG" ]; then
  MAP_DIR="$(cd "$(dirname "$INDEX_ARG")" && pwd -P)"
elif [ -n "$MAP_ROOT" ]; then
  case "$MAP_ROOT" in
    /*) MAP_DIR="$MAP_ROOT" ;;
    *) MAP_DIR="${ROOT:-$PWD}/$MAP_ROOT" ;;
  esac
  MAP_DIR="$(cd "$MAP_DIR" && pwd -P)"
elif [ -n "$ROOT" ]; then
  resolved="$("$SCRIPT_DIR/map_home.py" resolve --root "$ROOT" ${BRANCH_ARG:+--branch "$BRANCH_ARG"})" \
    || { echo "找不到地图目录：$ROOT" >&2; exit 1; }
  MAP_DIR="$(printf '%s\n' "$resolved" | sed -n 's/^map_dir: //p')"
  [ -n "$MAP_DIR" ] || { echo "无法解析地图目录：$ROOT" >&2; exit 1; }
else
  MAP_DIR="$(cd .map && pwd -P)"
fi

if [ -z "${ROOT:-}" ]; then
  ROOT="$("$SCRIPT_DIR/map_home.py" root --map-root "$MAP_DIR" 2>/dev/null || true)"
fi
if [ -z "${ROOT:-}" ] || [ ! -d "$ROOT" ]; then
  ROOT_RAW="$(git -C "$MAP_DIR" rev-parse --show-toplevel 2>/dev/null || pwd -P)"
  ROOT="$(cd "$ROOT_RAW" && pwd -P)"
fi

INDEX="$MAP_DIR/CODEMAP.md"
[ -f "$INDEX" ] || { echo "CODEMAP 不存在：$INDEX" >&2; exit 1; }
INDEX_ABS="$INDEX"
EXPECTED_INDEX="$INDEX_ABS"
MAP_REPO="$(git -C "$MAP_DIR" rev-parse --show-toplevel 2>/dev/null || true)"

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
  error "L1 必须位于当前地图根的 CODEMAP.md，当前为：${INDEX_ABS#$ROOT/}"
fi

while IFS= read -r legacy; do
  [ -n "$legacy" ] || continue
  error "发现旧地图，必须迁移到 .map 后删除旧文件：${legacy#$ROOT/}"
done < <(
  find "$ROOT/.claude" -type f -name 'CODEMAP*.md' 2>/dev/null
  find "$ROOT/.codex" -type f -name 'CODEMAP*.md' 2>/dev/null
)

for heading in "任务路由" "核心领域"; do
  grep -Fq "## $heading" "$INDEX_ABS" || error "L1 缺少章节：$heading"
done

while IFS= read -r nested; do
  [ -n "$nested" ] || continue
  error "CODEMAP 文件禁止嵌套：${nested#$ROOT/}"
done < <(find "$MAP_DIR" -mindepth 2 -type f -name 'CODEMAP*.md' ! -path "$MAP_DIR/next/*" 2>/dev/null)

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
  rel="${file#$MAP_DIR/}"
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

  # 地图事实现在跟踪在地图仓库里，不再要求进入项目源码仓库。
  if [ -n "$MAP_REPO" ]; then
    map_rel="${file#$MAP_REPO/}"
    if ! git -C "$MAP_REPO" ls-files --error-unmatch "$map_rel" >/dev/null 2>&1; then
      strict_warn "$rel 尚未纳入地图 Git 仓库"
    fi
  elif ! git -C "$ROOT" ls-files --error-unmatch "$rel" >/dev/null 2>&1; then
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
  error "缺少 ${GRAPH_DIR#$ROOT/}；关系结构必须使用 Graph YAML"
else
  graph_args=(--root "$ROOT" --map-root "$MAP_DIR" --refs-out "$GRAPH_REFS" --views-out "$GRAPH_VIEWS")
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
    error "$source 的锚点文件不存在（地图已失效）：$path"
    continue
  fi

  case "$path" in
    *.sql|*.yaml|*.yml|*.json|*.toml)
      if [ "$symbol" != "-" ]; then
        grep -Fq "$symbol" "$ROOT/$path" 2>/dev/null \
          || error "$source 的 SQL/配置键不存在（地图已失效）：$path -> $symbol"
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
            error "$source 的锚点符号不存在（地图已失效）：$path -> $symbol"
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

if [ "$AGE" -eq 1 ]; then
  echo
  if [ -x "$SCRIPT_DIR/freshness" ]; then
    age_output="$(UV_QUIET=1 "$SCRIPT_DIR/freshness" --root "$ROOT" --map-root "$MAP_DIR" 2>&1)"
    age_rc=$?
    printf '%s\n' "$age_output"
    if [ "$age_rc" -ne 0 ]; then
      error "新鲜度检查执行失败"
    else
      age_level="$(printf '%s\n' "$age_output" | sed -n 's/^总体：\([a-z-]*\).*/\1/p' | head -1)"
      case "$age_level" in
        needs-review|stale|conflict)
          warn "建议把相关文件 status 改为 needs-review，复核后同步 verified-commit"
          error "新鲜度未通过（${age_level}）：地图已过期或待复核，请更新锚点与 status 后重跑"
          ;;
        aging)
          warn "地图已进入 aging：基线领先较多，建议尽快复核"
          ;;
      esac
    fi
  else
    warn "缺少 freshness 脚本，无法输出 --age"
  fi
fi

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
