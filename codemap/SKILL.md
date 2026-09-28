---
name: codemap
description: >
  生成、读取和维护跨 AI 共用的 CODEMAP：把开发任务、故障现象与代码锚点关联起来，并从同一份结构化 Graph 生成 Mermaid、本地交互式知识图谱、业务泳道、需求影响图、Git Diff 反查和按需上下文。用户要求梳理代码结构、调用链、改动入口、业务规则、影响范围或可视化时使用；已有地图且在陌生模块反复搜索、做跨域影响分析或高风险改动时按需读取。不要为普通 CRUD 或一次搜索即可定位的局部改动建图。
---

# Codemap

让下一次冷启动能在两步内从任务或故障现象走到首个可靠代码锚点，并在高风险业务中看见不能破坏的规则。

CODEMAP 是带证据的导航缓存，不替代源码、测试、运行环境或人工确认的业务要求。

核心原则是：**持久化事实，动态生成视图**。Markdown 与 Graph 保存可复核的业务事实；Mermaid、Web、单需求影响图和 AI 上下文包都是派生视图，不得反向成为第二套真相。

首次建设或改版前先读取 [改造方向与分层契约](references/product-direction.md)，先确定每层职责，再生成地图文件。

视图改造还要读取 [类型化视图编译契约](references/view-compiler.md)：ViewSpec 只描述阅读请求，Archify 或其他渲染器只接收派生 IR，不得把坐标、排版和渲染字段写回 Graph。

## 使用边界

- 已有地图时，只在缺少上下文、跨域分析或高风险改动时读取 L1，再按路由加载最小 L2；不要把全量地图作为每次任务的前置仪式。
- 只有用户明确要求建图/更新，或当前任务实际改变了地图已记录的行为时才写地图；普通编码任务不顺手生成文档。
- 不记录目录树、完整接口清单、机械的 Controller 到 Service 罗列、无状态 CRUD，或一次源码搜索即可恢复的事实。
- 地图不能成为任务阻塞项。状态不是 `current` 时，把它当线索并回到源码核对。

## 两种模式

### 导航模式（默认）

回答“改哪里、调用怎么走、这个现象先查哪”。记录任务路由、模块职责、入口锚点、症状定位、显式控制/数据流和确认踩过的误导入口。

创建或大改导航结构时读取 [导航地图模板](references/navigation-template.md)。

### 高风险业务模式（按需增强）

当任务涉及资金、权限、库存、额度、订单、风控、对外状态、复杂状态机，或多存储/第三方副作用时，在导航内容上追加：业务成功定义、状态真相、不变量、事务/并发、幂等、重试、补偿、人工兜底和验证边界。

创建或大改高风险领域包时读取 [高风险业务模板](references/business-chain-template.md)。不要让普通领域承担这套成本。

## 权威与证据

地图必须区分：

- **规范性事实**：只有 `[RULE][human-confirmed]` 可作为人工确认的业务要求。
- **描述性事实**：`IMPL`、`VERIFY`、`RISK` 描述当前实现、验证结果和缺口；源码、测试、运行环境分别决定各自事实。
- **冲突**：规则和实现不能同时成立时写 `[CONFLICT][conflict]`，同时保留两边证据，不得自行裁决。

写任何关键结论前读取 [事实、证据与新鲜度规范](references/evidence-model.md)。

## 统一产物

```text
.map/CODEMAP.md                 # L1：任务路由、领域摘要、症状定位、全局规则/冲突
.map/CODEMAP-<domain>.md        # L2：领域导航；高风险领域可追加业务链
.map/graphs/<flow>.yaml         # v2 结构化关系层，供检索和派生视图使用
.map/views/<flow>.mmd           # 由 Graph 单向生成的 Mermaid 视图
.map/views/<flow>.view.yaml     # 可选的 ViewSpec，只声明语义视角和阅读镜头
.map/overlays/<task>.yaml       # 单需求影响覆盖层，默认不并入基础 Graph
.map/site/index.html            # 由 Graph 单向生成的本地交互视图
.map/context/<task>.md          # 按需求生成的临时 AI 上下文包
```

- L1 和 L2 必须扁平同级；Graph 和生成视图分别放入固定子目录。名称只用小写英文、数字和连字符。
- L1 目标不超过 120 行，L2 目标不超过 240 行。
- `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、Cursor/Windsurf 规则等只引用同一份 `.map/CODEMAP.md`，不复制正文。
- 若发现 `.claude/` 或 `.codex/` 中的旧 `CODEMAP*`，先读取 [迁移规范](references/migration.md)，不得留下两套 Codemap 事实源。
- 基础 Graph 只保存已存在或已确认的事实。尚未实施的需求写入 Overlay，并明确标记 `proposal/unverified`；完成源码和验证后才能提升进基础 Graph。

## 两条开发导航路径

- **正向定位**：任务或故障现象 → `query_graph` → 相关子图 → required Markdown → 源码锚点。
- **反向核查**：Git Diff → `impact_diff` → 直接命中节点/边 → 下游影响 → 未覆盖文件与验证边界。

两条路径只缩小调查范围，不替代源码和测试。涉及高风险逻辑时，即使地图命中也要回到实现核对；Diff 未命中必须明确报告，不能解释为“没有业务影响”。

## 改版与重建

- 先冻结当前技能中的职责、Markdown 模板、Graph Schema、Overlay 和视图规则，再生成项目地图；不得让旧地图反过来限制新定义。
- 新版只接受 `codemap.graph/v2`。旧 Graph 不兼容、不自动迁移，也不混入新版 Explorer 或查询结果。
- 重建以源码、测试、运行证据和人工确认规则为输入；旧 Codemap 只可作为待核对线索，禁止机械复制节点、边和结论。
- 改版验收先输出到隔离目录 `.map/next/`，工具只读取该目录下的新版 Graph；完整验证后再由用户决定是否替换正式地图。不得自动删除或覆盖旧地图。
- `CODEMAP*.md` 面向 AI，优先表达任务路由、边界、不变量、风险和证据；Graph 只承载关系与视图所需语义，避免复制长篇业务说明。

## 工作流

1. **读项目约束**：读取适用的 `AGENTS.md`、`CLAUDE.md` 等入口，确认已有文档和编辑边界。正式地图统一放在项目根目录 `.map/`；改版预览使用 `.map/next/`，不得与旧 Graph 混合读取。
2. **读取最小上下文**：若地图存在，先读 L1 的路由、`status` 和冲突，再加载命中的最小 L2；找不到路由才探索源码。
3. **发现真实入口**：从路由、命令、事件、任务、状态写入和测试追踪业务模块。跳过生成代码、依赖和迁移产物。
4. **选择分层**：运行 `scripts/count_sources.sh [项目根]` 取得规模提示。源码超过 50、核心领域/业务链超过 4、L1 预计超过 120 行，或多个高风险领域需要独立维护时拆 L2；文件数不是唯一判断。
5. **按模式组织内容**：默认使用导航模板；只有命中高风险条件的领域才加载并追加业务模板。
6. **逐条取证**：锚点使用 `路径 -> 符号/SQL/配置键`，不保存行号。显式调用才进入控制流；隐式钩子、反射、自动注册找不到证据时标 `unverified` 并给出验证路径。
7. **生成结构化 Graph**：按 [Graph Schema](references/graph-schema.md) 从源码和人工规则重新生成至少一张 summary Graph；不得把旧 Graph 当模板逐字段升级。YAML 是节点、边、泳道、条件和证据的唯一结构化关系源，不手写 Mermaid，也不保存渲染坐标。
8. **生成静态与交互视图**：运行 `scripts/render_graph <graph.yaml>` 生成 Mermaid；运行 `scripts/render_web .map/graphs --open` 生成并打开本地 Explorer。需要固定阅读镜头时，先写不含节点/边的 ViewSpec，再运行 `scripts/render_web .map/graphs --view .map/views/<name>.view.yaml --open`。Web 同时提供关系图和适用时的业务泳道，CODEMAP Markdown 不复制视图源码。
9. **按需求生成影响视图**：需求尚未实现时，按 [交互视图与需求覆盖层](references/interactive-explorer.md) 创建 `.map/overlays/<task>.yaml`，再用 `render_web --overlay` 展示新增、修改、风险和删除候选。Overlay 不得伪装成当前实现。
10. **为 AI 抽取最小上下文**：运行 `scripts/query_graph .map/graphs --query '<需求>' --depth 2`。优先加载命中节点的 Markdown 章节、规则、风险和源码锚点；`stale/needs-review/conflict/unverified` 只作线索并回到源码核对。
11. **开发后反查影响**：代码发生变化后运行 `scripts/impact_diff .map/graphs`；需要与分支基线比较时传入 `--base <rev>`。按 [代码改动影响分析](references/change-impact.md) 核对直接命中、下游影响和未覆盖文件，再决定是否更新基础 Graph 或需求 Overlay。
12. **增量写入与接入**：保留所有 `<!-- manual: keep -->` 块，只改变化的事实。Git 已提供恢复能力，不创建 `.bak`，不维护重复 changelog。仅向已存在且适用的 AI 入口追加按需读取规则。
13. **确定性校验**：同时校验导航文档、Graph 和使用中的 ViewSpec：

   ```bash
   scripts/check_graph .map/graphs
   scripts/check_map.sh .map/CODEMAP.md
   scripts/check_map.sh --strict .map/CODEMAP.md
   ```

   `render_web --view` 会在写 HTML 前校验 ViewSpec 引用的 Graph、Overlay、焦点节点、边类型和质量上限。`check_map.sh` 会调用 Graph 校验器、收集 YAML refs 并纳入条目级过期检测。普通模式报告结构、链接、锚点、新鲜度和冲突；严格模式将失效锚点、过期、冲突、非 `current`、未纳入 Git 和超限判为失败。

## 写作约束

- L1 路由必须包含：任务/现象、最小读取集、条件性追加读取集、首个锚点、关键规则、必须验证。
- L2 必须能脱离 L1 理解；高风险 L2 还必须覆盖状态真相、幂等和失败补偿。
- Summary Graph 最多 12 个节点，detail Graph 最多 18 个节点；超过就用节点 `sub` 拆出 detail 图。
- Obsidian 式力导向图只用于发现关联；严格执行顺序使用泳道或分层图，生命周期使用状态图，单需求使用影响覆盖层。不要用一种布局承载所有语义。
- AI 生成的是 Graph/Overlay/View Query，不生成任意 HTML、CSS 或坐标；布局和交互由 `render_web` 统一实现。
- ViewSpec 只允许引用 Graph/Overlay ID、语义类型、布局模式、焦点、边类型过滤和质量上限；禁止复制节点、边、规则、refs 或坐标。
- 语义视图按 `architecture / workflow / sequence / dataflow / lifecycle` 选择；当前 Explorer 先落地 `relation / swimlane`，其他类型只能标为目标投影，不得伪装成已经支持的渲染器。
- Archify 适配器属于可替换的派生渲染层；它可以消费临时 IR，但不能成为 Codemap 的事实存储或 MCP 的第二份状态。
- Explorer 左侧导航由 `domain / kind / level / parent / sub` 自动生成“领域 → 视角 → 总图/分图”，不得手工维护第二套菜单结构。
- 节点数量不受单屏限制；summary/detail 上限约束的是业务粒度，不是画布容量。关系图和泳道图分别使用自适应间距，默认舒适视图，完整缩放由用户主动触发。
- 误导入口只记录确认走过的弯路；未知内容写盲区，不用猜测补齐。
- 当前事实直接更新到所属位置；历史变化交给 Git。人工事故结论和业务铁律放进保护块。

## 完成条件

- 一个真实任务或故障现象能从 L1 在两步内到达最小 L2 和首个锚点。
- 高风险领域记录了业务成功、状态真相、不变量、幂等、副作用和失败补偿。
- Graph 无重复 ID、悬空边、孤立节点、缺失条件、失效 refs 或未声明环，生成视图已被 Markdown 引用。
- 本地 Explorer 能在全局关系、领域关系和业务泳道之间切换；点击节点可看到关联边、证据与源码锚点，点击或悬停边可在侧栏查看条件与说明。
- 一个真实需求能生成不污染基础 Graph 的 Overlay，并在“改前 / 只看改动 / 改后带上下文”之间切换；`query_graph` 能输出可审计的最小上下文包。
- 一组真实 Git 改动能由 `impact_diff` 反查直接命中、有限深度的下游影响和未覆盖文件；结果不夸大为完整影响证明。
- 固定的业务视角能由 ViewSpec 重建，且渲染器变化不会改变节点/边 ID、证据和业务条件。
- 结构检查、浏览器检查和人眼视觉复核分别报告，未完成浏览器或人工检查时不得声称视觉质量已验收。
- 关键结论有事实类型、证据等级和具体来源；未运行的内容没有标成 `runtime-verified`。
- 规则与实现差异进入冲突台账，没有被静默改写。
- 校验通过；不能通过的项目被明确交付为风险，而不是伪造 `current`。
