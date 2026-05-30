#!/usr/bin/env python3
"""Create a NanoHermes upstream-sync branch without importing upstream history."""
from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_FILE = ROOT / "infra" / "nanohermes" / "upstream-base.txt"


def git(*args: str, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        text=True,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def ensure_clean_tree() -> None:
    status = git("status", "--porcelain").stdout.strip()
    if status:
        raise SystemExit("Working tree is not clean; commit or stash before syncing upstream.")


def current_branch() -> str:
    return git("branch", "--show-current").stdout.strip()


def read_base() -> str:
    if not BASE_FILE.exists():
        raise SystemExit(f"Missing {BASE_FILE}; cannot determine current upstream base.")
    base = BASE_FILE.read_text(encoding="utf-8").strip()
    if not base:
        raise SystemExit(f"{BASE_FILE} is empty; cannot determine current upstream base.")
    return base


def verify_commit(ref: str, label: str) -> None:
    result = git("cat-file", "-e", f"{ref}^{{commit}}", check=False)
    if result.returncode != 0:
        raise SystemExit(f"Cannot resolve {label} commit {ref!r}. Fetch upstream first or fix {BASE_FILE}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print what would happen")
    parser.add_argument("--upstream", default="upstream", help="upstream remote name")
    parser.add_argument("--branch", default="main", help="upstream branch name")
    parser.add_argument("--base", default=None, help="override current upstream base SHA")
    args = parser.parse_args()

    ensure_clean_tree()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    sync_branch = f"sync/upstream-{stamp}"
    old_base = args.base or read_base()

    print(f"Current branch: {current_branch()}")
    print(f"Sync branch: {sync_branch}")
    print(f"Current upstream base: {old_base}")
    print(f"Target upstream ref: {args.upstream}/{args.branch}")

    if not args.dry_run:
        print("Fetching upstream so the patch range is available locally...")
    git("fetch", args.upstream, args.branch)

    new_base = git("rev-parse", f"FETCH_HEAD^{{commit}}").stdout.strip()
    verify_commit(old_base, "current upstream base")
    verify_commit(new_base, "target upstream")
    print(f"Target upstream commit: {new_base}")

    if old_base == new_base:
        print("Already at the requested upstream base; nothing to sync.")
        return 0

    changed_files = git("diff", "--name-only", old_base, new_base).stdout.strip()
    change_count = len([line for line in changed_files.splitlines() if line])
    print(f"Upstream changed files in patch range: {change_count}")

    if args.dry_run:
        return 0

    git("checkout", "-b", sync_branch)
    patch = git("diff", "--binary", old_base, new_base).stdout
    apply_result = git("apply", "--3way", "--index", check=False, input_text=patch)
    print(apply_result.stdout)
    if apply_result.returncode != 0:
        raise SystemExit(
            "Upstream patch did not apply cleanly. Resolve conflicts, then update "
            f"{BASE_FILE} to {new_base} before committing."
        )

    BASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASE_FILE.write_text(f"{new_base}\n", encoding="utf-8")
    git("add", str(BASE_FILE.relative_to(ROOT)))

    report = ROOT / ".hermes" / "upstream-sync" / f"{stamp}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["python3", "scripts/upstream_sync_report.py", "--output", str(report)],
        cwd=ROOT,
        check=False,
    )
    print(f"Wrote sync report: {report}")
    print("Review, run verification, then commit the sync branch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
