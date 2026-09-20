#!/usr/bin/env python3
"""
单张图片反推 prompt。

用法：
    export IMAGE_API_KEY=sk-xxx
    python3 analyze.py --image ref.png
    python3 analyze.py --image ref.png --out result.json
    python3 analyze.py --image ref.png --platform mj --platform sd

依赖：无（仅标准库）
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = os.environ.get("IMAGE_API_BASE", "https://api.openai.com/v1")
DEFAULT_MODEL = os.environ.get("IMAGE_API_MODEL", "gpt-5")

# ---------------------------------------------------------------- 契约一：字段字典
SYSTEM_PROMPT = """你是图像逆向工程专家。任务：把输入图片拆解成结构化字段，供后续不同生图模型使用。

输出格式（最重要，先看这条）：
每个字段一行，格式严格为：[字段名] 中文描述 | English description
每个字段的竖线左右两侧都必须有内容，缺一侧算不合格。
多个描述点用 / 分隔，不要用逗号或顿号。

正确示例：
[光照] 左上方主光 / 色温偏冷 / 柔光 | key light from upper left / cool color temperature / soft diffused light

铁律：
1. 只描述你在图中真实看到的内容。看不清、不确定的字段一律写 unknown。
2. 禁止推测、补全、美化。不要出现「可能」「大概」「似乎」这类词。
3. 英文要地道，用生图模型习惯的术语（如 shallow depth of field、rim light）。
4. 画面内的文字必须逐字照抄，保持原语言，绝对不要翻译，也不需要给英文版。
5. 不要输出 markdown 标题、表格、代码块或任何额外解释。

字段：
[主体] 数量 / 姿态 / 朝向 / 材质 / 表情或状态
[构图] 镜头焦段感 / 视角 / 主体位置与画面占比 / 景深
[光照] 光源方向 / 色温 / 软硬 / 有无轮廓光
[色彩] 主色板色值（给七个十六进制）/ 对比度 / 饱和度倾向
[风格] 媒介类型 / 流派或参考 / 质感
[技术] 清晰度 / 噪点 / 胶片颗粒 / 长宽比
[文字] 逐字照抄原文，没有则写 none
[一句话总述] 不超过 40 字"""


# ---------------------------------------------------------------- 图片处理
def encode_image(path, max_edge=768, quality=70):
    """读图并转 base64。原图可能很大，压到长边 768 足够识别。"""
    with open(path, "rb") as f:
        raw = f.read()

    mime = "image/png"
    if path.lower().endswith((".jpg", ".jpeg")):
        mime = "image/jpeg"
    elif path.lower().endswith(".webp"):
        mime = "image/webp"

    # 有 Pillow 就压；没有就直接用原图（但注意请求体会很大）
    try:
        import io

        from PIL import Image

        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "LA", "P"):
            # 透明区合成到白底，否则会被压成纯黑污染色板
            bg = Image.new("RGB", img.size, (255, 255, 255))
            img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        if max(w, h) > max_edge:
            scale = max_edge / float(max(w, h))
            img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        raw = buf.getvalue()
        mime = "image/jpeg"
    except ImportError:
        pass  # 没有 Pillow，原图直传

    return base64.b64encode(raw).decode(), mime


def iter_pixels(img):
    """Pillow 14 起 getdata 被弃用，这里做兼容。"""
    fn = getattr(img, "get_flattened_data", None)
    return fn() if callable(fn) else img.getdata()


def sample_palette(path, count=6):
    """
    从原图像素采样主色。模型报的色值是编的，真实色板只能算出来。
    有 Pillow 才可用；没有则返回空列表，渲染时回退到模型描述。
    """
    try:
        import collections

        from PIL import Image
    except ImportError:
        return []

    try:
        img = Image.open(path)
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")

        img.thumbnail((96, 96))
        buckets = collections.defaultdict(lambda: [0, 0, 0, 0])
        for r, g, b in iter_pixels(img):
            k = (r >> 4, g >> 4, b >> 4)
            cell = buckets[k]
            cell[0] += 1
            cell[1] += r
            cell[2] += g
            cell[3] += b

        items = sorted(buckets.values(), key=lambda c: -c[0])
        out = []
        for n, sr, sg, sb in items:
            if len(out) >= count:
                break
            r, g, b = sr // n, sg // n, sb // n
            # 合并肉眼难分的近色，避免输出六个几乎一样的蓝
            if any(abs(r - o[0]) + abs(g - o[1]) + abs(b - o[2]) < 42 for o in out):
                continue
            out.append((r, g, b))
        return ["#%02X%02X%02X" % c for c in out]
    except Exception:
        return []


# ---------------------------------------------------------------- 调用
def call_vision(image_path, base, model, key, timeout=180):
    b64, mime = encode_image(image_path)
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": SYSTEM_PROMPT},
                {"type": "image_url", "image_url": {"url": "data:%s;base64,%s" % (mime, b64)}},
            ],
        }],
        # 实测推理会吃掉大半输出预算，给足
        "max_tokens": 1500,
        "temperature": 0.1,
        "stream": False,
    }

    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:400]
        raise SystemExit("接口返回 HTTP %s：%s" % (e.code, body))
    except urllib.error.URLError as e:
        raise SystemExit(
            "网络请求失败：%s\n"
            "如果报 CONNECT aborted，是系统代理掐断了连接，"
            "试试 unset HTTPS_PROXY 或直接跑 curl --noproxy '*'。" % e.reason
        )

    choices = data.get("choices") or []
    if not choices:
        raise SystemExit("返回里没有 choices：" + json.dumps(data, ensure_ascii=False)[:400])

    msg = choices[0].get("message") or {}
    content = msg.get("content", "")
    if isinstance(content, list):
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content, data.get("usage", {})


# ---------------------------------------------------------------- 契约三：解析（容错优先）
def parse_fields(text):
    out, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^\s*[\[【]\s*([^\]】]+?)\s*[\]】]\s*(.*)$", line)
        if m:
            if cur:
                out.append(cur)
            cur = {"k": m.group(1).strip(), "v": m.group(2).strip()}
        elif cur and line.strip():
            cur["v"] += " " + line.strip()
    if cur:
        out.append(cur)
    return out


def split_bilingual(v):
    parts = re.split(r"\s*[|｜]\s*", v)
    if len(parts) >= 2:
        return parts[0].strip(), " ".join(parts[1:]).strip()
    whole = parts[0].strip()
    return whole, whole  # 没给分隔符就整段通用，保证不为空


def split_values(v):
    return [s.strip().rstrip("。，,;；") for s in re.split(r"\s*[\/／]\s*", v) if s.strip()]


def pick(fields, keys, lang):
    res = []
    for f in fields:
        for k in keys:
            if k in f["k"]:
                cn, en = split_bilingual(f["v"])
                res.extend(split_values(en if lang == "en" else cn))
                break
    return res


def raw_value(fields, key):
    # [文字] 按约定不翻译、不拆竖线，否则原文会被切碎
    for f in fields:
        if key in f["k"]:
            return f["v"].strip()
    return ""


_EMPTY_WORDS = ("none", "无", "没有", "unknown", "空", "n/a", "na")


def _dedupe_text(parts):
    """
    去掉重复与包含关系。模型常把同一句话写成中英两版，
    或者一端带上下文（招牌「营业中」）另一端只是原词（营业中）——
    后者应被前者吸收，否则会拼出啰嗦的双份。
    """
    out = []
    for p in parts:
        if any(p in o or o in p for o in out):
            # 保留信息更全的那一份
            for i, o in enumerate(out):
                if p in o:
                    break
                if o in p:
                    out[i] = p
                    break
            continue
        out.append(p)
    return out


def text_field(fields):
    """
    取画面内文字。模型可能写成 "none"、"none | none"、"无 | none" 等各种形态，
    所以拆开竖线后逐段判空——任一段是实义内容才算有文字。
    """
    v = raw_value(fields, "文字")
    if not v:
        return ""
    parts = [p.strip() for p in re.split(r"\s*[|｜]\s*", v) if p.strip()]
    real = [p for p in parts if p.lower() not in _EMPTY_WORDS]
    if not real:
        return ""
    out = _dedupe_text(real)
    return " | ".join(out) if len(out) > 1 else out[0]


def aspect_of(fields):
    t = " ".join(pick(fields, ["技术"], "en")) + " " + " ".join(pick(fields, ["技术"], "cn"))
    m = re.search(r"(\d+\s*[:：]\s*\d+)", t)
    if not m:
        return ""
    p = re.sub(r"\s", "", m.group(1).replace("：", ":")).split(":")
    if len(p) != 2 or int(p[0]) == 0 or int(p[1]) == 0:
        return ""
    return "%d:%d" % (int(p[0]), int(p[1]))


def hexes_of(fields, measured):
    # 优先用像素采样的真实色板，模型报的只作兜底
    if measured:
        return measured
    t = " ".join(pick(fields, ["色彩"], "cn")) + " " + " ".join(pick(fields, ["色彩"], "en"))
    found = re.findall(r"#[0-9A-Fa-f]{6}\b", t)
    seen, out = set(), []
    for h in found:
        hl = h.upper()
        if hl not in seen:
            seen.add(hl)
            out.append(hl)
    return out


# ---------------------------------------------------------------- 平台渲染
def render_en(fields, measured):
    parts = [", ".join(pick(fields, [k], "en")) for k in ("主体", "构图", "风格", "光照", "技术")]
    parts = [p for p in parts if p]
    hexes = hexes_of(fields, measured)
    if hexes:
        parts.append("color palette " + " ".join(hexes))
    out = ", ".join(parts)
    if not out:
        return ""
    extra = ""
    t = text_field(fields)
    if t:
        extra += ' Text in image reads verbatim: "%s".' % t
    ar = aspect_of(fields)
    if ar:
        extra += " Aspect ratio %s." % ar
    return re.sub(r"\s+", " ", out + "." + extra).replace("..", ".").strip()


def render_zh(fields, measured):
    groups = [pick(fields, [k], "cn") for k in ("主体", "构图", "风格", "光照", "技术")]
    groups = [g for g in groups if g]
    out = "；".join("，".join(g) for g in groups)
    if not out:
        return ""
    hexes = hexes_of(fields, measured)
    if hexes:
        out += "；主色板 " + " ".join(hexes)
    out += "。"
    t = text_field(fields)
    if t:
        out += "画面内文字原文为「%s」，不要翻译。" % t
    ar = aspect_of(fields)
    if ar:
        out += "长宽比 %s。" % ar
    return out


def render_mj(fields, measured):
    body = re.sub(r"\.\s*$", "", render_en(fields, measured))
    body = re.sub(r"\.\s*Aspect ratio[^.]*\.?", "", body, flags=re.I)
    ar = aspect_of(fields)
    return body + (" --ar " + ar if ar else "") + " --style raw --q 2"


def render_sd(fields, measured):
    pos = []
    # 构图必须进正向词，SD 丢掉构图就废了
    for k in ("主体", "构图", "风格", "光照"):
        pos += pick(fields, [k], "en")
    hexes = hexes_of(fields, measured)
    if hexes:
        pos.append("color palette " + " ".join(hexes))
    pos.append("masterpiece, best quality, highly detailed")
    neg = ("blurry, lowres, jpeg artifacts, watermark, signature, deformed, "
           "extra limbs, extra fingers, bad anatomy, oversaturated, low contrast")
    if not text_field(fields):
        neg += ", text, letters, words, caption"
    return "PROMPT: " + ", ".join(p for p in pos if p) + "\n\nNEGATIVE: " + neg


def render_dalle(fields, measured):
    base = render_zh(fields, measured)
    if not base:
        return ""
    return "请生成一张图片。" + base + " 严格保持上述数量、位置关系和文字内容，不要自行增删元素。"


def render_jimeng(fields, measured):
    base = render_zh(fields, measured)
    if not base:
        return ""
    style = "，".join(pick(fields, ["风格"], "cn"))
    return base + (" 画面质感：" + style + "。" if style else "")


RENDERERS = {
    "en": render_en,
    "zh": render_zh,
    "mj": render_mj,
    "sd": render_sd,
    "dalle": render_dalle,
    "jimeng": render_jimeng,
}


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser(description="把图片反推成各家生图模型的 prompt")
    ap.add_argument("--image", required=True, help="参考图路径")
    ap.add_argument("--base", default=DEFAULT_BASE, help="接口 Base URL")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="多模态模型名")
    ap.add_argument("--key", default=os.environ.get("IMAGE_API_KEY", ""), help="API Key，默认读 IMAGE_API_KEY")
    ap.add_argument("--out", help="把结果写入 JSON 文件")
    ap.add_argument("--platform", action="append", default=[],
                    help="要渲染的平台，可重复：en / zh / mj / sd / dalle / jimeng")
    args = ap.parse_args()

    if not args.key:
        raise SystemExit("缺少 API Key。设置环境变量 IMAGE_API_KEY 或用 --key 传入。")
    if not os.path.exists(args.image):
        raise SystemExit("找不到图片：" + args.image)

    raw, usage = call_vision(args.image, args.base, args.model, args.key)
    fields = parse_fields(raw)
    measured = sample_palette(args.image)

    plats = args.platform or ["en", "mj", "sd"]
    rendered = {}
    for p in plats:
        fn = RENDERERS.get(p)
        if fn:
            rendered[p] = fn(fields, measured)

    result = {
        "image": os.path.abspath(args.image),
        "model": args.model,
        "palette_measured": measured,
        "fields": fields,
        "rendered": rendered,
        "raw": raw,
        "usage": usage,
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("已写入 " + args.out)
    else:
        print("=" * 70)
        print("结构化字段")
        print("=" * 70)
        for f in fields:
            print("  [%s] %s" % (f["k"], f["v"]))
        if measured:
            print("\n原图采样主色：" + " ".join(measured))
        for p in plats:
            if rendered.get(p):
                print("\n" + "=" * 70)
                print(p)
                print("=" * 70)
                print(rendered[p])


if __name__ == "__main__":
    main()
