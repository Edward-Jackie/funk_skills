# Archify 集成

Codemap 3.0 用内置的 Archify 分支渲染。事实留在 Graph，呈现交给 Archify，两者用稳定 ID 绑定。

## 为什么用侧车，而不是把字段塞进 Archify

Archify 的每层 schema 都是 `additionalProperties: false`，校验器由 `renderers/archify/scripts/generate-validators.mjs` 生成。往里加字段要同时改 schema、重生成校验器、改渲染器，升级上游时回归成本高。所以编译器把一张 Graph 拆成两份产物：

```text
.map/graphs/<flow>.yaml
        │  scripts/compile_graph
        ├─► <flow>.candidate.json   只含绘图字段，Archify schema 不动
        └─► <flow>.facts.json       以节点/边 ID 为键的语义事实
                  └─► loadDiagram 把它内嵌进 HTML（inline JSON 块 + 样式 + 扩展脚本）
```

Archify 的 `deliver` 会把侧车随规格快照冻结，所以 `finalize` 的回执哈希覆盖注入后的产物，provenance 为 `current`。没有 `.facts.json` 时输出与原版 Archify 字节级一致。

## 映射表（Graph v2 → Archify workflow）

| Graph v2 | Archify | 说明 |
|---|---|---|
| node `id` / `label` | 同名 | ID 必须以字母开头，否则编译报错 |
| node `lane` | `lanes[]` 与 `nodes[].lane` | 无泳道声明时生成单泳道 |
| node `level` | `col`（0..5） | 跨泳道全局顺序，均匀压缩到 6 列 |
| 同泳道同列多节点 | `yOffset` 竖向堆叠，步长 140 | 单格最多 4 个，超出报错，提示拆 detail 图。较原步长 90 增加路由留空；画布可能增高，不能据此保证消除 `ambiguous-corridor`，仍须执行布局门禁 |
| node `kind` | `type`：entry→frontend，process/decision/terminal→backend，state/store→database，external→external | |
| node `detail` | `sublabel`（截断 26 字） | 全文在侧车 |
| node `tags[0]` | `tag` | 全部标签在侧车 |
| node `refs` | `sources`（≤3 条，`label`=symbol，≤48 字） | 仅在给出 `--repo-root` 且文件在固定版本存在时进图 |
| edge `kind` | `variant`：sync/read/write/transition→default，async/schedule/depends-on→dashed，compensate→security；`role`：async、error | |
| edge `label` | `label` | 无 label 且 condition 非 `always` 时，用 condition 截断 14 字 |
| edge `condition` / `detail` / `refs` / `evidence` | 无 | 只在侧车 |
| `layout.default` | swimlane / layered → workflow | 其余暂不支持 |
| graph `verified_commit` | `meta.repository.revision` | 非 40 位十六进制时退回 `HEAD`；SSH 或非 https 来源用 `local-only`，凭据会被剥掉 |

## 事实侧车 `codemap.facts/v1`

```json
{
  "schema": "codemap.facts/v1",
  "titles": { "<sub 或 parent 的图 ID>": "<标题>" },
  "graphs": { "<图 ID>": { "id", "title", "kind", "level", "status", "node_count", "edge_count" } },
  "graph": { "id", "title", "domain", "summary", "kind", "level", "parent", "status", "verified_at", "verified_commit" },
  "nodes": { "<id>": { "kind", "level", "detail", "tags", "refs", "evidence", "context", "sub", "rules" } },
  "edges": { "<id>": { "kind", "label", "condition", "detail", "refs", "evidence", "rules" } }
}
```

注入时转义 `<`、`>`、`&`、`{{`、U+2028/2029，避免破坏 HTML 和模板占位。

带 `sub` 的节点会在卡片右下角注入 `↳ 下钻 N` 按钮（18px 高）：`N` 为子图节点数，用于提示信息密度；业务子图用暖色、`status=conflict` 子图用红色，按钮可点击直接进入子图。注入时会把卡片底部标签左对齐，给按钮让位。Passport 的下钻按钮同时展示子图节点数与关系数。

## 页面与外壳的通信

| 方向 | 消息 | 触发 |
|---|---|---|
| 图 → 外壳 | `{source:'codemap', type:'open', graph, node?}` | 点「下钻」或「上级图」且页面在 iframe 内 |
| 外壳 → 图 | `{source:'codemap', type:'focus', node}` | iframe `load` 后发送，600ms 后补发一次（聚焦幂等） |

两端都校验 `source` 字段，外壳还校验 `event.source` 必须是当前 iframe。页面不在 iframe 内时，下钻用 `location.href = '<graph>.html'`。外壳 hash 形如 `#/<graph-id>` 或 `#/<graph-id>/<node-id>`。

## 布局与关系线门禁

`build_views --strict-layout` 在渲染后运行 Archify 组合检查，以下问题直接判失败：

| 问题码 | 含义 | 优先处理 |
| --- | --- | --- |
| `composition/proper-crossing` | 两条关系线交叉 | 调整泳道/层级，或拆图 |
| `composition/ambiguous-corridor` | 两条关系线共享走廊，视觉上重叠 | 减少跨泳道边，或把同向依赖聚合为一个节点 |
| `composition/arrowhead-collision` | 进入同一节点的箭头过近 | 合并重复入边，或拆分接收节点 |
| `composition/label-route-clearance` | 边标签压线或被遮挡 | 调整标签位置或简化边 |
| `composition/container-border-run` | 关系线贴着容器边框长距离走 | 调整泳道顺序或拆图 |

关系线密度是图结构的信号，不是渲染参数问题。优先把一张图拆成「总览 + 2~3 张 detail」，或把多个同向依赖聚合为一个节点并在标签/事实侧车保留明细；不要为了少拆图继续加节点或加边。

`build_views` 每张图在输出目录内的独立暂存目录编译和验收，通过后才替换该图派生产物；重跑不会复用陈旧浏览器回执，失败保留原产物。不要手删浏览器回执来把失败改成通过，直接重跑构建并读取本次回执。

## 补丁层改动清单（相对原版 Archify 3.2）

| 文件 | 改动 |
|---|---|
| `renderers/shared/codemap-facts.mjs` | 新增：注入逻辑、样式、Passport 扩展 |
| `renderers/shared/cli.mjs` | `loadDiagram` 在候选旁有 `.facts.json` 时注入模板 |
| `bin/archify.mjs` | `deliver` 把侧车随规格快照冻结到暂存目录 |

其余文件保持原版。三处改动以补丁形式保存在 `patches/archify-codemap.patch`（相对 Archify 3.2，`-p1`），已验证在原版目录上应用后与 `renderers/archify/` 逐文件一致：

```bash
cp -R <新版 archify> /tmp/archify-new && cd /tmp/archify-new
patch -p1 < <codemap>/patches/archify-codemap.patch
```

升级上游时先应用补丁，再用 `scripts/build_views --finalize` 对一个真实项目做回归。

## 收录规则（vendor 时对原版做的非补丁处理）

- 原版根目录的 `SKILL.md` 改名为 `SKILL.archify.md`，避免技能扫描器把 `renderers/archify/` 当成第二个 skill；Archify 代码没有读取该文件。
- 不收录 `examples/`（约 13 MB，仅 `archify examples/demo/doctor` 和无输入时的默认样例使用）、`node_modules/`、`.git/`。
- `skill-release.json` 保留。`finalize` 回执里的 `update` 段会提示「Archify 有新版」，那是原版上游的更新提醒，对本分支不适用，忽略即可。

## 验证口径

- 每页：`archify validate`、`deliver`、`check`、`browser-check` 通过（`build_views --finalize`）。
- 无侧车时产物与原版字节级一致。
- 浏览器检查与人眼视觉复核分别报告。

## 已知问题与待办

- **布局可读性**：个别 Graph 编译后触发 `viewer/projected-text-readability`（文字缩放过小），与侧车无关，源于列压缩与堆叠；需要按图拆 detail 或调整编译参数。
- **回执不含侧车哈希**：facts 变化时回执看不出来。
- **`rules` 字段**：编译器已透传，`check_graph` 尚未校验，规则 ID 格式待对照 `evidence-model.md` 定稿。
- **未实现**：`state` 与 `force` 布局、Overlay 三镜头渲染、力导向发现图、提交钩子、规则总表页。
- **没有 Graph 源头的图类型**：erd、class、tree、timeline、waterfall、explainer 不经编译器。
