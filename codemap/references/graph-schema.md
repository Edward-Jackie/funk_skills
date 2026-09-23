# Graph Schema

Graph YAML 是关系结构的唯一事实源；Mermaid 只是生成视图，不允许从 Mermaid 或 Markdown 反向更新 YAML。

当前 renderer 是 Codemap 的窄实现。未来有公共 flow renderer 时，应让 `render_graph` 适配或委托公共实现，不在 Codemap 和正向生码工具中长期维护两套渲染逻辑。

## 文件位置

```text
.map/graphs/<flow>.yaml
.map/views/<flow>.mmd
```

文件名、Graph ID、节点 ID 和边 ID 使用小写英文、数字和连字符。Summary 图最多 12 个节点，detail 图最多 18 个节点。

## 完整结构

```yaml
schema: codemap.graph/v1
id: billing-settlement
title: 结算主链
kind: control                 # control | data | business | state | dependency
level: summary                # summary | detail
parent: null                  # detail 图填写 { graph: <id>, node: <id> }
status: current               # current | needs-review | stale | conflict
verified_at: 2026-09-24
verified_commit: 0123456789abcdef
view: ../views/billing-settlement.mmd

nodes:
  - id: request
    label: 接收结算请求
    kind: entry               # entry | process | decision | state | store | external | terminal
    level: 0                  # 逻辑层级，非渲染坐标
    detail: 校验调用方和基础字段
    sub: null                 # 或相对当前 YAML 的 detail Graph 路径
    refs:
      - path: internal/billing/service.go
        symbol: Settle
    evidence:
      level: source-verified
      note: 已核对入口函数

  - id: accepted
    label: 进入结算
    kind: process
    level: 1
    detail: null
    sub: billing-settlement-detail.yaml
    refs: []
    evidence:
      level: unverified
      note: 细节由 sub Graph 展开

edges:
  - id: request-to-accepted
    from: request
    to: accepted
    label: 校验通过
    condition: validation == passed   # 无条件边显式写 always
    detail: null
    refs:
      - path: internal/billing/service.go
        symbol: Settle
    evidence:
      level: source-verified
      note: 显式分支

cycles: []                    # 每个实际有向环都必须声明
```

## detail 与 sub

- `detail` 保存节点或边的必要补充，没内容时写 `null`，不要塞大段说明。
- `sub` 从 summary 节点指向相对当前文件的 detail YAML。
- detail Graph 必须声明 `parent.graph` 和 `parent.node`，且与引用它的 summary 节点一致。
- Summary 用于导航，detail 用于展开局部复杂链；不要靠提高节点上限避免拆分。

## refs

`refs` 是结构化代码证据，每项必须有仓库相对路径，可选 `symbol`：

```yaml
refs:
  - path: db/queries/billing.sql
    symbol: name:SettleAccount
  - path: config/policy.yaml
    symbol: billing.retry.max_attempts
```

路径必须存在。代码符号由 `check_map.sh` 做定义式匹配；SQL 和配置键做字面匹配。外部系统或人工材料写进 `evidence.note`，不要伪造成代码路径。

## condition

每条边都必须有非空 `condition`：

- 无条件流转：`always`
- 判断分支：写能区分其他出边的条件，例如 `balance >= amount`
- 重试/补偿：写触发条件，例如 `timeout && attempts < max_attempts`

同一 decision 节点的出边条件不得重复。

## evidence

每个节点和边都必须有：

```yaml
evidence:
  level: source-verified
  note: 已核对 switch 分支和状态写入
```

等级使用 `human-confirmed`、`source-verified`、`test-verified`、`runtime-verified`、`unverified` 或 `conflict`。`source-verified` 必须至少有一个 ref；其他等级也必须在 `note` 说明具体来源或验证缺口。

## 环声明

校验器按强连通分量识别有向环。每组环必须显式声明节点集合和存在理由：

```yaml
cycles:
  - id: provider-retry
    nodes: [call-provider, wait-backoff]
    reason: 上游超时后按策略重试
```

未声明环和已经不存在的多余声明都会失败，避免把意外循环画成正常流程。
