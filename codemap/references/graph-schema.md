# Graph Schema

Graph YAML 是关系结构的唯一事实源；Mermaid、Web Explorer 和 AI 上下文包都是派生视图，不允许反向更新 YAML。

新版只接受 `codemap.graph/v2`。旧 Graph 不自动升级；重建时从源码、测试、运行证据和人工确认规则重新取证，避免把旧结构的噪音带入新图。

## 文件位置

```text
.map/graphs/<flow>.yaml
.map/views/<flow>.mmd
```

文件名、Graph ID、节点 ID、边 ID 和泳道 ID 使用小写英文、数字和连字符。Summary 图最多 12 个节点，detail 图最多 18 个节点。

## v2 完整结构

```yaml
schema: codemap.graph/v2
id: billing-settlement
title: 计费结算与分佣
domain: billing
summary: 从请求预扣、实际结算、账单落库到日结分佣
kind: business                 # control | data | business | state | dependency
level: summary                # summary | detail
parent: null                  # detail 图填写 { graph: <id>, node: <id> }
status: current               # current | needs-review | stale | conflict
verified_at: 2026-09-28
verified_commit: 0123456789abcdef
view: ../views/billing-settlement.mmd

layout:
  default: swimlane           # force | swimlane | layered | state
  direction: LR               # LR | TB
  lanes:
    - id: proxy
      label: 实时请求
      order: 1
    - id: storage
      label: 异步账单
      order: 2

nodes:
  - id: preconsume
    label: 预扣余额与额度
    kind: process              # entry | process | decision | state | store | external | terminal
    lane: proxy                # layout 声明 lanes 时必填
    level: 1                   # 逻辑层级，非渲染坐标
    detail: Redis Lua 原子冻结钱包、企业额度与 Key 额度
    tags: [billing, quota, redis]
    sub: null                 # 或相对当前 YAML 的 detail Graph 路径
    context:
      load: required           # required | optional
      markdown:
        - path: .map/CODEMAP-billing.md
          heading: 实时计费主链
    refs:
      - path: proxy/service/billing_service.go
        symbol: func PreConsume
    evidence:
      level: source-verified
      note: 已核对原子预扣入口

edges:
  - id: preconsume-to-provider
    from: preconsume
    to: provider
    kind: sync                 # sync | async | read | write | schedule | compensate | depends-on | transition
    label: 放行请求
    condition: 预扣成功       # 无条件边显式写 always
    detail: null
    refs:
      - path: proxy/controller/proxy_controller.go
        symbol: service.PreConsume
    evidence:
      level: source-verified
      note: 预扣成功后才调用上游

cycles: []                    # 每个实际有向环都必须声明
```

## 布局语义

- `force`：发现全局或局部关系，不表达严格先后。
- `swimlane`：跨角色、服务或存储的业务链；节点按 `lane` 分组，`level` 表示主顺序。
- `layered`：普通调用链或数据流；按 `level` 分层。
- `state`：生命周期和状态迁移；边通常使用 `transition`。
- `direction` 只影响生成视图，不改变业务语义。
- 不保存坐标。布局算法、折叠状态、筛选条件和镜头位置都属于视图状态。

`layout.lanes` 存在时，每个节点必须引用已声明的 `lane`。泳道按 `order` 排序，顺序相同时按声明顺序。

## tags 与 context

- `tags` 用于需求检索，保存稳定业务词，不堆函数名和同义词。
- `context.load: required` 表示命中节点时默认加载对应 Markdown 章节；`optional` 只输出引用，由 AI 判断是否继续读取。
- `context.markdown[].path` 必须是仓库内已存在的相对路径；`heading` 必须是非空章节名。查询器只输出章节引用，不复制整份领域包。

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

路径必须存在。代码符号由 `check_map.sh` 做字面匹配；外部系统或人工材料写进 `evidence.note`，不要伪造成代码路径。

## condition 与边类型

每条边都必须有非空 `condition`：

- 无条件流转：`always`
- 判断分支：写能区分其他出边的条件，例如 `balance >= amount`
- 重试/补偿：写触发条件，例如 `timeout && attempts < max_attempts`

同一 decision 节点的出边条件不得重复。边类型的含义：

- `sync`：同步控制流。
- `async`：消息、队列或后台异步处理。
- `read` / `write`：主要语义是读写存储。
- `schedule`：定时任务触发。
- `compensate`：回滚、退款或人工补偿。
- `depends-on`：结构依赖，不表示调用顺序。
- `transition`：状态迁移。

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
