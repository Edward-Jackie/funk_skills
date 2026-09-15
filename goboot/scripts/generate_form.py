#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GoBoot 本地决策表生成器。

用法：
    python3 generate_form.py intake.json --level standard --output goboot.html

不传输出路径时，默认输出到配置文件同目录下的同名 HTML。
"""
import argparse
import json
import sys
import os

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(SKILL_DIR, "..", "assets", "form-template.html")


def esc(v):
    """HTML 属性转义，防止注入破坏结构。"""
    if not isinstance(v, str):
        v = json.dumps(v, ensure_ascii=False)
    return (v.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def fieldset_html(idx, f):
    """单个题目(field)生成一个 fieldset 块。"""
    key = f.get("key", "问题%d" % idx)
    ftype = f.get("type", "text")
    title = f.get("title", key)
    required = f.get("required", False)
    name = "q-%s" % key

    attrs = ['data-key="%s"' % esc(key), 'data-type="%s"' % esc(ftype)]
    if required:
        attrs.append('data-required="true"')
    if f.get("showWhen"):
        # 条件逻辑：如 [{"key":"性别","value":"女"}]
        cond = json.dumps(f["showWhen"], ensure_ascii=False)
        # HTML 属性用单引号包裹，内部双引号合法；单引号转成实体
        attrs.append("data-show-when='%s'" % cond.replace("'", "&#39;"))

    req_mark = '<span class="req">*</span>' if required else ""
    parts = ['<fieldset %s>' % " ".join(attrs)]
    parts.append('  <p class="qtitle">%s%s</p>' % (esc(title), req_mark))

    # ---- 主体控件 ----
    if ftype == "text":
        ph = f.get("placeholder", "")
        parts.append('  <input type="text" placeholder="%s" autocomplete="off">' % esc(ph))
    elif ftype == "textarea":
        ph = f.get("placeholder", "")
        parts.append('  <textarea placeholder="%s" rows="%s"></textarea>' % (esc(ph), f.get("rows", 3)))
    elif ftype in ("radio", "checkbox"):
        t = "radio" if ftype == "radio" else "checkbox"
        parts.append('  <div class="choice-row">')
        for opt in f.get("options", []):
            parts.append('    <label><input type="%s" name="%s" value="%s" data-choice> %s</label>'
                         % (t, esc(name), esc(opt), esc(opt)))
        if f.get("other"):
            parts.append('    <label><input type="%s" name="%s" value="其他" data-other-choice> 其他</label>'
                         % (t, esc(name)))
        parts.append('  </div>')
    elif ftype == "range":
        lo, hi = f.get("min", 1), f.get("max", 10)
        val = f.get("value", (lo + hi) // 2)
        parts.append('  <div class="range-row">')
        parts.append('    <input type="range" min="%s" max="%s" value="%s" data-range>' % (lo, hi, val))
        parts.append('    <span class="range-val" data-range-val>%s</span>' % val)
        parts.append('  </div>')
    elif ftype == "select":
        parts.append('  <select>')
        parts.append('    <option value="">请选择</option>')
        for opt in f.get("options", []):
            parts.append('    <option value="%s">%s</option>' % (esc(opt), esc(opt)))
        parts.append('  </select>')
    elif ftype == "matrix":
        rows = f.get("rows", [])
        cols = f.get("cols", [])
        parts.append('  <table class="matrix">')
        parts.append('    <thead><tr><th></th>')
        for c in cols:
            parts.append('      <th>%s</th>' % esc(c))
        parts.append('    </tr></thead>')
        parts.append('    <tbody>')
        for r in rows:
            parts.append('      <tr data-matrix-row="%s"><td>%s</td>' % (esc(r), esc(r)))
            for c in cols:
                parts.append('        <td><input type="radio" name="%s-%s" value="%s"></td>'
                             % (esc(name), esc(r), esc(c)))
            parts.append('      </tr>')
        parts.append('    </tbody></table>')

    # ---- 更多选项 ----
    parts.append('  <details class="more">')
    parts.append('    <summary>更多选项</summary>')
    parts.append('    <div class="more-body">')
    parts.append('      <label class="more-row"><input type="checkbox" data-skip> 跳过此题</label>')
    if ftype in ("radio", "checkbox") and f.get("other"):
        parts.append('      <div class="more-row other-input" hidden>')
        parts.append('        <span>自己填：</span>')
        parts.append('        <input type="text" data-other-text placeholder="填你的答案">')
        parts.append('      </div>')
    parts.append('      <div class="more-row note-input">')
    parts.append('        <span>补充说明：</span>')
    parts.append('        <textarea data-note placeholder="对这道题有什么要补充的"></textarea>')
    parts.append('      </div>')
    parts.append('    </div>')
    parts.append('  </details>')
    parts.append('</fieldset>')
    return "\n".join(parts)


def build_form(cfg):
    """按配置生成表单体（含题组分组）。"""
    groups = cfg.get("groups", [{"name": "", "fields": cfg.get("fields", [])}])
    blocks = []
    idx = 0
    for g in groups:
        fields = g.get("fields", [])
        if not fields:
            continue
        if g.get("name"):
            blocks.append('<div class="group-title">%s</div>' % esc(g["name"]))
        blocks.append('<div class="group">')
        for f in fields:
            idx += 1
            blocks.append(fieldset_html(idx, f))
        blocks.append('</div>')
    return "\n".join(blocks)


def render(cfg):
    with open(TEMPLATE, encoding="utf-8") as fh:
        html = fh.read()
    return (html
            .replace("{{TITLE}}", esc(cfg.get("title", "问卷")))
            .replace("{{KICKER}}", esc(cfg.get("kicker", "")))
            .replace("{{DEK}}", esc(cfg.get("dek", "")))
            .replace("{{FORM_FIELDS}}", build_form(cfg)))


def filter_level(cfg, level):
    """按问诊深度筛选题目。"""
    result = dict(cfg)
    result["groups"] = []
    for group in cfg.get("groups", []):
        fields = [f for f in group.get("fields", [])
                  if level in f.get("levels", ["quick", "standard", "deep"])]
        if fields:
            item = dict(group)
            item["fields"] = fields
            result["groups"].append(item)
    result["kicker"] = "%s · %s" % (cfg.get("kicker", "本地决策表"), {
        "quick": "快速版",
        "standard": "标准版",
        "deep": "深入版",
    }[level])
    return result


def main():
    parser = argparse.ArgumentParser(description="生成 GoBoot 本地项目决策表")
    parser.add_argument("config", help="问卷 JSON 配置路径")
    parser.add_argument("--level", choices=("quick", "standard", "deep"),
                        default="standard", help="问诊深度，默认 standard")
    parser.add_argument("--output", "-o", help="输出 HTML 路径")
    args = parser.parse_args()

    cfg_path = args.config
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    out = args.output if args.output else (
        os.path.splitext(cfg_path)[0] + ".html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(filter_level(cfg, args.level)))
    print("已生成: %s" % out)


if __name__ == "__main__":
    main()
