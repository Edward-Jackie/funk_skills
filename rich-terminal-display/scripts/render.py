"""结构化信息 -> 终端表格/面板/树形结构渲染器。

用法：
    echo '<json>' | uv run --with rich python render.py
    uv run --with rich python render.py data.json

输入 JSON 的 "kind" 字段决定渲染方式：table / panel / tree。

table 示例：
{
  "kind": "table",
  "title": "标题",
  "columns": ["列1", "列2"],
  "rows": [["值1", "值2"], ["值3", "值4"]],
  "highlight_row": 2   # 可选，从 1 开始，整行加粗高亮（用于标出结论/推荐项）
}

panel 示例：
{
  "kind": "panel",
  "title": "标题",
  "body": "正文，支持 rich 的 [bold]...[/bold] 标记",
  "border_style": "cyan"
}

tree 示例：
{
  "kind": "tree",
  "label": "根节点",
  "children": [
    {"label": "子节点1", "children": [{"label": "孙节点"}]},
    {"label": "子节点2"}
  ]
}
"""
import json
import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

console = Console()


def render_table(data):
    table = Table(title=data.get("title"), show_lines=True)
    for col in data["columns"]:
        table.add_column(col, style="white")

    highlight = data.get("highlight_row")
    for i, row in enumerate(data["rows"], start=1):
        style = "bold green" if i == highlight else None
        table.add_row(*[str(cell) for cell in row], style=style)

    console.print()
    console.print(table)
    console.print()


def render_panel(data):
    console.print()
    console.print(Panel(
        data["body"],
        title=data.get("title"),
        border_style=data.get("border_style", "cyan"),
    ))
    console.print()


def render_tree(data):
    def build(node, tree):
        for child in node.get("children", []):
            branch = tree.add(child["label"])
            build(child, branch)

    root = Tree(data["label"])
    build(data, root)
    console.print()
    console.print(root)
    console.print()


RENDERERS = {"table": render_table, "panel": render_panel, "tree": render_tree}


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    kind = data.get("kind")
    renderer = RENDERERS.get(kind)
    if renderer is None:
        console.print(f"[bold red]未知的 kind: {kind!r}，支持 table / panel / tree[/bold red]")
        sys.exit(1)
    renderer(data)


if __name__ == "__main__":
    main()
