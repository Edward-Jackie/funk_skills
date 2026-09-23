#!/usr/bin/env bash
# Minimal behavioral checks for check_map.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHECK="$SCRIPT_DIR/check_map.sh"
GRAPH_CHECK="$SCRIPT_DIR/check_graph"
RENDER="$SCRIPT_DIR/render_graph"
FIXTURE="$(mktemp -d "${TMPDIR:-/tmp}/codemap-test.XXXXXX")"
trap 'rm -rf "$FIXTURE"' EXIT

git -C "$FIXTURE" init -q
git -C "$FIXTURE" config user.name codemap-test
git -C "$FIXTURE" config user.email codemap@example.invalid
mkdir -p "$FIXTURE/src" "$FIXTURE/.map/graphs" "$FIXTURE/.map/views"

cat > "$FIXTURE/src/billing.go" <<'EOF'
package billing

func Settle() {}
EOF

git -C "$FIXTURE" add src/billing.go
git -C "$FIXTURE" commit -qm 'add source'
base="$(git -C "$FIXTURE" rev-parse HEAD)"

cat > "$FIXTURE/.map/CODEMAP.md" <<EOF
# Fixture Code Map

<!-- codemap-meta
map-role: index
map-mode: navigation
status: current
verified-at: 2026-09-24
verified-commit: $base
-->

## 任务路由

| 任务/现象 | 最小读取集 | 条件性追加读取集 | 首个锚点 | 关键规则 | 必须验证 |
| --- | --- | --- | --- | --- | --- |
| 结算 | [billing](CODEMAP-billing.md) | 无 | \`src/billing.go -> Settle\` | 无 | 单测 |

## 核心领域

| 领域 | 职责 | 关键入口 | 模式 | 明细 |
| --- | --- | --- | --- | --- |
| billing | 结算 | \`src/billing.go -> Settle\` | navigation | [billing](CODEMAP-billing.md) |
EOF

cat > "$FIXTURE/.map/CODEMAP-billing.md" <<EOF
# Billing

<!-- codemap-meta
map-role: domain
map-mode: navigation
status: current
verified-at: 2026-09-24
verified-commit: $base
-->

## 任务导航

- [IMPL][source-verified] \`src/billing.go -> Settle\` 是结算入口。

## 生成视图

- [结算控制流](views/billing-settlement.mmd)（源：\`graphs/billing-settlement.yaml\`）
EOF

cat > "$FIXTURE/.map/graphs/billing-settlement.yaml" <<EOF
schema: codemap.graph/v1
id: billing-settlement
title: 结算控制流
kind: control
level: summary
parent: null
status: current
verified_at: 2026-09-24
verified_commit: $base
view: ../views/billing-settlement.mmd
nodes:
  - id: request
    label: 接收请求
    kind: entry
    level: 0
    detail: null
    sub: null
    refs:
      - path: src/billing.go
        symbol: Settle
    evidence:
      level: source-verified
      note: 已核对入口
  - id: settled
    label: 完成结算
    kind: terminal
    level: 1
    detail: null
    sub: null
    refs:
      - path: src/billing.go
        symbol: Settle
    evidence:
      level: source-verified
      note: fixture 终点
edges:
  - id: request-to-settled
    from: request
    to: settled
    label: 执行结算
    condition: always
    detail: null
    refs:
      - path: src/billing.go
        symbol: Settle
    evidence:
      level: source-verified
      note: fixture 显式流转
cycles: []
EOF

(cd "$FIXTURE" && "$RENDER" .map/graphs/billing-settlement.yaml >/dev/null)

git -C "$FIXTURE" add .map
git -C "$FIXTURE" commit -qm 'add maps'

(cd "$FIXTURE" && "$CHECK" --strict .map/CODEMAP.md)

expect_graph_failure() {
  local expected="$1"
  local output
  local status
  set +e
  output="$(cd "$FIXTURE" && "$GRAPH_CHECK" --skip-view-check .map/graphs 2>&1)"
  status=$?
  set -e
  if [ "$status" -eq 0 ] || ! printf '%s\n' "$output" | grep -Fq "$expected"; then
    echo "expected Graph failure containing: $expected" >&2
    printf '%s\n' "$output" >&2
    exit 1
  fi
  git -C "$FIXTURE" restore .map/graphs/billing-settlement.yaml
}

sed -i.bak 's/id: request-to-settled/id: request/' "$FIXTURE/.map/graphs/billing-settlement.yaml"
rm "$FIXTURE/.map/graphs/billing-settlement.yaml.bak"
expect_graph_failure "ID 重复"

sed -i.bak 's/to: settled/to: missing/' "$FIXTURE/.map/graphs/billing-settlement.yaml"
rm "$FIXTURE/.map/graphs/billing-settlement.yaml.bak"
expect_graph_failure "to 悬空"

sed -i.bak '/    condition: always/d' "$FIXTURE/.map/graphs/billing-settlement.yaml"
rm "$FIXTURE/.map/graphs/billing-settlement.yaml.bak"
expect_graph_failure "缺少 condition"

sed -i.bak 's#path: src/billing.go#path: src/missing.go#g' "$FIXTURE/.map/graphs/billing-settlement.yaml"
rm "$FIXTURE/.map/graphs/billing-settlement.yaml.bak"
expect_graph_failure "path 不存在"

sed -i.bak 's/    sub: null/    sub: missing.yaml/g' "$FIXTURE/.map/graphs/billing-settlement.yaml"
rm "$FIXTURE/.map/graphs/billing-settlement.yaml.bak"
expect_graph_failure "sub 文件不存在"

perl -0pi -e 's/cycles: \[\]/  - id: settled-to-request\n    from: settled\n    to: request\n    label: retry\n    condition: retry\n    detail: null\n    refs:\n      - path: src\/billing.go\n        symbol: Settle\n    evidence:\n      level: source-verified\n      note: fixture retry\ncycles: []/' "$FIXTURE/.map/graphs/billing-settlement.yaml"
expect_graph_failure "存在未声明环"

printf '\n- [CONFLICT][conflict] fixture conflict\n' >> "$FIXTURE/.map/CODEMAP-billing.md"
if (cd "$FIXTURE" && "$CHECK" --strict .map/CODEMAP.md >/dev/null 2>&1); then
  echo "expected conflict mismatch to fail" >&2
  exit 1
fi
git -C "$FIXTURE" restore .map/CODEMAP-billing.md

sed -i.bak 's/CODEMAP-billing.md/CODEMAP-missing.md/g' "$FIXTURE/.map/CODEMAP.md"
rm "$FIXTURE/.map/CODEMAP.md.bak"
if (cd "$FIXTURE" && "$CHECK" .map/CODEMAP.md >/dev/null 2>&1); then
  echo "expected missing link to fail" >&2
  exit 1
fi
git -C "$FIXTURE" restore .map/CODEMAP.md

printf '\nfunc Refund() {}\n' >> "$FIXTURE/src/billing.go"
if (cd "$FIXTURE" && "$CHECK" --strict .map/CODEMAP.md >/dev/null 2>&1); then
  echo "expected stale source to fail" >&2
  exit 1
fi

echo "check_map.sh tests passed"
