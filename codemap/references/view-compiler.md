# 类型化视图编译契约

Codemap 的 Graph 是业务事实，ViewSpec 是可重建的阅读请求，渲染 HTML 是临时产物。三者不能混成一层：

```text
Graph / Markdown / Overlay
            ↓
        ViewSpec
            ↓
  Codemap Explorer 或 Archify 适配器
            ↓
      HTML / SVG / 浏览器回执
```

## ViewSpec 的职责

ViewSpec 只声明“从哪张图、用什么语义和镜头阅读”，不能复制节点、边、规则、源码锚点或坐标。它适合放在 `.map/views/<name>.view.yaml`，也可以只在临时目录生成。

```yaml
schema: codemap.view/v1
id: billing-workflow
title: Billing 计费主链
graph: billing-settlement
overlay: null

render:
  engine: codemap-web       # codemap-web；未来可接 archify-adapter
  mode: swimlane            # relation | swimlane
  semantic: workflow        # architecture | workflow | sequence | dataflow | lifecycle

selection:
  focus: preconsume
  edge_kinds: [sync, async, compensate]
  depth: 2

quality:
  require_evidence: true
  max_nodes: 18
  max_edges: 32
```

### 字段约束

- `graph` 必须引用已加载的 `codemap.graph/v2` Graph ID。
- `overlay` 只能引用已加载的 `codemap.overlay/v1` ID；需求视图必须明确它是方案层。
- `render.mode` 是当前 Explorer 的实际布局；现阶段只支持 `relation` 和 `swimlane`。
- `render.semantic` 是目标语义，不等于当前已经存在对应渲染器。`workflow`、`sequence`、`dataflow`、`lifecycle` 后续可由 Archify 适配器承接。
- `selection.focus` 必须是 Graph 中的节点 ID；`edge_kinds` 只能使用 Graph 已出现的边类型。
- `depth` 只控制阅读焦点的上下文深度，不改 Graph 的关系事实。
- `quality` 是视图生成门禁，不是业务规则；证据不足时只能提示或失败，不能补写事实。

## 五类语义投影

同一张业务 Graph 可以按不同问题投影，不需要复制五张事实图：

| 语义 | 适合回答 | Archify 目标类型 |
| --- | --- | --- |
| `architecture` | 系统边界、服务、存储和外部依赖 | Architecture |
| `workflow` | 角色/服务之间的严格业务顺序 | Workflow |
| `sequence` | 一次请求的调用先后、返回、重试 | Sequence |
| `dataflow` | 数据从输入到存储和下游的流转 | Dataflow |
| `lifecycle` | 状态、迁移、失败和终态 | Lifecycle |

投影规则：

1. 节点和边沿用 Graph 稳定 ID，不能在渲染层重新编号。
2. `condition`、`kind`、`evidence` 和 `refs` 是关系语义，不能因为画面简洁被删除。
3. `path + symbol` 在生成源码链接时临时解析为行范围；行号不写回 Graph。
4. 视图可以选择节点和边，但“未选中”不代表事实不存在。
5. Graph、Overlay 变化后，ViewSpec 和 HTML 都应重新生成；不要手改 HTML。

## 质量流水线

当前阶段由 `render_web --view` 完成 ViewSpec 校验、Graph 校验和 HTML 生成。后续接入 Archify 时保持同一顺序：

1. 校验 Graph、Overlay 和 ViewSpec。
2. 生成对应类型的临时 IR，不把 IR 写回事实层。
3. 生成 HTML/SVG，检查稳定 ID、节点/边覆盖和证据入口。
4. 在浏览器中检查横向溢出、节点碰撞、标签可读性、主题和键盘焦点。
5. 生成机器可读回执；回执绑定 Graph 提交、ViewSpec 内容和产物哈希。
6. 明确区分“结构检查通过”“浏览器检查通过”和“人眼视觉复核通过”。

没有完成第 4 步时，只能说“生成成功”，不能说“视觉质量已验收”。

## 与 MCP 的边界

MCP 只应暴露 ViewSpec 和 Core 能力，例如 `codemap.query`、`codemap.impact`、`codemap.render`。MCP 不保存第二份 Graph，不直接修改 HTML，也不绕过 Skill 的证据和 Overlay 规则。
