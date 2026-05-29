#!/usr/bin/env python3
"""Write a small upstream-sync report for the current NanoHermes branch."""
from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_FILE = ROOT / ".nanohermes" / "upstream-base.txt"


def run(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout.strip()


def read_base() -> str:
    if BASE_FILE.exists():
        return BASE_FILE.read_text(encoding="utf-8").strip()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    branch = run("branch", "--show-current")
    head = run("rev-parse", "--short", "HEAD")
    upstream_base = read_base()
    upstream_short = run("rev-parse", "--short", upstream_base) if upstream_base else "unknown"
    status = run("status", "--short") or "clean"
    if upstream_base:
        stat = run("diff", "--stat", upstream_base, "HEAD") or "no downstream diff"
    else:
        stat = "missing .nanohermes/upstream-base.txt"
    content = f"""# Upstream sync report

Generated: {datetime.now(timezone.utc).isoformat()}

Branch: `{branch}`
HEAD: `{head}`
Tracked upstream base: `{upstream_short}`

NanoHermes uses a squashed downstream history. The upstream base is stored in
`.nanohermes/upstream-base.txt`; sync branches apply an upstream patch range
instead of merging `upstream/main`, so pushes stay small.

## Working tree

```text
{status}
```

## Downstream diff stat vs tracked upstream base

```text
{stat}
```

## Required verification

```bash
bash -n scripts/install.sh
python3 -m py_compile hermes_cli/main.py scripts/sync_upstream.py scripts/upstream_sync_report.py
uv run --with pytest python -m pytest tests/package_manager/test_package_manager_cli.py -q -o 'addopts='
```
"""
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(args.output)
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
