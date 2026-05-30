# NanoHermes

NanoHermes is a downstream Hermes distribution focused on a tiny core, package-managed optional tools, and a faster release cadence.

## Why this repo exists

NousResearch/hermes-agent moves on its own timeline. NanoHermes keeps a controlled downstream patch stack so we can ship:

- smaller default installs
- apt-like package management for tools/plugins
- honest runtime tool availability
- cleaner installer behavior
- regular upstream syncs from NousResearch/hermes-agent

## Repository shape

The current top-level map and audit entry points are documented in
[`../repository-layout.md`](../repository-layout.md).

The `quarker1337/nanoHermes` GitHub repo is intentionally slim/squashed. It contains a NanoHermes snapshot plus downstream changes, not the full upstream Hermes Git history.

The upstream commit represented by the snapshot is tracked in:

```text
infra/nanohermes/upstream-base.txt
```

Do not merge `upstream/main` into `main`; use the patch-sync workflow in
[`../upstream-sync.md`](../upstream-sync.md) so pushes stay small.

## Remotes

Recommended local remote setup:

```bash
git remote add origin git@github.com:quarker1337/nanoHermes.git
git remote add upstream https://github.com/NousResearch/hermes-agent.git
```

In this local checkout, `origin` should point to our NanoHermes repo and `upstream` should point to Nous.

## Package manager

Canonical command:

```bash
hermes pkg update
hermes pkg search web
hermes pkg show web-search
hermes pkg install web-search --dry-run
```

Alias:

```bash
hermes plug search web
```

The package registry lives in `quarker1337/Hermes-Packages`.

## Upstream sync

Use:

```bash
python scripts/sync_upstream.py --dry-run
python scripts/sync_upstream.py
```

See [`../upstream-sync.md`](../upstream-sync.md).
