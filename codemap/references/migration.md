# 旧地图迁移规范

仅在项目的 `.claude/` 或 `.codex/` 中存在旧 `CODEMAP*` / `MAPCODE*` 时读取。

## 目标

迁移完成后，所有地图文件只保留在项目根目录 `.map/`。所有 AI 入口引用同一份 `.map/CODEMAP.md`，不复制正文。

## 步骤

1. 读取所有旧地图、适用的 AI 入口和 Git 状态；不要先移动或删除。
2. 按语义归类内容：
   - 任务、症状、入口、调用链、误导入口进入导航结构。
   - 人工规则、状态真相、幂等、补偿、观测和冲突进入高风险业务结构。
   - 目录树、重复接口清单、分析动作和旧 changelog 不迁移。
3. 逐字保留 `<!-- manual: keep -->` 块。没有保护标记但明显属于人工规则/事故结论的内容，先包进保护块。
4. 同一结论冲突时不要择一：创建 `[CONFLICT][conflict]`，把目标文件设为 `status: conflict`。
5. 把旧 Markdown Mermaid 图迁移为 `.map/graphs/*.yaml`，用 `render_graph` 生成到 `.map/views/`；Markdown 只保留视图链接。
6. 旧地图没有可靠证据或基线时，目标文件使用 `status: needs-review`；不要为了迁移通过校验伪造 `current`。
7. 更新已有 `AGENTS.md`、`CLAUDE.md` 等入口中的旧路径，使其只引用新 L1。
8. 同时运行 `check_graph` 和普通地图校验，确认目标完整后再删除旧文件。删除前用 `git diff --stat` 明确列出范围。

Git 已保存旧版本，不创建 `.bak`。若旧文件未纳入 Git，迁移前不得删除其中无法重建的人工内容。
