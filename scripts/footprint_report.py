#!/usr/bin/env python3
"""Report NanoHermes checkout size without mixing shipped payload and local junk.

The report intentionally separates:

* Git object store size.
* Tracked HEAD content grouped by top-level path.
* Actual local top-level checkout size.
* Ignored generated artifacts grouped by likely cause.
* Optional virtualenv/site-packages size when a venv path exists.

This is a measurement helper only; it never deletes files.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from importlib.metadata import distributions
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

CACHE_TOP_LEVEL = {
    ".mypy_cache",
    ".pytest-cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".uv-cache",
}
BUILD_TOP_LEVEL = {
    "build",
    "dist",
    "htmlcov",
}
DEV_ENV_NAMES = {
    ".direnv",
    ".venv",
    "node_modules",
    "venv",
}
GENERATED_DOCS_PREFIXES = (
    "docs/site/.docusaurus",
    "docs/site/static/api/",
    "docs/site/static/llms",
)
GENERATED_BUILD_NAMES = {
    "dist",
    "web_dist",
    "tui_dist",
}


def run_git(*args: str, check: bool = False) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def human_size(size: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(size)
    for unit in units:
        if abs(value) < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{size} B"


def path_size(path: Path) -> int:
    try:
        if path.is_symlink() or path.is_file():
            return path.lstat().st_size
        if path.is_dir():
            return sum(
                child.lstat().st_size
                for child in path.rglob("*")
                if child.exists() and not child.is_dir()
            )
    except OSError:
        return 0
    return 0


def tracked_tree_by_top() -> tuple[int, Counter[str]]:
    output = run_git("ls-tree", "-r", "-l", "HEAD")
    by_top: Counter[str] = Counter()
    total = 0
    for line in output.splitlines():
        if "\t" not in line:
            continue
        meta, rel_path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) < 4 or not parts[3].isdigit():
            continue
        size = int(parts[3])
        total += size
        top = rel_path.split("/", 1)[0]
        by_top[top] += size
    return total, by_top


def git_store_summary() -> dict[str, Any]:
    git_dir = ROOT / ".git"
    summary: dict[str, Any] = {
        "path": ".git",
        "bytes": path_size(git_dir) if git_dir.exists() else 0,
        "count_objects": {},
    }
    output = run_git("count-objects", "-vH")
    for line in output.splitlines():
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        summary["count_objects"][key] = value
    return summary


def local_top_level_sizes() -> Counter[str]:
    sizes: Counter[str] = Counter()
    for child in ROOT.iterdir():
        sizes[child.name] = path_size(child)
    return sizes


def ignored_paths() -> list[Path]:
    output = run_git("status", "--ignored", "--porcelain=v1", "-z")
    paths: list[Path] = []
    for record in output.split("\0"):
        if not record.startswith("!! "):
            continue
        rel = record[3:].rstrip("/")
        if not rel:
            continue
        paths.append(Path(rel))
    return collapse_nested_paths(paths)


def collapse_nested_paths(paths: list[Path]) -> list[Path]:
    collapsed: list[Path] = []
    for rel in sorted(paths, key=lambda item: (len(item.parts), item.as_posix())):
        if any(is_relative_to(rel, existing) for existing in collapsed):
            continue
        collapsed.append(rel)
    return collapsed


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return path != parent


def ignored_category(rel_path: Path) -> str:
    parts = rel_path.parts
    if not parts:
        return "other ignored"
    top = parts[0]
    name = parts[-1]
    posix = rel_path.as_posix()
    if top in CACHE_TOP_LEVEL or "__pycache__" in parts or name.endswith((".pyc", ".pyo")):
        return "bytecode/test caches"
    if top in BUILD_TOP_LEVEL or name.endswith(".egg-info") or name in GENERATED_BUILD_NAMES:
        return "build outputs"
    if any(part in DEV_ENV_NAMES for part in parts):
        return "dev environments/dependency installs"
    if posix.startswith(GENERATED_DOCS_PREFIXES):
        return "docs/frontend generated artifacts"
    return "other ignored"


def ignored_artifact_summary() -> tuple[Counter[str], Counter[str]]:
    by_category: Counter[str] = Counter()
    by_path: Counter[str] = Counter()
    for rel in ignored_paths():
        size = path_size(ROOT / rel)
        category = ignored_category(rel)
        by_category[category] += size
        by_path[rel.as_posix()] = size
    return by_category, by_path


def venv_summary(venv_path: Path) -> dict[str, Any] | None:
    if not venv_path.exists():
        return None
    total = path_size(venv_path)
    site_packages = sorted((venv_path / "lib").glob("python*/site-packages"))
    if not site_packages:
        return {"path": str(venv_path), "bytes": total, "site_packages": None}
    site = site_packages[0]
    entries: Counter[str] = Counter()
    for child in site.iterdir():
        entries[child.name] = path_size(child)
    dist_count = sum(1 for _ in distributions(path=[str(site)]))
    return {
        "path": str(venv_path),
        "bytes": total,
        "site_packages": {
            "path": str(site.relative_to(ROOT)) if site.is_relative_to(ROOT) else str(site),
            "bytes": path_size(site),
            "distribution_count": dist_count,
            "largest_entries": entries,
        },
    }


def top_items(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    return [
        {"name": name, "bytes": size, "human": human_size(size)}
        for name, size in counter.most_common(limit)
    ]


def build_report(top: int, venv: Path | None) -> dict[str, Any]:
    tracked_total, tracked_by_top = tracked_tree_by_top()
    ignored_by_category, ignored_by_path = ignored_artifact_summary()
    venv_path = venv if venv is not None else ROOT / ".venv"
    return {
        "repo": str(ROOT),
        "git": git_store_summary(),
        "tracked_head": {
            "bytes": tracked_total,
            "human": human_size(tracked_total),
            "by_top": top_items(tracked_by_top, top),
        },
        "local_top_level": top_items(local_top_level_sizes(), top),
        "ignored_artifacts": {
            "bytes": sum(ignored_by_category.values()),
            "human": human_size(sum(ignored_by_category.values())),
            "by_category": top_items(ignored_by_category, top),
            "largest_paths": top_items(ignored_by_path, top),
        },
        "venv": venv_summary(venv_path),
    }


def print_human(report: dict[str, Any], top: int) -> None:
    print("NanoHermes footprint report")
    print(f"repo: {report['repo']}")
    print()
    print("Git object store")
    print(f"  .git: {human_size(report['git']['bytes'])}")
    count_objects = report["git"].get("count_objects", {})
    for key in ("size-pack", "in-pack", "packs", "size"):
        if key in count_objects:
            print(f"  {key}: {count_objects[key]}")
    print()
    print("Tracked HEAD content")
    print(f"  total: {report['tracked_head']['human']}")
    for item in report["tracked_head"]["by_top"]:
        print(f"  {item['human']:>10}  {item['name']}")
    print()
    print("Local top-level checkout size")
    for item in report["local_top_level"]:
        print(f"  {item['human']:>10}  {item['name']}")
    print()
    print("Ignored/generated local artifacts")
    print(f"  total: {report['ignored_artifacts']['human']}")
    print("  by category:")
    for item in report["ignored_artifacts"]["by_category"]:
        print(f"  {item['human']:>10}  {item['name']}")
    print("  largest ignored paths:")
    for item in report["ignored_artifacts"]["largest_paths"][:top]:
        print(f"  {item['human']:>10}  {item['name']}")
    print()
    venv = report.get("venv")
    if not venv:
        print("Virtualenv: not found")
        return
    print("Virtualenv")
    print(f"  {venv['path']}: {human_size(venv['bytes'])}")
    site = venv.get("site_packages")
    if not site:
        return
    print(f"  site-packages: {human_size(site['bytes'])}")
    print(f"  installed distributions: {site['distribution_count']}")
    print("  largest site-packages entries:")
    for item in top_items(site["largest_entries"], top):
        print(f"  {item['human']:>10}  {item['name']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=15, help="number of largest entries to show")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--venv", type=Path, default=None, help="virtualenv path to inspect; defaults to .venv")
    args = parser.parse_args()
    top = max(1, args.top)
    report = build_report(top=top, venv=args.venv)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report, top=top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
