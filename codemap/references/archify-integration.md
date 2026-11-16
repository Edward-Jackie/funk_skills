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

Archify 的 `deliver` 会把侧车随规格快照冻结，所以 `finalize` 的回执哈希覆盖注入后的产物，provenance 为 `current`。没有 `.facts.json` 时不注入 Codemap 菜单与滚轮处理；模板提供的扩展方法不启用，保留原有阅读行为。

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
| `layout.default` | swimlane / layered → workflow；state → lifecycle v3 | state 必须有明确 lifecycle 初终/主路径；force 暂不支持 |
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
| 图/外壳 → 宿主 | `{source:'codemap', type:'ready'}` | 请求重新授予当前宿主能力 |
| 宿主 → 外壳 → 图 | `{source:'codemap', type:'capabilities', actions, context:{repo_id,branch}}` | 仅接受 `create-requirement`；独立本地文件不接受维护能力 |
| 图 → 外壳 → 宿主 | `{source:'codemap', type:'action', action:'create-requirement', graph, node?, edge?, context}` | 打开需求草稿；不直接写入、不携带命令或任意文件路径 |

每一跳都校验 `event.source` 和 `event.origin`，能力只能由直接宿主授予；外壳校验当前图、对象存在与动作白名单。`source` 字段只是协议标记。父来源由 `document.referrer` 或同源推导，文件模式只允许只读定位；不接受任意首次握手来源。页面不在 iframe 内时，下钻用 `location.href = '<graph>.html'`。外壳 hash 形如 `#/<graph-id>` 或 `#/<graph-id>/<node-id>`。宿主 focus 可额外带 graph，外壳先定位图再聚焦。

### V4.2 画布交互

普通滚轮只在画布实际命中时按指针缩放，范围为 0.25—3；增量按 deltaMode 换算，限制到 ±100 像素后使用连续指数缩放。缩放达到边界仍阻止页面滚动；Ctrl/Cmd 手势保留浏览器行为。侧栏、输入、弹窗、菜单及工具栏不触发底图缩放。所有缩放和平移共用 `Archify.view`，不保存业务坐标。

右键按空白/节点/关系提供阅读动作，与键盘 Shift+F10、更多按钮共用集中动作表；菜单支持方向键、Escape、边缘避让。维护入口仅在宿主授予后显示，首版裸 MAP 只支持发起需求，评注和发布必须进入有版本上下文的工作台。

## 布局与关系线门禁

### 设计投影（V4.2 开发分支）

`scripts/compile_design <requirement.json> --out-dir <目录> --view domain|flow|page [--scenario <id>]` 消费工作台同一份 schema=1 修订。flow 且 lifecycle 适用时投影 states/transitions/mainPath；普通 CRUD 的 flow 和其余视图投影 workflow。输出 JSON 回执给出 candidate/facts 路径，随后使用现有 `archify finalize <type> <candidate> <html> --json --out-dir <唯一回执目录>` 完成渲染门禁。脚本只写明确指定的派生产物，不发布 Graph/MAP，也不执行源码或业务条件。

侧车 `graph.mode=design` 保存 requirement_id/version/revision；对象、关系、完整条件、动作、规则和场景依据来自输入修订，证据保持 unverified。工作台确认和真实实现证据仍由 Core 判断，设计图不能代签。生命周期按完整初终状态呈现，场景范围保存于侧车用于关联说明；其余视图按场景过滤，空视图说明原因。超过 18 个节点要求缩小场景范围。

需求规范 ID 不受 Archify 的字母前缀限制：仅对渲染器不接受的 ID 做确定性编码，并避让所有规范 ID。侧车 `id_map.canonical_to_render/render_to_canonical` 和每项 `original_id` 保留可逆对应；规则/条件/对象正文仍为规范 ID。链接、侧栏、宿主事件对外回映规范 ID，渲染内部别名不是第二份业务对象。合法字母前缀 ID 保持不变。

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
| `renderers/shared/codemap-interactions.mjs` | 画布滚轮分区、集中菜单动作、宿主能力桥 |
| `assets/template.html` | 在原摄像机内增加指针缩放与 Codemap 平移模式；无侧车时不启用 |
| `renderers/shared/cli.mjs` | `loadDiagram` 在候选旁有 `.facts.json` 时注入模板 |
| `bin/archify.mjs` | `deliver` 把侧车随规格快照冻结到暂存目录 |

其余文件保持原版。五处改动以补丁形式保存在 `patches/archify-codemap.patch`（相对 Archify 3.2，`-p1`），已验证在原版目录上应用后与 `renderers/archify/` 逐文件一致：

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
- 无侧车时不启用 Codemap 交互，原生渲染与浏览器门禁回归。
- 浏览器检查与人眼视觉复核分别报告。

## 已知问题与待办

- **布局可读性**：个别 Graph 编译后触发 `viewer/projected-text-readability`（文字缩放过小），与侧车无关，源于列压缩与堆叠；需要按图拆 detail 或调整编译参数。
- **回执不含侧车哈希**：facts 变化时回执看不出来。
- **`rules` 字段**：V4.2 开发分支已校验结构化 ID/版本，旧字符串保留并标未结构化；规则表存在不代替人工确认。
- **未实现**：`force` 布局、Overlay 三镜头渲染、力导向发现图、提交钩子、规则总表页。
- **没有 Graph 源头的图类型**：erd、class、tree、timeline、waterfall、explainer 不经编译器。
