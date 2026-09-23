# 导航地图模板

创建新地图或重构导航结构时使用。日常只改命中任务的条目，不要每次套完整模板。

## L1：`.map/CODEMAP.md`

```markdown
# <项目名> Code Map

<!-- codemap-meta
map-role: index
map-mode: navigation
status: needs-review
verified-at: <YYYY-MM-DD>
verified-commit: <Git commit>
-->

**权威边界**：地图是带证据的导航缓存；源码、测试、运行环境和人工确认分别决定各自事实。

## 任务路由

| 任务/现象 | 最小读取集 | 条件性追加读取集 | 首个锚点 | 关键规则 | 必须验证 |
| --- | --- | --- | --- | --- | --- |
| <动词、实体、别名或故障现象> | [领域包](CODEMAP-<domain>.md) | <跨域时才读的包或无> | `<路径> -> <符号>` | <前置状态或无> | <测试、日志、状态> |

## 核心领域

| 领域 | 职责 | 关键入口 | 模式 | 明细 |
| --- | --- | --- | --- | --- |
| <领域> | <一句话> | `<路径> -> <符号>` | navigation/business | [明细](CODEMAP-<domain>.md) |

## 症状定位

| 可观测现象 | 首个锚点 | 常见误判 |
| --- | --- | --- |
| <现象> | `<路径> -> <符号>` | <确认过的误区> |

## 全局规则与冲突

- 无；或列出跨领域 `[RULE]` / `[CONFLICT]`，详细证据放到所属 L2。

## 生成视图

- [领域依赖](views/domain-dependencies.mmd)（源：`graphs/domain-dependencies.yaml`）
```

L1 只负责路由。详细调用链、业务说明和历史不要塞进 L1。

## L2：`.map/CODEMAP-<domain>.md`

```markdown
# <领域> Code Map

<!-- codemap-meta
map-role: domain
map-mode: navigation
status: needs-review
verified-at: <YYYY-MM-DD>
verified-commit: <Git commit>
-->

**适用任务/现象**：<关键词、别名、故障表现>

**条件性追加读取**：<仅在什么条件下读取哪个领域包>

## 任务导航

### <真实开发任务>

1. `<路径> -> <符号>`：<为什么从这里开始>
2. `<路径> -> <符号>`：<后续落点>

**前置条件**：<必须先成立的状态或规则>

**陷阱**：<已确认的边界，不写猜测>

**必须验证**：<测试、日志、状态或输出>

## 生成视图

- [控制流](views/<domain>-control.mmd)（源：`graphs/<domain>-control.yaml`）
- [数据流](views/<domain>-data.mmd)（源：`graphs/<domain>-data.yaml`；仅在数据形态变化难以从控制流看出时生成）

关系、条件、refs、证据和盲区只在 Graph YAML 维护；这里不手写 Mermaid。

## 症状定位

| 现象 | 首个锚点 | 常见误判 |
| --- | --- | --- |

## 误导入口

- `<路径> -> <符号>`：<为什么看似相关但不应从这里修改>。

## 已知盲区与冲突

- [RISK][unverified] <缺口及验证路径>。
```

没有内容的可选章节直接省略，不保留空壳。高风险领域把 `map-mode` 改为 `business`，并追加高风险业务模板。
