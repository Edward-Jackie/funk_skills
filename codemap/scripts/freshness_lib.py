"""Codemap 新鲜度计算：L1/L2 元数据、Graph 元数据与锚点统一在这里推导。

check_map.sh --age、query_graph、impact_diff 和 MCP 共用同一份逻辑，避免各自算一套。
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "codemap.freshness/v1"
LEVELS = ("fresh", "aging", "needs-review", "stale", "conflict")
SEVERITY = {level: index for index, level in enumerate(LEVELS)}
AGING_COMMITS = 20
AGING_DAYS = 14

META_RE = re.compile(r"<!--\s*codemap-meta\s*(.*?)-->", re.S)
ANCHOR_RE = re.compile(r"`([^`\n]+?)\s+->\s+([^`\n]+?)`")
SIMPLE_SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PLACEHOLDER_RE = re.compile(r"[{}*<> ]|->|/$")
CONFIG_SUFFIXES = {".sql", ".yaml", ".yml", ".json", ".toml"}
SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Anchor:
    path: str
    symbol: str
    source: str
    commit: str


@dataclass
class Entry:
    kind: str
    id: str
    path: str
    status: str
    verified_at: str
    verified_commit: str
    head_ahead_commits: int | None = None
    verified_age_days: int | None = None
    stale_anchors: int = 0
    missing_anchors: int = 0
    degraded_anchors: int = 0
    anchor_count: int = 0
    issue_anchors: int = 0
    conflicts: int = 0
    level: str = "fresh"
    reasons: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.reasons is None:
            self.reasons = []

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "id": self.id,
            "path": self.path,
            "status": self.status,
            "verified_at": self.verified_at,
            "verified_commit": self.verified_commit,
            "head_ahead_commits": self.head_ahead_commits,
            "verified_age_days": self.verified_age_days,
            "stale_anchors": self.stale_anchors,
            "missing_anchors": self.missing_anchors,
            "degraded_anchors": self.degraded_anchors,
            "anchor_count": self.anchor_count,
            "issue_anchors": self.issue_anchors,
            "conflicts": self.conflicts,
            "level": self.level,
            "reasons": self.reasons,
        }


def git(root: Path, *args: str, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=timeout,
    )


def find_root(path: Path) -> Path:
    probe = path if path.is_dir() else path.parent
    result = git(probe, "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else Path.cwd().resolve()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def meta_value(text: str, key: str) -> str:
    match = META_RE.search(text)
    if not match:
        return ""
    for line in match.group(1).splitlines():
        name, sep, value = line.partition(":")
        if sep and name.strip() == key:
            return value.strip()
    return ""


def relative(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def commit_info(root: Path, commit: str, now: datetime) -> tuple[int | None, int | None, bool]:
    """返回 (领先提交数, 基线距今天数, commit 是否有效)。"""
    if not commit:
        return None, None, False
    check = git(root, "cat-file", "-e", f"{commit}^{{commit}}")
    if check.returncode != 0:
        return None, None, False
    counted = git(root, "rev-list", "--count", f"{commit}..HEAD")
    ahead = int(counted.stdout.strip()) if counted.returncode == 0 and counted.stdout.strip().isdigit() else None
    stamped = git(root, "show", "-s", "--format=%ct", commit)
    age = None
    if stamped.returncode == 0 and stamped.stdout.strip().isdigit():
        age = max(0, int((now - datetime.fromtimestamp(int(stamped.stdout.strip()), timezone.utc)).days))
    return ahead, age, True


def map_anchors(text: str, source: str, commit: str) -> list[Anchor]:
    result: list[Anchor] = []
    for path, symbol in ANCHOR_RE.findall(text):
        path, symbol = path.strip(), symbol.strip()
        if not path or PLACEHOLDER_RE.search(path):
            continue
        result.append(Anchor(path, symbol, source, commit))
    return result


def graph_anchors(graph: dict[str, Any], source: str, commit: str) -> list[Anchor]:
    result: list[Anchor] = []
    for group in ("nodes", "edges"):
        for item in graph.get(group, []) or []:
            if not isinstance(item, dict):
                continue
            for ref in item.get("refs", []) or []:
                if isinstance(ref, dict) and isinstance(ref.get("path"), str) and ref["path"].strip():
                    result.append(
                        Anchor(ref["path"].strip(), str(ref.get("symbol") or "").strip(), source, commit)
                    )
    return result


def symbol_state(root: Path, anchor: Anchor, deep: bool) -> str:
    """present | missing | degraded。degraded 表示只有普通引用或无法机械验证。"""
    target = root / anchor.path
    if not target.is_file():
        return "missing"
    symbol = anchor.symbol
    if not symbol or symbol == "-":
        return "present"
    text = read_text(target)
    if not text:
        return "missing"
    if target.suffix in CONFIG_SUFFIXES:
        return "present" if symbol in text else "missing"
    if not deep:
        return "present" if symbol in text else "missing"
    if SIMPLE_SYMBOL_RE.fullmatch(symbol):
        where = SCRIPT_DIR / "where.sh"
        if where.is_file():
            proc = subprocess.run(
                [str(where), str(target), symbol],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            hits = [
                line
                for line in proc.stdout.splitlines()
                if re.match(r"^\d+:", line) and not line.startswith("(no definition match")
            ]
            if hits:
                return "present"
            return "degraded" if symbol in text else "missing"
        return "degraded"
    return "present" if symbol in text else "missing"


def changed_paths(root: Path, commit: str, cache: dict[str, set[str]]) -> set[str]:
    if commit not in cache:
        result = git(root, "diff", "--name-only", commit, "--")
        cache[commit] = {line.strip() for line in result.stdout.splitlines() if line.strip()} if result.returncode == 0 else set()
    return cache[commit]


def check_anchors(
    root: Path,
    anchors: list[Anchor],
    entries: dict[str, Entry],
    deep: bool,
    cache: dict[str, set[str]],
) -> None:
    seen: set[tuple[str, str, str]] = set()
    for anchor in anchors:
        key = (anchor.source, anchor.path, anchor.symbol)
        if key in seen:
            continue
        seen.add(key)
        entry = entries.get(anchor.source)
        if entry is None:
            continue
        entry.anchor_count += 1
        issue = False
        state = symbol_state(root, anchor, deep)
        if state == "missing":
            entry.missing_anchors += 1
            issue = True
        elif state == "degraded":
            entry.degraded_anchors += 1
            issue = True
        if anchor.commit and anchor.path in changed_paths(root, anchor.commit, cache):
            entry.stale_anchors += 1
            issue = True
        if issue:
            entry.issue_anchors += 1


def entry_level(entry: Entry, commit_ok: bool) -> str:
    reasons = entry.reasons
    level = "fresh"

    def bump(candidate: str) -> None:
        nonlocal level
        if SEVERITY[candidate] > SEVERITY[level]:
            level = candidate

    if not commit_ok:
        reasons.append("verified-commit 不存在或为空")
        bump("stale")
    if entry.conflicts or entry.status == "conflict":
        if entry.conflicts:
            reasons.append(f"存在 {entry.conflicts} 条未决冲突")
        elif entry.status == "conflict":
            reasons.append("status=conflict")
        bump("conflict")
    if entry.status == "stale":
        reasons.append("status=stale")
        bump("stale")
    if entry.missing_anchors:
        reasons.append(f"{entry.missing_anchors} 条锚点文件或符号已失效")
        bump("stale")
    if entry.status == "needs-review":
        reasons.append("status=needs-review")
        bump("needs-review")
    if entry.stale_anchors:
        reasons.append(f"{entry.stale_anchors} 条锚点的证据文件在基线后变化")
        bump("needs-review")
    if entry.head_ahead_commits is not None and entry.head_ahead_commits > AGING_COMMITS:
        reasons.append(f"领先基线 {entry.head_ahead_commits} 个提交")
        bump("aging")
    if entry.verified_age_days is not None and entry.verified_age_days > AGING_DAYS:
        reasons.append(f"基线已 {entry.verified_age_days} 天")
        bump("aging")
    return level


def compute(
    root: Path,
    map_dir: Path,
    deep: bool = False,
    now: datetime | None = None,
    scan_anchors: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    map_dir = map_dir.resolve()
    now = now or datetime.now(timezone.utc)
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    cache: dict[str, set[str]] = {}
    entries: dict[str, Entry] = {}
    anchors: list[Anchor] = []

    for path in sorted(map_dir.glob("CODEMAP*.md")):
        if not path.is_file():
            continue
        rel = relative(path, map_dir)
        text = read_text(path)
        source = rel
        status = meta_value(text, "status")
        commit = meta_value(text, "verified-commit")
        conflicts = text.count("[CONFLICT][conflict]")
        role = meta_value(text, "map-role")
        entry = Entry(
            kind="index" if role == "index" else "domain",
            id=path.stem,
            path=rel,
            status=status,
            verified_at=meta_value(text, "verified-at"),
            verified_commit=commit,
            conflicts=conflicts,
        )
        entries[source] = entry
        anchors.extend(map_anchors(text, source, commit))

    graph_dir = map_dir / "graphs"
    if graph_dir.is_dir():
        for path in sorted([*graph_dir.rglob("*.yaml"), *graph_dir.rglob("*.yml")]):
            text = read_text(path)
            try:
                graph = yaml.safe_load(text)
            except yaml.YAMLError:
                graph = None
            if not isinstance(graph, dict):
                continue
            rel = relative(path, map_dir)
            commit = str(graph.get("verified_commit") or "")
            source = rel
            status = str(graph.get("status") or "")
            entry = Entry(
                kind="graph",
                id=str(graph.get("id") or path.stem),
                path=rel,
                status=status,
                verified_at=str(graph.get("verified_at") or ""),
                verified_commit=commit,
                conflicts=1 if status == "conflict" else 0,
            )
            entries[source] = entry
            anchors.extend(graph_anchors(graph, source, commit))

    commit_ok: dict[str, bool] = {}
    for entry in entries.values():
        entry.head_ahead_commits, entry.verified_age_days, ok = commit_info(
            root, entry.verified_commit, now
        )
        commit_ok[entry.path] = ok

    if scan_anchors:
        check_anchors(root, anchors, entries, deep, cache)
    for entry in entries.values():
        entry.level = entry_level(entry, commit_ok[entry.path])

    ordered = sorted(entries.values(), key=lambda item: (-SEVERITY[item.level], item.path))
    level = max((entry.level for entry in ordered), key=lambda item: SEVERITY[item], default="fresh")
    primary = entries.get("CODEMAP.md") or (ordered[0] if ordered else None)
    reasons: list[str] = []
    for entry in ordered:
        for reason in entry.reasons:
            value = f"{entry.path}：{reason}"
            if value not in reasons:
                reasons.append(value)
    counts = {name: sum(1 for entry in ordered if entry.level == name) for name in LEVELS}
    stale_total = sum(entry.stale_anchors for entry in ordered)
    missing_total = sum(entry.missing_anchors for entry in ordered)
    anchor_total = sum(entry.anchor_count for entry in ordered)
    issue_total = sum(entry.issue_anchors for entry in ordered)
    return {
        "schema": SCHEMA,
        "root": str(root),
        "map_dir": str(map_dir),
        "head": head,
        "level": level,
        "verified_commit": primary.verified_commit if primary else "",
        "head_ahead_commits": primary.head_ahead_commits if primary else None,
        "verified_age_days": primary.verified_age_days if primary else None,
        "stale_anchors": stale_total,
        "missing_anchors": missing_total,
        "degraded_anchors": sum(entry.degraded_anchors for entry in ordered),
        "anchor_count": anchor_total,
        "issue_anchors": issue_total,
        "stale_ratio": round(issue_total / anchor_total, 3) if anchor_total else 0.0,
        "deep": deep,
        "scan_anchors": scan_anchors,
        "checked_entries": len(ordered),
        "counts": counts,
        "reasons": reasons[:12],
        "entries": [entry.as_dict() for entry in ordered],
    }


def disclaimer(level: str) -> str:
    if level == "fresh":
        return "地图基线内未发现变化；仍只说明证据源未变，不证明结论正确。"
    return "地图是导航缓存，不是事实层；当前新鲜度非 fresh，只能当线索，动手前必须核对源码。"


def banner(data: dict[str, Any]) -> str:
    level = data.get("level", "fresh")
    if level == "fresh":
        return ""
    details: list[str] = []
    if data.get("head_ahead_commits") is not None:
        details.append(f"领先 {data['head_ahead_commits']} 个提交")
    if data.get("verified_age_days") is not None:
        details.append(f"基线已 {data['verified_age_days']} 天")
    if data.get("stale_anchors"):
        details.append(f"{data['stale_anchors']} 条锚点证据已变化")
    if data.get("missing_anchors"):
        details.append(f"{data['missing_anchors']} 条锚点已失效")
    summary = "；".join(details) or "无法确认基线"
    return (
        f"> **新鲜度：{level}**（{summary}）\n"
        f"> {disclaimer(level)}\n\n"
    )


def render_text(data: dict[str, Any]) -> str:
    lines = ["== 新鲜度 =="]
    for entry in data["entries"]:
        kind = {"index": "L1", "domain": "L2", "graph": "Graph"}.get(entry["kind"], entry["kind"])
        details: list[str] = []
        if entry["head_ahead_commits"] is not None:
            details.append(f"领先 {entry['head_ahead_commits']} 提交")
        if entry["verified_age_days"] is not None:
            details.append(f"{entry['verified_age_days']} 天")
        if entry["stale_anchors"]:
            details.append(f"{entry['stale_anchors']} 条需重核")
        if entry["missing_anchors"]:
            details.append(f"{entry['missing_anchors']} 条失效")
        if entry["degraded_anchors"]:
            details.append(f"{entry['degraded_anchors']} 条降级检查")
        suffix = f"：{'；'.join(details)}" if details else ""
        flag = "[可能过期] " if entry["level"] in {"aging", "needs-review", "stale", "conflict"} else ""
        lines.append(f"[{entry['level']}] {flag}{kind} {entry['path']}{suffix}")
        for reason in entry["reasons"]:
            lines.append(f"  - {reason}")
    counts = " / ".join(f"{name} {data['counts'][name]}" for name in LEVELS)
    lines.append(f"总体：{data['level']}（{counts}）")
    if data.get("anchor_count"):
        lines.append(
            f"锚点：共 {data['anchor_count']} 条，需重核 {data['stale_anchors']} 条，"
            f"失效 {data['missing_anchors']} 条，过期比例 {data['stale_ratio']:.1%}"
        )
    if data["level"] != "fresh":
        lines.append(f"提示：{disclaimer(data['level'])}")
    return "\n".join(lines)
