#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""show_question 结果落盘：把用户粘贴回来的问卷答案追加存档，支持多轮合并。

用法：
    python3 archive.py "<问卷标题>" answer.json
    python3 archive.py "<问卷标题>"        # 从 stdin 读 JSON（粘贴后管道）

存档目录默认 ~/Desktop/问卷存档/，同名问卷所有轮次收进一个数组文件：
    ~/Desktop/问卷存档/<问卷标题>.json        # 数组，每轮一条，带"建档批次"
    ~/Desktop/问卷存档/<问卷标题>.csv         # 汇总表（可选，--csv 生成）
"""
import json, os, sys, csv, datetime

ARCHIVE_DIR = os.path.expanduser("~/Desktop/问卷存档")
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def now_tag():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def load_answers(arg):
    """从参数里的文件路径读，或从 stdin 读。"""
    if arg and os.path.exists(arg):
        with open(arg, encoding="utf-8") as fh:
            return json.load(fh)
    data = sys.stdin.read().strip()
    if not data:
        print("错误：没有输入内容", file=sys.stderr)
        sys.exit(1)
    return json.loads(data)


def append_to_archive(title, answers):
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    safe = title.replace("/", "_").replace("\\", "_")
    path = os.path.join(ARCHIVE_DIR, safe + ".json")

    # 已有存档则读出来，追加本轮
    records = []
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                records = json.load(fh)
        except Exception:
            records = []

    rec = dict(answers)
    rec["建档批次"] = now_tag()
    records.append(rec)

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)
    return path, records


def write_csv(title, records):
    """把已归档的多轮结果汇总成横表 CSV（键对齐，缺的留空）。"""
    safe = title.replace("/", "_").replace("\\", "_")
    path = os.path.join(ARCHIVE_DIR, safe + ".csv")
    # 收集所有键（含"建档批次"），多轮并集
    keys = []
    for rec in records:
        for k in rec:
            if k not in keys:
                keys.append(k)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec.get(k, "") for k in keys})
    return path


def main():
    if len(sys.argv) < 2:
        print("用法: python3 archive.py \"<问卷标题>\" [answer.json]  [--csv]", file=sys.stderr)
        sys.exit(1)
    title = sys.argv[1]
    json_arg = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    make_csv = "--csv" in sys.argv

    answers = load_answers(json_arg)
    path, records = append_to_archive(title, answers)
    print("已存档: %s（累计 %d 份）" % (path, len(records)))

    if make_csv:
        csv_path = write_csv(title, records)
        print("已汇总: %s" % csv_path)


if __name__ == "__main__":
    main()