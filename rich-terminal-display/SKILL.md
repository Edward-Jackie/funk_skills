---
name: rich-terminal-display
description: |
  把结构化信息（方案对比、诊断结果、多选项列表、层级结构）渲染成终端表格/面板/树形结构，
  而不是用纯 Markdown 文字堆砌。当回复里出现"对比几个方案""列一下诊断结果""这几个选项
  哪个好""层级关系是什么样的"这类结构化内容时，优先用这个 Skill 渲染，再在文字里做简短说明。
  不要用于纯叙述性说明、单一事实陈述，或已经有专门上报工具的场景（例如代码审查发现）。
trigger: /rich_display
---

# Rich 终端展示

用 Python `rich` 库把结构化信息渲染成终端表格 / 面板 / 树形结构。通过 `uv run --with rich`
临时安装运行，不需要装进任何项目的依赖环境，用完即走。

## 什么时候用

- 需要对比多个方案/版本（每个方案在同一组维度上取值） → 用 `table`
- 需要突出一段结论、警告或"怎么做到的"说明 → 用 `panel`
- 需要展示层级/目录/调用关系 → 用 `tree`
- 纯叙述性文字、单一事实、已有专门工具处理的内容（如 code review 用 `ReportFindings`）不要用这个

## 怎么调用

**优先用文件传参，不要用 `echo | stdin`**——实测 `echo '<json>'` 传多行/带 `\n` 转义的内容时，
Bash 工具会把里面的 `\n` 转成真实换行符，写进字符串值内部会导致 JSON 解析失败
（`Invalid control character`）。用 Write 工具把 JSON 落一个临时文件，再传路径最稳：

```bash
uv run --with rich python scripts/render.py data.json
```

### table

```json
{
  "kind": "table",
  "title": "标题",
  "columns": ["列1", "列2"],
  "rows": [["值1", "值2"], ["值3", "值4"]],
  "highlight_row": 2
}
```

`highlight_row` 可选，从 1 开始计数，用来整行加粗高亮最终结论/推荐项。

### panel

```json
{
  "kind": "panel",
  "title": "标题",
  "body": "正文，支持 rich 标记如 [bold]...[/bold] [green]...[/green]",
  "border_style": "cyan"
}
```

### tree

```json
{
  "kind": "tree",
  "label": "根节点",
  "children": [
    {"label": "子节点1", "children": [{"label": "孙节点"}]},
    {"label": "子节点2"}
  ]
}
```

## 原则

1. **先渲染，再总结**：先把结构化内容用表格/面板/树跑出来，正文里只做一两句话的简短说明，
   不要在文字里把表格内容再复述一遍。
2. **JSON 是一次性拼的，不要求预先落盘**：直接在 Bash 调用里内联 JSON 即可，不需要每次都建文件。
3. **列数据用真实内容，不用占位符**：标题、列名、结论都要来自当前对话的真实上下文。
