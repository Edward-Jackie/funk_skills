# 旧地图迁移规范

仅在项目的 `.claude/` 或 `.codex/` 中存在旧 `CODEMAP*` 时读取。

## 目标

迁移完成后，事实只保留在 `~/.codemap/maps/<project>/<branch>/`（旧版为项目内 `.map/`）。所有 AI 入口引用同一份 `<map-root>/CODEMAP.md`，不复制正文。

先用脚本完成目录迁移与视图分组：

```bash
scripts/migrate_maps --root <项目根> [--branch <分支>] [--remove-legacy]
```

## 步骤

1. 读取所有旧地图、适用的 AI 入口和 Git 状态；不要先移动或删除。
2. 按语义归类内容：
   - 任务、症状、入口、调用链、误导入口进入导航结构。
   - 人工规则、状态真相、幂等、补偿、观测和冲突进入高风险业务结构。
   - 目录树、重复接口清单、分析动作和旧 changelog 不迁移。
3. 逐字保留 `<!-- manual: keep -->` 块。没有保护标记但明显属于人工规则/事故结论的内容，先包进保护块。
4. 同一结论冲突时不要择一：创建 `[CONFLICT][conflict]`，把目标文件设为 `status: conflict`。
5. 不迁移旧 Graph 或 Mermaid 节点。按新版定义从源码重新生成 `<map-root>/next/graphs/*.yaml`，再用 `render_graph` 派生视图。
6. 旧 Markdown 结论没有可靠证据时只列入待核对清单，不写进新版事实；不要为了迁移通过校验伪造 `current`。
7. 更新已有 `AGENTS.md`、`CLAUDE.md` 等入口中的旧路径，使其只引用新 L1。
8. 运行 `check_map.sh --root <项目根> --age` 和 `build_views --root <项目根>`，确认目标完整后再用 `--remove-legacy` 删除旧文件。旧 `.map/` 若已被项目 Git 跟踪，删除需在项目仓库单独提交。

Git 已保存旧版本，不创建 `.bak`。若旧文件未纳入 Git，迁移前不得删除其中无法重建的人工内容。
