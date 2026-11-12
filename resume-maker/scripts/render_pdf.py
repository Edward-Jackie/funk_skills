#!/usr/bin/env python3
"""
简历 PDF 渲染脚本
将 Markdown 格式的简历通过 HTML 模板转换为 PDF

依赖：
    pip install weasyprint jinja2 python-frontmatter markdown

用法：
    python render_pdf.py --input resume.md --template classic --output resume.pdf
    python render_pdf.py --input resume.md --template classic --output resume.html --preview
"""

import argparse
import sys
from pathlib import Path

try:
    import frontmatter
    from jinja2 import Environment, FileSystemLoader
    from markdown import markdown
except ImportError as e:
    print(f"缺少依赖: {e}")
    print("请运行: pip install jinja2 python-frontmatter markdown")
    sys.exit(1)

# WeasyPrint 是可选的，只在生成 PDF 时需要
WEASYPRINT_AVAILABLE = False
try:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    # OSError 可能是缺少系统依赖（pango 等）
    pass


def parse_resume_markdown(content: str) -> dict:
    """
    解析 Markdown 简历内容为结构化数据

    支持的格式：
    # 基本信息
    - 姓名：张三
    - 电话：13800138000

    # 工作经历
    ## 公司名 | 职位 | 2022.06 - 至今
    - 职责1
    - 职责2
    """
    sections = {}
    current_section = None
    current_subsection = None

    lines = content.strip().split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # 一级标题：section
        if line.startswith('# '):
            current_section = line[2:].strip()
            sections[current_section] = []
            current_subsection = None

        # 二级标题：subsection
        elif line.startswith('## '):
            current_subsection = line[3:].strip()
            if current_section:
                sections[current_section].append({
                    'title': current_subsection,
                    'content': []
                })

        # 列表项
        elif line.startswith('- ') and current_section:
            item = line[2:].strip()
            if current_subsection and sections[current_section]:
                sections[current_section][-1]['content'].append(item)
            else:
                # 直接挂在 section 下的列表项（如基本信息）
                if ':' in item or '：' in item:
                    # 键值对
                    sep = ':' if ':' in item else '：'
                    key, value = item.split(sep, 1)
                    if not sections[current_section]:
                        sections[current_section].append({})
                    if isinstance(sections[current_section][0], dict) and 'title' not in sections[current_section][0]:
                        sections[current_section][0][key.strip()] = value.strip()
                else:
                    if not sections[current_section]:
                        sections[current_section].append({'items': []})
                    if isinstance(sections[current_section][-1], dict) and 'items' in sections[current_section][-1]:
                        sections[current_section][-1]['items'].append(item)

        i += 1

    return sections


def render_html(sections: dict, template_name: str, templates_dir: Path) -> str:
    """使用 Jinja2 模板渲染 HTML"""
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False
    )

    template = env.get_template(f"{template_name}.html")
    return template.render(sections=sections)


def html_to_pdf(html_content: str, output_path: Path):
    """将 HTML 转换为 PDF"""
    if not WEASYPRINT_AVAILABLE:
        print("错误: WeasyPrint 未安装或系统依赖缺失")
        print("macOS 用户请先运行: brew install pango")
        print("然后运行: pip install weasyprint")
        print("\n或者使用 --preview 参数生成 HTML 预览")
        sys.exit(1)
    HTML(string=html_content).write_pdf(str(output_path))


def main():
    parser = argparse.ArgumentParser(description='将 Markdown 简历转换为 PDF')
    parser.add_argument('--input', '-i', required=True, help='输入的 Markdown 文件路径')
    parser.add_argument('--template', '-t', default='classic', help='模板名称 (classic/modern/minimal)')
    parser.add_argument('--output', '-o', required=True, help='输出文件路径 (.pdf 或 .html)')
    parser.add_argument('--preview', action='store_true', help='只生成 HTML 预览，不转 PDF')

    args = parser.parse_args()

    # 路径处理
    input_path = Path(args.input)
    output_path = Path(args.output)
    script_dir = Path(__file__).parent
    templates_dir = script_dir.parent / 'assets' / 'templates'

    # 检查输入文件
    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}")
        sys.exit(1)

    # 检查模板
    template_file = templates_dir / f"{args.template}.html"
    if not template_file.exists():
        print(f"错误: 模板不存在: {template_file}")
        print(f"可用模板: {', '.join(f.stem for f in templates_dir.glob('*.html'))}")
        sys.exit(1)

    # 读取并解析 Markdown
    content = input_path.read_text(encoding='utf-8')
    sections = parse_resume_markdown(content)

    # 渲染 HTML
    html_content = render_html(sections, args.template, templates_dir)

    # 输出
    if args.preview or output_path.suffix == '.html':
        output_path = output_path.with_suffix('.html')
        output_path.write_text(html_content, encoding='utf-8')
        print(f"HTML 预览已生成: {output_path}")
    else:
        output_path = output_path.with_suffix('.pdf')
        html_to_pdf(html_content, output_path)
        print(f"PDF 已生成: {output_path}")


if __name__ == '__main__':
    main()
