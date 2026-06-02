---
name: nanohermes-upstream-sync
description: "Use when comparing NanoHermes against upstream NousResearch/hermes-agent, selectively porting upstream changes, or packaging upstream-only features without bloating the NanoHermes base."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [nanohermes, upstream-sync, downstream, packaging, hermes-agent]
    related_skills: [hermes-agent, hermes-agent-skill-authoring, github-repo-management]
---

# NanoHermes Upstream Sync

## Overview

NanoHermes is a slim downstream distribution of Hermes Agent. It intentionally keeps the base small, moves optional capabilities into `quarker1337/Hermes-Packages`, preserves Tirith/security behavior, and avoids silently restoring upstream's full bundled payload.

Use this skill to compare `/home/wayne/hans/nanoHermes` with upstream `NousResearch/hermes-agent`, decide what to port, and land changes safely. NanoHermes currently has a slim/downstream history shape, so do not assume a normal fork merge workflow.

## When to Use

Use this skill when the user asks to:

- Check how far NanoHermes drifted from upstream Hermes.
- Pull in a specific upstream feature, fix, provider, tool, plugin, app, or docs change.
- Re-sync after upstream releases or large upstream PRs.
- Package an upstream feature as an optional NanoHermes package instead of putting it back in base.
- Investigate upstream-only features such as the desktop app, GUI/dashboard changes, provider refactors, or installer changes.

Do not use this skill for ordinary app development unrelated to upstream Hermes. Do not blindly merge upstream into NanoHermes.

## Repository Map

Local checkouts:

```text
/home/wayne/hans/nanoHermes         # downstream runtime/source repo
/home/wayne/hans/Hermes-Packages    # package registry for optional tool/skill/app payloads
```

Important remotes:

```bash
cd /home/wayne/hans/nanoHermes
git remote -v
# origin   git@github.com:quarker1337/nanoHermes.git
# upstream https://github.com/NousResearch/hermes-agent.git
```

Important downstream conventions:

- Base NanoHermes starts with zero installed skills.
- Optional capabilities belong in package-managed assets when possible.
- `Hermes-Packages` manifests must advertise `contents.skills` for skills and regenerate `registry/index*.json` plus `registry/checksums.txt`.
- The base wheel should stay lean: avoid re-adding optional platform plugins, regional providers, browser engines, dashboard/desktop Node payloads, or large skill trees to the default wheel.
- Keep Tirith/security behavior unless the user explicitly approves a change.

## First: Fetch and Establish the Sync Shape

Always start clean and fetch upstream:

```bash
cd /home/wayne/hans/nanoHermes
git status --short
git fetch --all --prune --tags

git rev-parse --short=12 HEAD
git rev-parse --short=12 origin/main
git rev-parse --short=12 upstream/main
```

Check whether a normal merge base exists:

```bash
if mb=$(git merge-base HEAD upstream/main 2>/dev/null); then
  echo "merge-base: $(git rev-parse --short=12 "$mb")"
  git rev-list --left-right --count upstream/main...HEAD
else
  echo "No merge base: NanoHermes is a slim/downstream tree. Use tree/path comparison and selective porting, not git merge."
  git rev-list --left-right --count upstream/main...HEAD || true
fi
```

If there is no merge base, treat counts as rough reachability counts only. The useful comparison is file/tree-level drift, not merge ancestry.

## Drift Inventory Commands

Use tree comparisons that work even without shared history:

```bash
cd /home/wayne/hans/nanoHermes

# Snapshot-level churn summary.
git diff --shortstat upstream/main HEAD

# File status summary. R entries are rename heuristics, not proof of intentional moves.
git diff --name-status upstream/main HEAD > /tmp/nanohermes-upstream-name-status.txt
python3 - <<'PY'
from collections import Counter
lines = open('/tmp/nanohermes-upstream-name-status.txt', encoding='utf-8').read().splitlines()
print(Counter(line.split('\t', 1)[0][0] for line in lines if line))
PY

# Compare file sets and top-level roots.
python3 - <<'PY'
import subprocess, collections

def git(args):
    return subprocess.check_output(['git'] + args, text=True)

nano = set(git(['ls-tree', '-r', '--name-only', 'HEAD']).splitlines())
up = set(git(['ls-tree', '-r', '--name-only', 'upstream/main']).splitlines())

def top(files):
    c = collections.Counter(f.split('/', 1)[0] if '/' in f else '<root>' for f in files)
    return c.most_common(25)

print('nano files:', len(nano))
print('upstream files:', len(up))
print('common paths:', len(nano.intersection(up)))
print('nano-only:', len(nano.difference(up)))
print('upstream-only:', len(up.difference(nano)))
print('top nano-only:', top(nano.difference(up)))
print('top upstream-only:', top(up.difference(nano)))
PY
```

For current upstream release triage, also inspect recent upstream commits:

```bash
git log --oneline --decorate --max-count=30 upstream/main
git log --oneline --decorate --max-count=50 --grep='desktop' upstream/main
git log --oneline --decorate --max-count=50 --grep='installer\|provider\|browser\|gateway\|security' upstream/main
```

## Decide How to Port

Classify upstream drift into buckets before editing:

1. Must-port core fixes
   - Security fixes, auth/token persistence, crash fixes, model/provider correctness, session corruption, dangerous-command/Tirith hardening.
   - Port into NanoHermes source if the feature is still in the base runtime.

2. Package as optional capability
   - Browser engine, dashboard, desktop GUI, gateway integrations, provider packs, large skill trees, media/voice/image stacks, Node/Electron payloads.
   - Add or update `Hermes-Packages` manifests/assets instead of putting payloads back in base.

3. Keep out of NanoHermes base
   - Website source, full upstream skill corpus, optional plugins, large frontend workspaces, generated app release artifacts, platform-specific installers unless explicitly requested.

4. Needs design first
   - Upstream refactors that assume bundled payloads or broad default install behavior.
   - Anything that changes installer defaults, package-manager asset destinations, profile/toolset behavior, or Hermes home semantics.

## Selective Porting Workflow

Never use `git merge upstream/main` on NanoHermes unless you have first proven a safe merge base and the user approved a full merge. Prefer one of these patterns.

### Single File or Small Patch

```bash
cd /home/wayne/hans/nanoHermes

git show upstream/main:path/to/file.py > /tmp/upstream-file.py
# Compare against downstream path, accounting for moved files.
git diff --no-index -- path/to/downstream-file.py /tmp/upstream-file.py || true
```

Apply with `patch` or `write_file`, preserving NanoHermes packaging gates and lazy imports.

### Directory-Level Inspection

```bash
rm -rf /tmp/hermes-upstream-slice
mkdir -p /tmp/hermes-upstream-slice
git archive upstream/main path/to/dir | tar -C /tmp/hermes-upstream-slice -xf -

# Compare to downstream equivalent.
git diff --no-index -- /tmp/hermes-upstream-slice/path/to/dir downstream/path/to/dir || true
```

For large directories, list changed files first and port a small product slice rather than copying everything.

### Patch Range with No Shared History

When upstream commits are relevant but NanoHermes lacks their ancestry, inspect commit patches and manually adapt them:

```bash
git show --stat --find-renames <upstream_sha>
git show --find-renames --patch <upstream_sha> -- path/or/area
```

Do not `cherry-pick` unless the trees are close enough and the conflict surface is understood. Manual porting is usually safer.

## Package-Managed Feature Ports

When an upstream feature is optional in NanoHermes, work in both repos as one product slice:

1. In NanoHermes, make runtime hooks package-aware and lazy.
   - Base startup and tool discovery must not import or probe heavyweight optional dependencies.
   - Missing optional payloads should produce actionable install hints, not prompts or crashes.

2. In Hermes-Packages, add the package manifest and assets.
   - Put manifests under `packages/official/<name>/package.toml` for official tool/app/runtime packages.
   - Put pure skill packs under `packages/skills/<name>/package.toml`.
   - Put archives under `assets/python/` or `assets/skills/` as appropriate.
   - Regenerate registry outputs with `python3 scripts/build_index.py`.

3. Add tests in both repos.
   - Hermes-Packages: manifest/index/content tests.
   - NanoHermes: package-manager install/dry-run/state/runtime-availability tests.

4. Smoke local and remote registry flows.
   - `hermes pkg --source /home/wayne/hans/Hermes-Packages/registry/index.json show <pkg>`
   - `hermes pkg --source /home/wayne/hans/Hermes-Packages/registry/index.json install <pkg> --dry-run`
   - After push, repeat with the default remote registry.

## Desktop App Port Notes

Upstream now ships a native desktop app under:

```text
apps/desktop/              # Electron/Vite/React app
apps/shared/               # shared frontend package used by desktop
apps/bootstrap-installer/  # Tauri bootstrap installer, mostly upstream installer surface
hermes_cli/main.py         # desktop/gui command and build/launch helpers
scripts/install.sh         # --include-desktop on Unix-like installs
scripts/install.ps1        # desktop build/install flow on Windows
```

NanoHermes should not blindly restore this to base. Treat desktop as an optional package candidate.

Recommended NanoHermes desktop shape:

- Package name: `desktop` or `desktop-app`.
- Type: likely `bundle` or a new app-oriented package type if the registry schema grows one.
- Payload: `apps/desktop` plus `apps/shared` from upstream, probably archive-backed.
- Runtime dependencies: Node/npm plus desktop build dependencies. Existing `runtime_dependencies` only calls `ensure_dependency(<name>)`, so a desktop package may need a new dependency kind or a dedicated `ensure_dependency('desktop')` implementation.
- CLI: `hermes desktop` should be present only as a lightweight launcher/hint in base, or restored lazily so missing app source says `hermes pkg install desktop --yes`.
- Asset destinations: current package assets are restricted to `skills`, `optional-skills`, `optional-mcps`, and `python-site-packages/...`. Installing `apps/desktop` likely needs a new safe destination root such as `runtime/apps/desktop`, `$HERMES_HOME/apps/desktop`, or package-data under site-packages, plus a launcher that resolves that location.
- Tests: package-manager safe extraction, `hermes desktop --help`/missing-payload hint, local registry dry-run, and no desktop Node probes during base startup.

Port desktop in phases:

1. Inventory upstream desktop files and dependencies.
2. Add NanoHermes resolver/launcher design for package-installed app assets.
3. Add package-manager destination support if needed.
4. Create the desktop package asset and manifest in Hermes-Packages.
5. Verify `hermes pkg install desktop --dry-run` does not mutate base and advertises the large Node/Electron footprint clearly.
6. Only then attempt build/launch smokes.

## Verification Matrix

For NanoHermes source changes:

```bash
cd /home/wayne/hans/nanoHermes
.venv/bin/python -m pytest tests/package_manager/test_package_manager_cli.py -q -o 'addopts='
.venv/bin/python -m pytest <targeted tests> -q -o 'addopts='
git diff --check
git status --short
```

For Hermes-Packages changes:

```bash
cd /home/wayne/hans/Hermes-Packages
python3 scripts/build_index.py
python3 scripts/build_index.py --check
uv run --with pytest python -m pytest -q
git diff --check
git status --short
```

For remote package verification after push:

```bash
cd /home/wayne/hans/nanoHermes
tmp=$(mktemp -d /tmp/nano-pkg-smoke.XXXXXX)
.venv/bin/hermes pkg --home "$tmp" install <package> --dry-run --timeout 60
rm -rf "$tmp"
```

Before declaring complete:

- Local status is clean in both repos.
- Local head equals remote head by `git ls-remote`.
- Generated registry payload matches `scripts/build_index.py --check`.
- Optional packages do not reintroduce large payloads into the NanoHermes base wheel.

## Common Pitfalls

1. Blind upstream merge.
   - NanoHermes may have no merge base with upstream. Use tree/path comparison and selective ports.

2. Restoring optional payloads into base.
   - If upstream carries a large app, plugin, provider, skill corpus, or Node workspace, package it.

3. Forgetting the package repo.
   - Optional feature ports often need coordinated NanoHermes and Hermes-Packages changes.

4. Runtime probes during startup.
   - Base startup must not install/probe Node, Chromium, Electron, ffmpeg, or platform SDKs unless the user explicitly installed/requested that feature.

5. Asset destination mismatch.
   - The package manager currently restricts asset destinations. Add safe destination support deliberately rather than writing archives into arbitrary paths.

6. Treating current drift numbers as permanent.
   - Drift changes every upstream fetch. Regenerate the inventory each session and report exact SHAs.

7. Stale tests from old tree state.
   - If files change after a broad test starts, restart the test or clearly label the result stale.

## Quick Report Template

When reporting drift, include:

```text
NanoHermes HEAD: <sha>
Upstream main: <sha>
Merge base: <sha or none>
File snapshot: <nano files> nano / <upstream files> upstream / <common> common
Tree diff shortstat: <files changed>, <insertions>, <deletions>
Major upstream-only payloads: ...
Major NanoHermes-only payloads: ...
High-value upstream candidates: ...
Recommended next slice: ...
```
