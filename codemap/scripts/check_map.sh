#!/usr/bin/env bash
# check_map.sh — CODEMAP 的确定性校验器。
#
# Usage:
#   scripts/check_map.sh [--strict] [.claude/CODEMAP.md]
#
# 普通模式检查：元数据完整性、文件命名、锚点失效、条目级过期、冲突计数。
# --strict 模式额外把「过期 / 冲突 / 待复核 / 未纳入 Git」判为失败，可直接用于 CI。
#
# 本脚本不接受人的主观判断，只做可机械判定的检查。它是 Step 8 自查的替代品：
# 与其让模型「记得抽查」，不如让一条命令给出答案。

set -uo pipefail

STRICT=0
if [ "${1:-}" = "--strict" ]; then
  STRICT=1
  shift
fi

INDEX="${1:-.claude/CODEMAP.md}"
[ -f "$INDEX" ] || { echo "CODEMAP 不存在：$INDEX" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAP_DIR="$(cd "$(dirname "$INDEX")" && pwd)"
INDEX_ABS="$MAP_DIR/$(basename "$INDEX")"
ROOT="$(git -C "$MAP_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"

errors=0
warnings=0
strict_issues=0

# 收集本次纳管的地图文件：L1 + 它链接到的所有 CODEMAP-<模块>.md
FILES_LIST="$(mktemp "${TMPDIR:-/tmp}/codemap-files.XXXXXX")"
ANCHORS_ALL="$(mktemp "${TMPDIR:-/tmp}/codemap-anchors.XXXXXX")"
trap 'rm -f "$FILES_LIST" "$ANCHORS_ALL"' EXIT

printf '%s\n' "$INDEX_ABS" > "$FILES_LIST"
grep -oE '\]\([^ )#]+\.md\)' "$INDEX_ABS" 2>/dev/null \
  | sed -E 's/^\]\((.*)\)$/\1/' \
  | while IFS= read -r rel; do
      [ -f "$MAP_DIR/$rel" ] && printf '%s\n' "$MAP_DIR/$rel"
    done >> "$FILES_LIST"
sort -u "$FILES_LIST" -o "$FILES_LIST"

# 锚点必须是「文件路径 -> 符号」，绝不存行号：行号是派生值，代码一移动就静默失效。
# 这里把每个文件里出现过的锚点汇总成 TSV：路径 <TAB> 符号 <TAB> 来源地图文件。
parse_anchors() {
  local file="$1"
  grep -oE '`[^`]+ -> [^`]+`' "$file" 2>/dev/null \
    | sed -E 's/^`([^`]+) -> ([^`]+)`$/\1\t\2/' \
    | while IFS="$(printf '\t')" read -r p s; do
        printf '%s\t%s\t%s\n' "$p" "$s" "${file#$MAP_DIR/}"
      done
}

echo "== CODEMAP 校验 =="
echo "root: ${ROOT}"
echo

while IFS= read -r file; do
  rel="${file#$ROOT/}"
  base="$(basename "$file")"

  # 命名约定：L1 只能是 CODEMAP.md，模块包只能是 CODEMAP-<小写模块>.md，且全部扁平同级。
  if [ "$base" != "CODEMAP.md" ] && ! printf '%s\n' "$base" | grep -Eq '^CODEMAP-[a-z0-9]+(-[a-z0-9]+)*\.md$'; then
    echo "[错误] $rel 命名不合规：模块包必须为 CODEMAP-<小写模块>.md"
    errors=$((errors + 1))
  fi
  if [ "$(dirname "$file")" != "$MAP_DIR" ]; then
    echo "[错误] $rel 未与 .claude/CODEMAP.md 同级，禁止嵌套目录"
    errors=$((errors + 1))
  fi

  # 新鲜度元数据：没有它就无法判断地图是否过期，也就无法安全地信任它。
  meta="$(sed -n '/<!-- codemap-meta/,/-->/p' "$file")"
  status="$(printf '%s\n' "$meta" | sed -n 's/^[[:space:]]*status:[[:space:]]*//p' | head -1)"
  commit="$(printf '%s\n' "$meta" | sed -n 's/^[[:space:]]*verified-commit:[[:space:]]*//p' | head -1)"
  vat="$(printf '%s\n' "$meta" | sed -n 's/^[[:space:]]*verified-at:[[:space:]]*//p' | head -1)"

  if [ -z "$status" ] || [ -z "$commit" ] || [ -z "$vat" ]; then
    echo "[错误] $rel 缺少完整 codemap-meta（需要 status / verified-at / verified-commit）"
    errors=$((errors + 1))
    continue
  fi

  case "$status" in
    current) ;;
    needs-review|stale|conflict)
      echo "[注意] $rel 状态为 $status —— 只能作为线索，不得当作实现事实使用"
      warnings=$((warnings + 1))
      strict_issues=$((strict_issues + 1))
      ;;
    *)
      echo "[错误] $rel 使用未知 status：${status}（应为 current / needs-review / stale / conflict）"
      errors=$((errors + 1))
      ;;
  esac

  if ! git -C "$ROOT" cat-file -e "$commit^{commit}" 2>/dev/null; then
    echo "[错误] $rel 的 verified-commit 在仓库中不存在：$commit"
    errors=$((errors + 1))
    commit=""
  fi

  if ! git -C "$ROOT" ls-files --error-unmatch "$rel" >/dev/null 2>&1; then
    echo "[注意] $rel 尚未纳入 Git —— 地图必须随业务代码一起评审和回滚"
    warnings=$((warnings + 1))
    strict_issues=$((strict_issues + 1))
  fi

  parse_anchors "$file" >> "$ANCHORS_ALL"

  # 冲突台账计数：冲突条目是要被看见的，静默取代码实现是这份地图最坏的行为。
  nconflict="$(grep -cE '\|\s*`?conflict`?\s*\|' "$file" 2>/dev/null || true)"
  nconflict="${nconflict:-0}"
  if [ "$nconflict" -gt 0 ]; then
    echo "[冲突] $rel 有 $nconflict 条冲突记录未决策"
    warnings=$((warnings + 1))
  fi
done < "$FILES_LIST"

echo
echo "== 锚点与过期 =="

if [ ! -s "$ANCHORS_ALL" ]; then
  echo "（未发现任何 '文件路径 -> 符号' 锚点）"
else
  sort -u "$ANCHORS_ALL" -o "$ANCHORS_ALL"

  # 先过一遍锚点，剔除占位符、确认文件与符号真实存在。
  # 同一对「文件 -> 符号」可能在多个段落重复出现，此处去重，避免同一个结论报多遍。
  VALID="$(mktemp "${TMPDIR:-/tmp}/codemap-valid.XXXXXX")"
  trap 'rm -f "$FILES_LIST" "$ANCHORS_ALL" "$VALID"' EXIT

  nfiles=0
  while IFS="$(printf '\t')" read -r path symbol src; do
    [ -n "$path" ] || continue

    # 跳过明显是占位符 / 简写而非真实路径的锚点。
    case "$path" in
      *'{'*|*'}'*|*'*'*|*' '*|*'<'*|*'>'*) continue ;;
      *'->'*|*/) continue ;;
    esac
    case "$path" in
      *.go|*.py|*.js|*.jsx|*.ts|*.tsx|*.vue|*.java|*.sh|*.sql|*.yaml|*.yml|*.json) ;;
      *) continue ;;
    esac

    if [ ! -f "$ROOT/$path" ]; then
      echo "[失效] $src 引用的文件不存在：$path"
      warnings=$((warnings + 1))
      strict_issues=$((strict_issues + 1))
      continue
    fi

    # 符号必须实际存在，且必须是「定义式」匹配而不是随便一次提及 —— 防止从命名推断出假调用。
    # where.sh 找不到定义时会退化为列出全部出现位置，以 "(no definition match" 开头；
    # 真正命中定义时输出是纯粹的 "<行号>:<源码>" 列表，据此区分两者。
    if [ -n "$symbol" ] && printf '%s\n' "$symbol" | grep -Eq '^[A-Za-z_][A-Za-z0-9_.]*$'; then
      hits="$("$SCRIPT_DIR/where.sh" "$ROOT/$path" "$symbol" 2>/dev/null \
        | awk '/^\(no definition match/ { next } /^[0-9]+:/ { print }')"
      if [ -z "$hits" ]; then
        if grep -qF "$symbol" "$ROOT/$path" 2>/dev/null; then
          echo "[降级] $src 的符号仅在文件中出现、未找到定义式匹配：$path -> $symbol"
        else
          echo "[失效] $src 引用的符号不存在：$path -> $symbol"
        fi
        warnings=$((warnings + 1))
        strict_issues=$((strict_issues + 1))
      fi
    fi

    printf '%s\t%s\t%s\n' "$path" "$symbol" "$src" >> "$VALID"
    nfiles=$((nfiles + 1))
  done < "$ANCHORS_ALL"

  # 再按「文件」聚合判断过期：一个文件变了，就一次性列出它名下所有待重核的锚点。
  # 半个文件过期和整个文件过期，要采取的动作完全不同，所以这里只报受影响的部分。
  echo
  nstale_files=0
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    changed=0
    ncommits=0
    # 该文件名下每个锚点各自带着「它所在地图文件」的 verified-commit，逐个比对。
    while IFS="$(printf '\t')" read -r _p _s src; do
      [ -n "$src" ] || continue
      vcommit="$(sed -n '/<!-- codemap-meta/,/-->/p' "$MAP_DIR/$src" \
        | sed -n 's/^[[:space:]]*verified-commit:[[:space:]]*//p' | head -1)"
      [ -n "$vcommit" ] || continue
      git -C "$ROOT" cat-file -e "$vcommit^{commit}" 2>/dev/null || continue
      if ! git -C "$ROOT" diff --quiet "$vcommit" -- "$path" 2>/dev/null; then
        changed=1
        ncommits="$(git -C "$ROOT" rev-list --count "$vcommit"..HEAD -- "$path" 2>/dev/null || echo '?')"
        break
      fi
    done < <(awk -F'\t' -v p="$path" '$1==p { print }' "$VALID")

    if [ "$changed" -eq 1 ]; then
      echo "[过期] $path 自核对后已变化（$ncommits 次提交），以下锚点需重新核对："
      awk -F'\t' -v p="$path" '$1==p { printf "         - %s\n", $2 }' "$VALID" | sort -u
      nstale_files=$((nstale_files + 1))
      warnings=$((warnings + 1))
      strict_issues=$((strict_issues + 1))
    fi
  done < <(cut -f1 "$VALID" | sort -u)

  echo
  echo "共校验 $nfiles 条锚点，涉及 $(cut -f1 "$VALID" | sort -u | grep -c .) 个文件；其中 $nstale_files 个文件自核对后发生过变化。"
  if [ "$nstale_files" -gt 0 ]; then
    echo "只需重新核对上面列出的锚点，其余条目仍可继续使用。"
  fi
fi

# 尺寸体检：地图每次会话都会被加载，薄是硬指标。
echo
echo "== 尺寸 =="
while IFS= read -r file; do
  rel="${file#$ROOT/}"
  n="$(wc -l < "$file" | tr -d ' ')"
  limit=200
  [ "$(basename "$file")" = "CODEMAP.md" ] && limit=120
  if [ "$n" -gt "$limit" ]; then
    echo "[超限] $rel 共 $n 行（上限 ${limit}）—— 拆出 CODEMAP-<模块>.md，人工保护块原样保留"
    warnings=$((warnings + 1))
  else
    echo "[正常] $rel 共 $n 行"
  fi
done < "$FILES_LIST"

echo
echo "== 结论：错误 ${errors}，注意 ${warnings} =="
if [ "$errors" -gt 0 ]; then
  exit 1
fi
if [ "$STRICT" -eq 1 ] && [ "$strict_issues" -gt 0 ]; then
  echo "严格模式未通过：存在失效锚点、过期条目、冲突记录、待复核状态或未纳入 Git 的地图。" >&2
  exit 1
fi

echo "CODEMAP 基础校验通过。"
