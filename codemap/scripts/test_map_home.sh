#!/usr/bin/env bash
# 验证 map home 迁移：旧 .map -> ~/.codemap/maps、views 按 domain 分组、校验通过。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/codemap-map-home.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
export CODEMAP_MAP_HOME="$TMP/maps"
export UV_QUIET=1

PROJECT="$TMP/project"
mkdir -p "$PROJECT/src" "$PROJECT/.map/graphs" "$PROJECT/.map/views"
git -C "$PROJECT" init -q
git -C "$PROJECT" config user.email test@example.com
git -C "$PROJECT" config user.name test

cat > "$PROJECT/src/billing.go" <<'EOF'
package billing

func Settle() {}
EOF

cat > "$PROJECT/.map/CODEMAP-billing.md" <<'EOF'
# Billing

<!-- codemap-meta
map-role: domain
map-mode: navigation
status: current
verified-at: 2026-11-04
verified-commit: __COMMIT__
-->

入口：`src/billing.go -> Settle`。
EOF

cat > "$PROJECT/.map/CODEMAP.md" <<'EOF'
# Index

<!-- codemap-meta
map-role: index
map-mode: navigation
status: current
verified-at: 2026-11-04
verified-commit: __COMMIT__
-->

## 任务路由

| 任务 | 读取 |
| --- | --- |
| 结算 | [Billing](CODEMAP-billing.md) |

## 核心领域

- Billing：[视图](views/billing-settlement.mmd)
EOF

cat > "$PROJECT/.map/graphs/billing-settlement.yaml" <<'EOF'
schema: codemap.graph/v2
id: billing-settlement
title: 结算控制流
domain: billing
summary: fixture 结算控制流
kind: control
level: summary
parent: null
status: current
verified_at: 2026-11-04
verified_commit: __COMMIT__
view: ../views/billing-settlement.mmd
layout:
  default: layered
  direction: TB
  lanes: []
nodes:
  - id: request
    label: 接收请求
    kind: entry
    tags: []
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
    tags: []
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
    kind: sync
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

git -C "$PROJECT" add .map src
git -C "$PROJECT" commit -qm init
COMMIT="$(git -C "$PROJECT" rev-parse HEAD)"
sed -i.bak "s/__COMMIT__/$COMMIT/g" "$PROJECT/.map/CODEMAP.md" "$PROJECT/.map/CODEMAP-billing.md" "$PROJECT/.map/graphs/billing-settlement.yaml"
rm -f "$PROJECT/.map/CODEMAP.md.bak" "$PROJECT/.map/CODEMAP-billing.md.bak" "$PROJECT/.map/graphs/billing-settlement.yaml.bak"
"$SCRIPT_DIR/render_graph" "$PROJECT/.map/graphs/billing-settlement.yaml" >/dev/null
git -C "$PROJECT" add .map
git -C "$PROJECT" commit -qm map

"$SCRIPT_DIR/migrate_maps" --root "$PROJECT" >/dev/null
MAP_DIR="$CODEMAP_MAP_HOME/project/main"
[ -f "$MAP_DIR/CODEMAP.md" ]
[ -f "$MAP_DIR/graphs/billing-settlement.yaml" ]
[ -f "$MAP_DIR/views/billing/billing-settlement.mmd" ]
[ -f "$CODEMAP_MAP_HOME/project/repo.json" ]
grep -q "view: ../views/billing/billing-settlement.mmd" "$MAP_DIR/graphs/billing-settlement.yaml"
grep -q "(views/billing/billing-settlement.mmd)" "$MAP_DIR/CODEMAP.md"

"$SCRIPT_DIR/check_map.sh" --root "$PROJECT" --age >/dev/null

"$SCRIPT_DIR/migrate_maps" --root "$PROJECT" --remove-legacy >/dev/null
[ ! -d "$PROJECT/.map" ]
"$SCRIPT_DIR/check_map.sh" --root "$PROJECT" --age >/dev/null

echo "map_home tests passed"
