#!/usr/bin/env python3
"""
批量给图片打标，输出 JSONL。适合给 LoRA 数据集生成 caption。

用法：
    export IMAGE_API_KEY=sk-xxx
    python3 batch.py --dir ./images --out ./captions.jsonl
    python3 batch.py --dir ./images --platform en --workers 4

断点续跑：已处理的图片会跳过，重新跑不会重复请求。
"""

import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyze import (  # noqa: E402
    RENDERERS,
    call_vision,
    parse_fields,
    sample_palette,
)

EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
_print_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(msg, file=sys.stderr, flush=True)


def list_images(d):
    out = []
    for root, _, files in os.walk(d):
        for name in sorted(files):
            if name.lower().endswith(EXTS):
                out.append(os.path.join(root, name))
    return out


def load_done(path):
    """读已有的 JSONL，拿到已处理的图片路径，用于断点续跑。"""
    done = set()
    if not os.path.exists(path):
        return done
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["image"])
            except (ValueError, KeyError):
                continue
    return done


def process(path, args):
    raw, usage = call_vision(path, args.base, args.model, args.key)
    fields = parse_fields(raw)
    measured = sample_palette(path)
    rendered = {}
    for p in args.platform:
        fn = RENDERERS.get(p)
        if fn:
            rendered[p] = fn(fields, measured)
    return {
        "image": os.path.abspath(path),
        "fields": fields,
        "palette_measured": measured,
        "rendered": rendered,
        "usage": usage,
    }


def main():
    ap = argparse.ArgumentParser(description="批量反推 prompt")
    ap.add_argument("--dir", required=True, help="图片目录，会递归扫描")
    ap.add_argument("--out", required=True, help="输出 JSONL 路径")
    ap.add_argument("--base", default=os.environ.get("IMAGE_API_BASE", "https://api.openai.com/v1"))
    ap.add_argument("--model", default=os.environ.get("IMAGE_API_MODEL", "gpt-5"))
    ap.add_argument("--key", default=os.environ.get("IMAGE_API_KEY", ""))
    ap.add_argument("--platform", action="append", default=[],
                    help="要渲染的平台，可重复。默认只出 en")
    ap.add_argument("--workers", type=int, default=3, help="并发数，默认 3。别开太高，容易触发限流")
    args = ap.parse_args()

    if not args.key:
        raise SystemExit("缺少 API Key。设置环境变量 IMAGE_API_KEY 或用 --key 传入。")
    if not args.platform:
        args.platform = ["en"]

    images = list_images(args.dir)
    if not images:
        raise SystemExit("目录里没找到图片：" + args.dir)

    done = load_done(args.out)
    todo = [p for p in images if os.path.abspath(p) not in done]

    log("共 %d 张，已完成 %d 张，待处理 %d 张" % (len(images), len(done), len(todo)))
    if not todo:
        return

    # 追加模式，配合断点续跑
    mode = "a" if done else "w"
    ok = fail = 0

    with open(args.out, mode, encoding="utf-8") as out_f, \
            ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process, p, args): p for p in todo}
        for i, fut in enumerate(as_completed(futures), 1):
            path = futures[fut]
            try:
                rec = fut.result()
                out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out_f.flush()
                ok += 1
                log("[%d/%d] ok  %s" % (i, len(todo), os.path.basename(path)))
            except Exception as e:
                fail += 1
                log("[%d/%d] FAIL %s — %s" % (i, len(todo), os.path.basename(path), str(e)[:160]))

    log("完成：成功 %d，失败 %d。输出 %s" % (ok, fail, args.out))
    if fail:
        log("失败的图再跑一次本命令即可，已成功的会跳过。")


if __name__ == "__main__":
    main()
