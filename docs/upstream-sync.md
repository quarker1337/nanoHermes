# NanoHermes upstream sync

NanoHermes is a downstream Hermes distribution. The GitHub repo is intentionally squashed: it keeps NanoHermes small and does not push the full `NousResearch/hermes-agent` history into `quarker1337/nanoHermes`.

The currently integrated upstream commit is tracked in:

```text
.nanohermes/upstream-base.txt
```

## Routine

```bash
git config rerere.enabled true
git fetch upstream main
python scripts/sync_upstream.py --dry-run
python scripts/sync_upstream.py
```

The script creates a branch named:

```text
sync/upstream-YYYYMMDD
```

Then it applies the patch range from the tracked upstream base to the target upstream commit with `git apply --3way --index`, updates `.nanohermes/upstream-base.txt`, and writes a report under `.hermes/upstream-sync/`.

This is intentionally not a `git merge upstream/main`: merging would make the slim downstream branch reference upstream history and would turn future pushes back into full Hermes-history pushes.

## Conflict hotspots

Expect conflicts most often in:

- `pyproject.toml`
- `uv.lock`
- `scripts/install.sh`
- `toolsets.py`
- `hermes_cli/main.py`
- `hermes_cli/setup.py`
- `cli.py`
- `tui_gateway/server.py`
- `tui_gateway/slash_worker.py`
- README/docs branding

## Verification after a sync

Focused gate:

```bash
bash -n scripts/install.sh
python3 -m py_compile hermes_cli/main.py scripts/sync_upstream.py scripts/upstream_sync_report.py
uv run --with pytest python -m pytest tests/package_manager/test_package_manager_cli.py -q -o 'addopts='
```

Broad gate before release:

```bash
HOME=$(mktemp -d /tmp/nanohermes-clean-home-XXXXXX) uv run --extra all python -m pytest -o 'addopts=' -m 'not integration' -q
npm test --prefix ui-tui
```

## Rules

- Keep upstream patch-sync commits separate from Nano-specific follow-up fixes when possible.
- Do not report a pre-edit broad test run as validation for a post-edit tree.
- If the sync branch is dirty or conflicts remain, do not push `main`.
- Do not merge `upstream/main` into `main`; use the patch-sync workflow so the remote stays slim.
