# 交互视图与需求覆盖层

Codemap 的 Markdown 和 Graph 保存事实，Web Explorer 只负责展示。任何视觉布局、筛选结果和临时需求图都不得反向改写基础事实。

## 视图选择

| 问题 | 视图 | 约束 |
| --- | --- | --- |
| 整个系统有哪些领域、彼此如何关联 | 力导向关系图 | 只做发现，不表达严格先后顺序 |
| 当前领域周围有哪些依赖 | 局部关系图 | 默认一至两跳，避免全图噪音 |
| 一次请求如何跨系统运行 | 业务泳道 | 节点按 `lane` 分组，横向表示主顺序 |
| 状态怎样迁移 | 状态图 | 条件写在边上，失败与补偿不能省略 |
| 新需求会影响哪里 | 需求影响图 | 基础图加 Overlay，不直接修改基础图 |

同一 Graph 可以生成多个视图。视图切换只改变布局和可见范围，不改变节点、边、证据或 refs。

## 总分总钻取

左侧菜单必须从 Graph 元数据自动生成，不维护单独配置：

```text
领域
├─ 业务视角
│  ├─ 业务总览        总
│  └─ 核心业务链      分
├─ 服务视角
│  ├─ 跨服务架构      总
│  └─ 单服务链路      分
└─ 需求方案
   └─ 当前需求        方案
```

1. `domain` 形成领域根，`kind` 归入业务或服务视角，`level` 显示总图/分图标签。
2. `parent` 和 summary 节点的 `sub` 建立下钻与返回关系。
3. 顶部面包屑显示 `领域 / 视角 / 父图 / 当前图`，需求模式追加 Overlay 标题。
4. 点击业务链后切换为泳道或状态图；点击节点展示规则、风险、证据、Markdown 章节和源码锚点。
5. 收拢时保留当前影响范围高亮，帮助用户回到整体。

节点 ID 在不同视图中保持稳定，渲染器可据此实现位置过渡。不要把坐标写回 Graph。

## 需求 Overlay

未实施需求使用 `.map/overlays/<task>.yaml`：

```yaml
schema: codemap.overlay/v1
id: api-key-daily-quota
title: API Key 每日额度
status: proposal
query: 为 API Key 增加按自然日重置的消费额度
base_graphs: [billing-settlement]

nodes:
  - id: preconsume
    graph: billing-settlement
    action: modify
    reason: 预扣时同时校验每日窗口额度

  - id: daily-window
    graph: billing-settlement
    action: add
    label: 每日额度窗口
    kind: state
    lane: redis
    level: 2
    detail: 按时区和自然日保存已用、在途与 generation
    tags: [api-key, quota, daily]
    refs: []
    evidence:
      level: unverified
      note: 需求方案，尚未实现

edges:
  - id: window-to-preconsume
    graph: billing-settlement
    action: add
    reason: 每次预扣都必须占用对应自然日的额度窗口
    from: daily-window
    to: preconsume
    kind: sync
    label: 校验并占用
    condition: 请求进入预扣
    detail: null
    refs: []
    evidence:
      level: unverified
      note: 需求方案，尚未实现
```

`action` 取值：

- `add`：准备新增。
- `modify`：准备修改现有节点或边。
- `risk`：需要重点验证，但不一定修改。
- `remove`：准备移除，渲染时仍保留轮廓以表达影响。

Overlay 必须保持 `status: proposal`，且新增节点和边使用 `unverified`。实现并完成源码、测试或运行验证后，才能把事实提升进基础 Graph，然后删除或归档 Overlay。

需求图提供三种镜头：

- **改前**：只显示基础 Graph，便于确认当前事实。
- **只看改动**：默认显示 Overlay 节点、Overlay 边及一跳必要上下文，适合开发和评审。
- **改后带上下文**：把 Overlay 叠加到完整基础 Graph，适合检查下游影响。

开发进度不复用 `add / modify / risk / remove` 的颜色。计划中、开发中、已验证等进度放到右侧清单，避免“改动类型”和“完成状态”混淆。

## AI 上下文查询

```bash
scripts/query_graph .map/graphs \
  --query "API Key 每日额度" \
  --depth 2 \
  --overlay .map/overlays/api-key-daily-quota.yaml \
  --out .map/context/api-key-daily-quota.md
```

查询器按标题、描述、标签、Markdown 章节和源码锚点选种子，再沿边扩展有限深度。输出应包含：

- 命中的 Graph 及其状态。
- 节点、边、条件和证据。
- 最小 Markdown 章节引用。
- 源码锚点。
- Overlay 的新增、修改、风险和删除候选。

查询结果是临时上下文，不是事实源。未命中不代表不存在，涉及高风险逻辑时仍需源码搜索。

## 本地 Explorer

```bash
scripts/render_web .map/graphs \
  --overlay .map/overlays/api-key-daily-quota.yaml \
  --open
```

默认生成 `.map/site/index.html`，不启动服务、不访问网络。Explorer 至少提供：

- Graph 搜索与切换。
- 按“领域 → 业务/服务视角 → 总图/分图”组织左侧菜单，需求 Overlay 单独放在“需求方案”。
- 顶部显示当前领域、父图和需求方案的面包屑。
- 关系探索和业务泳道切换；进入声明 `layout.default: swimlane` 的明细图时默认使用泳道。
- 需求模式支持“改前 / 只看改动 / 改后带上下文”。
- 同步、异步、读写、定时和补偿边筛选。
- 关系图画布不直接渲染边注释，避免文字与连线交叉；悬停或点击边时在右侧展示关系类型、触发条件、说明和证据。
- 选中节点时在右侧列出全部入边和出边，可从关系列表高亮对应连线。
- 节点证据、风险、Markdown 上下文和源码锚点。
- Overlay 开关与动作图例。

## 阅读密度

- 不限制单屏节点数量；summary/detail 的节点上限只控制建模粒度。
- 关系图按节点数量自适应理想边长：少量节点约 260px，中等约 230px，较多约 205px。
- 泳道默认宽度约 240px，纵向层级间距约 130px，同层节点错位约 100px。
- 默认使用约 `0.92` 的舒适缩放并保留拖拽空间，不自动把整图压进一屏。
- “适配画布”是显式操作；扩大间距后不能再用自动全图缩放抵消留白。
