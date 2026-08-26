# Mapcode 证据与新鲜度规范

## 元数据

L1 和每个 L2 文件在标题后保存：

```markdown
<!-- mapcode-meta
map-role: index
status: current
verified-at: 2026-08-25
verified-commit: 0123456789abcdef
-->
```

`map-role` 为 `index` 或 `domain`。`status` 取值：

- `current`：已按 `verified-commit` 核对当前证据。
- `needs-review`：旧地图迁移、证据不足或尚未建立可靠基线。
- `stale`：锚点文件在核对提交后发生变化。
- `conflict`：存在尚未裁决的规则与实现冲突。

新鲜度只是“相关代码是否变化”的信号，不证明业务结论正确。`current` 仍需结合逐条证据标签阅读。

## 逐条事实

使用稳定类型区分业务要求、当前实现和风险：

```markdown
- [RULE][human-confirmed] 同一请求只能完成一次资金结算。
- [IMPL][source-verified] `billing/service.go -> Settle` 使用 request_id 执行幂等脚本。
- [VERIFY][test-verified] `billing/service_test.go -> TestSettleIdempotent` 覆盖重复结算。
- [RISK][unverified] Redis 故障恢复后的幂等状态尚未做真实环境验证。
```

推荐类型：

- `RULE`：规范性业务规则。
- `IMPL`：当前实现事实。
- `VERIFY`：测试、运行或观测证据。
- `RISK`：缺口、盲区或违反后果。
- `CONFLICT`：两个来源不能同时成立。

## 冲突

冲突必须同时呈现两边证据：

```markdown
### C-001 缓存隔离维度不一致

- [RULE][human-confirmed] 实体价格缓存必须按上级代理隔离。
- [IMPL][source-verified] 当前缓存键只有用户和模型维度。
- [CONFLICT][conflict] 数据库查询维度与缓存维度不一致。
- **风险**：用户变更绑定后可能在缓存期读取旧价格。
- **待决策**：修改实现，或由负责人调整业务规则并说明安全前提。
```

没有得到授权时，地图维护不得替用户选择冲突的解决方向。

## 新鲜度判断

校验脚本从 `路径 -> 符号` 锚点提取证据文件，并比较 `verified-commit` 之后的变化：

- 文件或符号不存在：锚点失效。
- 文件在基线后变化：地图可能 `stale`，需要人工核对相关结论。
- 文件未变化：只说明证据源未变化，不提升证据等级。
- 工作区存在相关未提交修改：同样视为可能过期。

通配路径、目录和外部系统证据无法做符号级自动校验，应保留为人工检查项。

## 版本控制

地图与代码一起进入版本控制。业务代码变更影响某领域时，同一主题提交应更新该领域地图，或者明确说明业务事实未变化并刷新核对基线。不要单独维护无审查、无回滚能力的本地事实源。
