# 事实、证据与新鲜度规范

地图里的每条关键结论由两个维度组成：**事实类型**说明它是什么，**证据等级**说明凭什么相信。不要把两者混成一个模糊的“高置信度”。

## 事实类型

| 类型 | 含义 | 示例 |
| --- | --- | --- |
| `RULE` | 人工确认的规范性业务要求 | 同一请求只能完成一次资金结算 |
| `IMPL` | 当前代码、配置或数据实现 | `request_id` 被用作幂等键 |
| `VERIFY` | 已执行的测试、运行或观测结果 | 重复结算测试已通过 |
| `RISK` | 未覆盖的故障模式、盲区或违反后果 | Redis 恢复后的幂等状态未验证 |
| `CONFLICT` | 两个来源不能同时成立 | 规则要求代理隔离，但缓存键没有代理维度 |

## 证据等级

| 标签 | 使用条件 | 允许的动作 |
| --- | --- | --- |
| `human-confirmed` | 负责人明确确认，且附会议、工单、需求或事故结论来源 | 只能与 `RULE` 配对，作为业务要求引用 |
| `source-verified` | 已核对显式调用、分支、状态写入、SQL 或配置 | 可作为当前实现事实 |
| `test-verified` | 测试已实际运行、通过且覆盖该结论 | 可作为测试覆盖事实 |
| `runtime-verified` | 已在真实依赖或目标环境验证 | 可作为实际运行事实 |
| `unverified` | 证据不足，只有命名、结构或经验推断 | 只能当线索，动手前必须核对 |
| `conflict` | 规范、源码、测试、数据库或运行结果互相矛盾 | 不得择一采信，必须进入冲突台账 |

推荐写法：

```markdown
- [RULE][human-confirmed] 同一请求只能完成一次资金结算。证据：PAY-142 事故复盘。
- [IMPL][source-verified] `billing/service.go -> Settle` 使用 `request_id` 执行幂等写入。
- [VERIFY][test-verified] `billing/service_test.go -> TestSettleIdempotent` 已运行并覆盖重复请求。
- [RISK][unverified] Redis 故障恢复后的幂等状态尚未在目标环境验证。
```

硬约束：

1. `human-confirmed` 不能从源码推断；没有人工来源就不是业务要求。
2. 测试文件存在不等于 `test-verified`，必须实际运行并覆盖该结论。
3. 阅读源码不能替代 `runtime-verified`。
4. 从命名推断出的调用关系一律 `unverified`。

## 元数据

每个地图文件在标题后保存：

```markdown
<!-- codemap-meta
map-role: index
map-mode: navigation
status: current
verified-at: 2026-09-24
verified-commit: 0123456789abcdef
-->
```

- `map-role`：`index` 或 `domain`。
- `map-mode`：`navigation` 或 `business`。业务模式包含导航内容，并满足高风险业务模板。
- `status`：`current`、`needs-review`、`stale` 或 `conflict`。
- `verified-at`：最后核对日期，格式 `YYYY-MM-DD`。
- `verified-commit`：实际存在的 Git commit。

`current` 只说明已基于该提交核对，不自动提升任何条目的证据等级。其他状态只能作为线索。

## 锚点

统一写成反引号包裹的 `文件路径 -> 符号/SQL/配置键`：

```markdown
`backend/identity/service.go -> AuthenticateSession`
`db/queries/billing.sql -> name:SettleAccount`
`config/policy.yaml -> billing.retry.max_attempts`
```

不保存行号。行号是查询结果，使用 `scripts/where.sh <文件> <符号>` 现算。

外部系统、数据库现状或人工材料不是代码锚点，直接写清来源，不伪装成可自动校验的路径。

## 新鲜度

校验器按每个地图文件自己的 `verified-commit` 比较其锚点文件：

- 文件或符号消失：锚点失效。
- 文件在基线之后发生变化，包括当前工作区变化：相关条目需要重新核对。
- 文件未变化：只说明证据源没变，不证明结论正确。
- 无法机械验证的 SQL 名、配置键或复杂语言符号：报告为降级检查，不得伪装成定义式验证。

只降级受影响条目，不把整张地图判死。

## 冲突

冲突必须显式使用 `[CONFLICT][conflict]`，这样校验器才能可靠计数：

```markdown
### C-001 缓存隔离维度不一致

- [RULE][human-confirmed] 价格缓存必须按上级代理隔离。证据：PRICING-21。
- [IMPL][source-verified] `pricing/cache.go -> priceCacheKey` 只有用户和模型维度。
- [CONFLICT][conflict] 规范与当前缓存键不一致。
- **风险**：绑定变化后可能读取其他代理价格。
- **待决策**：由业务负责人确认规则，或修改实现并补回归测试。
```

存在未解决冲突时，文件 `status` 必须为 `conflict`。校验器同时检查条目标记和文件状态，避免二者漂移。

## 人工保护块

无法从源码恢复的人工规则、事故结论和陷阱放入：

```markdown
<!-- manual: keep -->
[RULE][human-confirmed] 人工确认内容及来源。
<!-- /manual -->
```

增量更新必须逐字保留保护块。不要创建 `.bak`；Git 提供历史和恢复能力。地图必须与对应代码一起进入版本控制。
