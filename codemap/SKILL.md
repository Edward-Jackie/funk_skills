---
name: codemap
version: "3.0"
description: >
  生成、读取和维护跨 AI 共用的 CODEMAP：把开发任务、故障现象与代码锚点关联起来，并从同一份结构化 Graph 编译成 Archify 质量的可下钻业务图（泳道、分层、跨图检索、侧栏展示条件/证据/源码锚点）、Git Diff 反查和按需 AI 上下文。用户要求梳理代码结构、调用链、改动入口、业务规则、影响范围或可视化时使用；已有地图且在陌生模块反复搜索、做跨域影响分析或高风险改动时按需读取。不要为普通 CRUD 或一次搜索即可定位的局部改动建图。
---

# Codemap 3.0

CODEMAP 是带证据的导航缓存，不替代源码、测试、运行环境或人工确认的业务要求。让下一次冷启动能在两步内从任务或故障现象走到首个可靠代码锚点，并在高风险业务中看见不能破坏的规则。

3.0 的结构：**Codemap 管事实，Archify 管呈现**。`.map/` 的 Markdown 与 Graph 保存可复核的事实；图是由 Graph 单向编译出的派生产物，渲染器是内置的 Archify 分支（`renderers/archify/`，Apache-2.0，改动见 [Archify 集成](references/archify-integration.md)）。原 Explorer 前端已退役。

核心原则：**持久化事实，动态生成视图**。HTML 不手改，Graph 不存坐标，视图不反向成为第二套真相。

首次建设或改版前先读 [改造方向与分层契约](references/product-direction.md)；改渲染链路先读 [Archify 集成](references/archify-integration.md)。

## 使用边界

- 已有地图时，只在缺少上下文、跨域分析或高风险改动时读取 L1，再按路由加载最小 L2；不要把全量地图当前置仪式。
- 只有用户明确要求建图/更新，或当前任务实际改变了地图已记录的行为时才写地图。
- 不记录目录树、完整接口清单、机械的 Controller 到 Service 罗列、无状态 CRUD，或一次源码搜索即可恢复的事实。
- 地图不是阻塞项。状态不是 `current` 时当线索，回源码核对。

## 两种模式

- **导航模式（默认）**：回答「改哪里、调用怎么走、这个现象先查哪」。创建或大改结构时读 [导航地图模板](references/navigation-template.md)。
- **高风险业务模式（按需）**：涉及资金、权限、库存、额度、订单、风控、复杂状态机或多存储/第三方副作用时，追加业务成功定义、状态真相、不变量、幂等、补偿、人工兜底。读 [高风险业务模板](references/business-chain-template.md)。

## 权威与证据

- **规范性事实**：只有 `[RULE][human-confirmed]` 是人工确认的业务要求。
- **描述性事实**：`IMPL`、`VERIFY`、`RISK` 描述当前实现、验证结果和缺口。
- **冲突**：规则和实现不能同时成立时写 `[CONFLICT][conflict]`，保留两边证据，不自行裁决。

写关键结论前读 [事实、证据与新鲜度规范](references/evidence-model.md)。

## 统一产物

```text
.map/CODEMAP.md                  # L1：任务路由、领域摘要、症状定位、全局规则/冲突
.map/CODEMAP-<domain>.md         # L2：领域导航；高风险领域可追加业务链
.map/graphs/<flow>.yaml          # Graph v2：关系层的唯一结构化事实源
.map/views/index.html            # 下钻外壳：导航树、面包屑、跨图检索
.map/views/<flow>.html           # 每张图的 Archify 页面（单独过校验）
.map/views/<flow>.candidate.json # 编译出的 Archify 候选（派生）
.map/views/<flow>.facts.json     # 事实侧车（派生）：condition、证据、锚点、下钻、规则
.map/overlays/<task>.yaml        # 单需求影响覆盖层，默认不并入基础 Graph
.map/context/<task>.md           # 按需求生成的临时 AI 上下文包
```

- L1/L2 扁平同级；名称只用小写英文、数字和连字符。L1 目标不超过 120 行，L2 不超过 240 行。
- `AGENTS.md`、`CLAUDE.md` 等入口只引用同一份 `.map/CODEMAP.md`，不复制正文。
- 旧 `.claude/` 或 `.codex/` 里的 `CODEMAP*` 先读 [迁移规范](references/migration.md)，不得留下两套事实源。
- 基础 Graph 只保存已存在或已确认的事实；未实施需求写入 Overlay，标 `proposal/unverified`。

## 工作流

1. **读项目约束**：读适用的 `AGENTS.md`、`CLAUDE.md`，确认编辑边界。改版预览输出到 `.map/next/`，不与旧 Graph 混读，验证后由用户决定替换。
2. **读最小上下文**：地图存在时先读 L1 的路由、`status`、冲突，再加载命中的最小 L2。
3. **发现真实入口**：从路由、命令、事件、任务、状态写入和测试追踪业务模块，跳过生成代码和依赖。
4. **选择分层**：`scripts/count_sources.sh [项目根]` 取规模提示；源码超过 50、核心领域超过 4、L1 预计超过 120 行时拆 L2。
5. **逐条取证**：锚点用 `路径 -> 符号/SQL/配置键`，不存行号；找不到证据的隐式钩子标 `unverified`。
6. **生成 Graph**：按 [Graph Schema](references/graph-schema.md) 从源码和人工规则重新生成，YAML 是节点、边、泳道、条件、证据的唯一结构化源。Summary 最多 12 个节点，detail 最多 18 个；超过就用节点 `sub` 拆 detail 图。
7. **生成视图并校验事实层**：`check_graph` 要求每张 Graph 的 `view` 指向最新的 `.mmd`，所以新写的 Graph 必须先有 `.mmd`。第 8 步的 `scripts/build_views` 在默认输出到 `.map/views/` 时会先替每张图运行 `render_graph`；单张可手动 `scripts/render_graph .map/graphs/<flow>.yaml`。之后再运行 `scripts/check_graph .map/graphs` 与 `scripts/check_map.sh [--strict] .map/CODEMAP.md`。
8. **生成可下钻视图**：

   ```bash
   scripts/build_views --root <项目根>              # 编译 + 渲染 + 外壳，输出 .map/views/
   scripts/build_views --root <项目根> --finalize   # 每页走 Archify 完整门禁（含真实浏览器检查）
   scripts/build_views --root <项目根> --only <graph-id>
   ```

   每张图独立失败不阻断其余；退出码非零表示有失败。有源码锚点的图会带 `meta.repository`，锚点在固定版本不存在时不进图（仍留在侧车），并给出警告。
9. **AI 取最小上下文**：`scripts/query_graph .map/graphs --query '<需求>' --depth 2`，优先加载命中节点的 Markdown 章节、规则、风险与锚点。命中带 `sub` 的节点会提示可下钻的子图，分图命中会输出上级链。
10. **开发后反查影响**：`scripts/impact_diff .map/graphs [--base <rev>]`；Diff 未命中必须明确报告，不能解释为「没有业务影响」。
11. **增量写入**：保留所有 `<!-- manual: keep -->` 块，只改变化的事实；不创建 `.bak`，历史交给 Git。

## 读图方式（给人）

打开 `.map/views/index.html`：左侧导航整体可收起 / 展开（侧栏顶部右侧 ☰ 按钮或快捷键 `[`，状态记在浏览器本地；收起后内容区左上角出现「展开导航」按钮），分组与子图也可逐级折叠或「全部收起」。导航按「总 → 分 → 分」生成：分组标题合并为一行「领域 - 视角」（如 `billing - 业务视角`），组内按 `parent` 链逐级嵌套，层数不限；存在多张并列的顶层图时，自动合成「系统总览」作为总入口，各顶层图成为它下面的分；顶部有面包屑和跨图检索（快捷键 `/`，支持中文子串，搜节点名、ID、标签、说明、锚点）。图页面里点节点或边，侧栏出现「Codemap」区：完整说明、标签、证据等级、`path -> symbol` 锚点、边的触发条件；有 `sub` 的节点带「下钻」入口，子图带「上级图」入口。Archify 原有的节点查找、路径探查、可达性、导出等能力全部保留。

## 当前能力边界（未实现的不得宣称已支持）

- **已支持**：`layout.default` 为 `swimlane` / `layered` 的 Graph（编译为 Archify workflow）。所有图从入口层开始排：`direction: LR` 入口在最左、入口泳道在最上；`TB` 入口在最上（level 成行、泳道成列，最多 6 条泳道）。`level` 压缩到 6 列，同泳道同列最多堆叠 4 个节点，超出时编译报错并提示拆 detail 图。
- **未支持**：`state`（生命周期）与 `force` 布局的 Graph 会被跳过并列入汇总；需求 Overlay 的三镜头渲染、力导向发现图、提交钩子自动更新；Graph 的 `rules` 绑定字段已透传到侧车，但 `check_graph` 尚未校验它。
- **无 Graph 源头的图类型**（erd、class、tree、timeline、waterfall、explainer）：不经 Graph 编译，需要时直接用内置 Archify 按其 SKILL 流程出图，不进下钻外壳。
- 渲染链路的完整边界与待办见 [Archify 集成](references/archify-integration.md)。

## 写作约束

- L1 路由必须包含：任务/现象、最小读取集、条件性追加读取集、首个锚点、关键规则、必须验证。
- L2 必须能脱离 L1 理解；高风险 L2 还必须覆盖状态真相、幂等和失败补偿。
- AI 只产出 Graph / Overlay / 查询，不生成任意 HTML、CSS 或坐标；布局由 Archify 自动路由，呈现提示放编译器映射，不进 Graph。
- 严格执行顺序用泳道或分层，生命周期用状态图，单需求用 Overlay；不要用一种布局承载所有语义。
- 误导入口只记录确认走过的弯路；未知内容写盲区，不猜测补齐。
- 当前事实直接更新到所属位置；人工事故结论和业务铁律放进保护块。

## 完成条件

- 一个真实任务或故障现象能从 L1 在两步内到达最小 L2 和首个锚点。
- 高风险领域记录了业务成功、状态真相、不变量、幂等、副作用和失败补偿。
- Graph 无重复 ID、悬空边、孤立节点、缺失条件、失效 refs 或未声明环；生成视图已被 Markdown 引用。
- `scripts/build_views --finalize` 全部通过，节点与边 ID 在 Graph、候选、侧车、HTML 间一致。
- 点击节点/边能看到条件、证据与源码锚点；summary 到 detail 能两跳进退，面包屑正确。
- 结构检查、浏览器检查和人眼视觉复核分别报告，未做的不得声称已验收。
- 关键结论有事实类型、证据等级和具体来源；规则与实现差异进入冲突台账。
- 校验不能通过的项目被明确交付为风险，而不是伪造 `current`。
