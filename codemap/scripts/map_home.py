#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""地图目录解析：~/.codemap/maps/<project>/<branch>，并兼容项目内旧的 <root>/.map。

事实文件（CODEMAP*.md、graphs/、overlays/）按分支全量存放；views/ 与 .metrics/ 是派生产物。
所有脚本和 MCP 都通过这里定位地图，不各自拼路径。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path(os.environ.get("CODEMAP_HOME", "~/.codemap")).expanduser()
MAPS_HOME = Path(os.environ.get("CODEMAP_MAP_HOME", str(HOME / "maps"))).expanduser()

FACT_PATTERNS = ("CODEMAP*.md", "graphs", "overlays")
DERIVED_DIRS = ("views", ".metrics", "context", "site")
FORMAT = 1
NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class Location:
    root: Path
    map_dir: Path
    branch: str
    project: str
    source: str  # home | home-default | legacy | explicit | missing
    expected: Path
    repo_home: Path
    meta: dict[str, Any] = field(default_factory=dict)
    note: str = ""

    @property
    def exists(self) -> bool:
        return (self.map_dir / "CODEMAP.md").is_file()

    def as_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "map_dir": str(self.map_dir),
            "expected": str(self.expected),
            "repo_home": str(self.repo_home),
            "branch": self.branch,
            "project": self.project,
            "source": self.source,
            "note": self.note,
            "exists": self.exists,
            "repo_id": self.meta.get("repo_id", ""),
            "default_branch": self.meta.get("default_branch", ""),
        }


def git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=str(path), capture_output=True, text=True, check=False
    )


def sanitize(value: str) -> str:
    cleaned = NAME_RE.sub("-", value.strip()).strip("-._")
    return cleaned or "project"


def branch_dir(branch: str) -> str:
    return sanitize(branch.replace("/", "__"))


def current_branch(root: Path) -> str:
    proc = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    branch = proc.stdout.strip()
    if branch and branch != "HEAD":
        return branch
    sha = git(root, "rev-parse", "--short=8", "HEAD").stdout.strip()
    return f"detached-{sha or 'unknown'}"


def default_branch(root: Path) -> str:
    head = git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if head.returncode == 0 and head.stdout.strip().startswith("origin/"):
        return head.stdout.strip()[len("origin/") :]
    for name in ("main", "master"):
        if git(root, "show-ref", "--verify", "--quiet", f"refs/heads/{name}").returncode == 0:
            return name
    return current_branch(root)


def repo_id(root: Path) -> str:
    roots = git(root, "rev-list", "--max-parents=0", "HEAD").stdout.split()
    return min(roots)[:16] if roots else ""


def remote_url(root: Path) -> str:
    proc = git(root, "remote", "get-url", "origin")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def project_name(root: Path, meta: dict[str, Any] | None = None) -> str:
    if meta and meta.get("name"):
        return str(meta["name"])
    return sanitize(root.name)


def repo_home(root: Path, meta: dict[str, Any] | None = None) -> Path:
    return MAPS_HOME / project_name(root, meta)


def meta_path(root: Path, meta: dict[str, Any] | None = None) -> Path:
    return repo_home(root, meta) / "repo.json"


def read_meta(root: Path) -> dict[str, Any]:
    path = meta_path(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_meta(root: Path, branch: str | None = None) -> dict[str, Any]:
    home = repo_home(root)
    home.mkdir(parents=True, exist_ok=True)
    meta = read_meta(root)
    meta.update(
        {
            "format": FORMAT,
            "name": project_name(root, meta),
            "root": str(root.resolve()),
            "remote": remote_url(root),
            "repo_id": repo_id(root) or meta.get("repo_id", ""),
            "default_branch": meta.get("default_branch") or default_branch(root),
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    if branch:
        meta["last_branch"] = branch
    path = home / "repo.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def home_branch(root: Path, branch: str) -> Path:
    meta = read_meta(root)
    return repo_home(root, meta) / branch_dir(branch)


def project_root_from_map(map_dir: Path) -> Path | None:
    """地图位于 ~/.codemap/maps/<project>/<branch> 时，从同项目 repo.json 取项目根。"""
    map_dir = map_dir.expanduser().resolve()
    if MAPS_HOME.resolve() not in map_dir.parents:
        return None
    current = map_dir
    for _ in range(4):
        candidate = current / "repo.json"
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if data:
            root = data.get("root")
            if isinstance(root, str) and root.strip():
                path = Path(root).expanduser()
                if path.is_dir():
                    return path.resolve()
        if current == MAPS_HOME.resolve() or current.parent == current:
            break
        current = current.parent
    return None


def git_root(path: Path) -> Path | None:
    proc = git(path, "rev-parse", "--show-toplevel")
    return Path(proc.stdout.strip()).resolve() if proc.returncode == 0 else None


def resolve(root: Path, branch: str | None = None, explicit: Path | str | None = None) -> Location:
    root = Path(root).expanduser().resolve()
    meta = read_meta(root)
    branch = branch or current_branch(root)
    home = repo_home(root, meta)
    expected = home / branch_dir(branch)
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        return Location(root, path, branch, project_name(root, meta), "explicit", path, home, meta)
    if (expected / "CODEMAP.md").is_file():
        return Location(root, expected, branch, project_name(root, meta), "home", expected, home, meta)
    fallback = str(meta.get("default_branch") or "")
    if fallback and fallback != branch:
        alt = home / branch_dir(fallback)
        if (alt / "CODEMAP.md").is_file():
            note = f"当前分支 {branch} 没有地图，回退到默认分支 {fallback}；新鲜度仍按当前分支计算"
            return Location(root, alt, branch, project_name(root, meta), "home-default", expected, home, meta, note)
    legacy = root / ".map"
    if (legacy / "CODEMAP.md").is_file():
        note = "地图仍在项目 .map/（legacy）；建议运行 migrate_maps 迁入 ~/.codemap/maps"
        return Location(root, legacy, branch, project_name(root, meta), "legacy", expected, home, meta, note)
    return Location(root, expected, branch, project_name(root, meta), "missing", expected, home, meta)


def fact_files(source: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in FACT_PATTERNS:
        for path in sorted(source.glob(pattern)):
            if path.is_file():
                files.append(path)
            elif path.is_dir():
                files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
    return files


def ensure(root: Path, branch: str | None = None, copy_from: Path | None = None) -> Location:
    root = Path(root).expanduser().resolve()
    branch = branch or current_branch(root)
    meta = write_meta(root, branch)
    home = repo_home(root, meta)
    target = home / branch_dir(branch)
    target.mkdir(parents=True, exist_ok=True)
    for name in DERIVED_DIRS:
        (target / name).mkdir(parents=True, exist_ok=True)
    if copy_from and copy_from.is_dir():
        for path in fact_files(copy_from):
            rel = path.relative_to(copy_from)
            if rel.parts and rel.parts[0] in DERIVED_DIRS:
                continue
            destination = target / rel
            if destination.exists():
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    return Location(root, target, branch, project_name(root, meta), "home", target, home, meta)


def iter_projects() -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    if not MAPS_HOME.is_dir():
        return projects
    for meta_file in sorted(MAPS_HOME.glob("*/repo.json")):
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        root = Path(str(meta.get("root", ""))).expanduser()
        branches = sorted(
            path.name for path in meta_file.parent.iterdir()
            if path.is_dir() and (path / "CODEMAP.md").is_file()
        )
        projects.append(
            {
                "name": meta.get("name") or meta_file.parent.name,
                "root": str(root) if str(root) else "",
                "map_home": str(meta_file.parent),
                "branches": branches,
                "repo_id": meta.get("repo_id", ""),
                "default_branch": meta.get("default_branch", ""),
            }
        )
    return projects


def _print(data: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif isinstance(data, dict):
        for key, value in data.items():
            print(f"{key}: {value}")
    else:
        print(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_resolve = sub.add_parser("resolve", help="解析项目当前分支的地图目录")
    p_resolve.add_argument("--root", type=Path, required=True)
    p_resolve.add_argument("--branch")
    p_resolve.add_argument("--map-root", type=Path)
    p_resolve.add_argument("--json", action="store_true")

    p_ensure = sub.add_parser("ensure", help="创建地图目录并写入 repo.json")
    p_ensure.add_argument("--root", type=Path, required=True)
    p_ensure.add_argument("--branch")
    p_ensure.add_argument("--from-map", type=Path, help="从旧地图目录复制事实文件")
    p_ensure.add_argument("--json", action="store_true")

    p_list = sub.add_parser("list", help="列出 map home 中的项目")
    p_list.add_argument("--json", action="store_true")

    p_root = sub.add_parser("root", help="从地图目录反查项目根")
    p_root.add_argument("--map-root", type=Path, required=True)

    p_meta = sub.add_parser("meta", help="读取或刷新项目 repo.json")
    p_meta.add_argument("--root", type=Path, required=True)
    p_meta.add_argument("--write", action="store_true")
    p_meta.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "resolve":
        location = resolve(args.root, args.branch, args.map_root)
        _print(location.as_dict(), args.json)
        return 0 if location.exists else 1

    if args.command == "ensure":
        location = ensure(args.root, args.branch, args.from_map)
        _print(location.as_dict(), args.json)
        return 0

    if args.command == "list":
        _print({"maps_home": str(MAPS_HOME), "projects": iter_projects()}, args.json)
        return 0

    if args.command == "root":
        root = project_root_from_map(args.map_root)
        if root is None:
            print("不是 map home 布局，且没有可用的 repo.json", file=sys.stderr)
            return 1
        print(root)
        return 0

    if args.command == "meta":
        meta = write_meta(args.root) if args.write else read_meta(args.root)
        _print(meta, args.json)
        return 0 if meta else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
