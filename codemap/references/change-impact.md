# 代码改动影响分析

Codemap 同时支持“需求找代码”和“代码改动反查业务”。反查只回答已被 Graph 证据覆盖的影响，不把未命中解释为没有风险。

## 使用时机

- 开发中需要确认当前改动触及哪些业务链。
- 提交前检查是否遗漏下游、补偿、异步或存储节点。
- 需求 Overlay 准备收口时，对比计划影响与实际 Diff。
- 评审已有分支时，从代码文件快速进入业务上下文。

普通局部改动且一次源码搜索即可判断时不必运行。

## 命令

检查暂存区、工作区和未跟踪文件：

```bash
scripts/impact_diff .map/graphs
```

包含某个基线到当前 `HEAD` 的提交差异：

```bash
scripts/impact_diff .map/graphs --base origin/main --depth 2
```

只分析明确文件：

```bash
scripts/impact_diff .map/graphs \
  --path proxy/service/billing_service.go \
  --path api/job/commission_daily.go
```

通过 `--out .map/context/change-impact.md` 保存临时结果。该文件不是真源，默认不提交。

## 命中规则

1. 变更路径与节点或边的 `refs[].path` 完全一致时记为直接命中。
2. 直接命中的边将两端节点加入影响种子。
3. 从种子沿有向边向下游扩展有限深度；默认两跳，不做无限传播。
4. 输出受影响节点的 required/optional Markdown 章节和源码锚点。
5. 没有任何 Graph ref 命中的变更文件必须进入“未覆盖文件”，提醒回到 L1 或源码探索。

不根据文件名相似度猜测业务归属，也不把同目录文件自动视为同一影响域。

## 结果解释

- **直接命中**：当前 Graph 明确引用了变更文件，仍需核对具体 diff 是否真的改变对应行为。
- **下游影响**：按 Graph 方向推导的检查范围，不表示一定发生行为变化。
- **未覆盖文件**：地图没有证据，可能是普通实现细节，也可能是覆盖缺口；必须人工判断。
- **非 current Graph**：只能作为定位线索，先重新验证相关节点和边。

需求完成时比较 Overlay、Diff 结果和最终 Graph：计划但未命中的项需要确认是否漏做；Diff 命中但 Overlay 未声明的项需要确认是否出现范围外影响；只有源码和验证都完成的事实才能提升进基础 Graph。
