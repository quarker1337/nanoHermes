# NanoHermes

> **UNDER CONSTRUCTION:** NanoHermes is a work-in-progress downstream fork of
> [Nous Research Hermes Agent](https://github.com/NousResearch/hermes-agent).
> It is not the upstream Hermes release, not production-stable, and not yet a
> polished installer experience.

NanoHermes is the experimental **minimal install / package-managed fork** of
Hermes Agent.

The goal is simple:

- keep the base Hermes install smaller;
- move optional tools and heavier integrations out of the default install;
- let users add capabilities later through an apt-like package flow;
- keep upstream Hermes compatibility where possible.

If you want the stable official agent today, use upstream Hermes Agent instead:

- Docs: https://hermes-agent.nousresearch.com/docs/
- Repo: https://github.com/NousResearch/hermes-agent

---

## What this repo is

NanoHermes is a downstream distribution of Hermes Agent. It currently keeps the
core CLI identity and package metadata compatible with Hermes while adding a
`nanohermes` alias and an experimental package manager.

This repo is for people who want to test or help build the slimmer downstream
path, not for users who need the most stable Hermes setup right now.

---

## Current status

This project is actively being built.

Expected rough edges:

- install flow may change;
- package names and registry schema may change;
- optional tool packages may be incomplete;
- docs may lag behind the code;
- upstream sync may occasionally require manual conflict resolution.

Working/intentional pieces:

- NanoHermes is based on Hermes Agent;
- base dependencies are being slimmed where possible;
- optional features are being separated into package-managed installs;
- `hermes pkg ...` and `hermes plug ...` are the experimental package commands;
- `nanohermes` is available as a CLI alias for the Hermes entry point;
- the default package registry uses GitHub's Contents API for better network compatibility:
  `https://api.github.com/repos/quarker1337/Hermes-Packages/contents/registry/index.json?ref=main`.
  The direct raw index is also available at
  `https://raw.githubusercontent.com/quarker1337/Hermes-Packages/main/registry/index.json`.

---

## Quick start for contributors/testers

This is the current development-style install path:

```bash
git clone https://github.com/quarker1337/nanoHermes.git
cd nanoHermes

curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e .

hermes --help
nanohermes --help
```

On Windows, use PowerShell and the repository installer script once the repo is
checked out:

```powershell
.\scripts\install.ps1
```

Then try the package manager:

```bash
hermes pkg update
hermes pkg search web
hermes pkg show web-search
hermes pkg install web-search --dry-run
hermes pkg doctor
```

### Tiny base, package-managed capabilities

NanoHermes base intentionally starts with **zero installed skills**. Install the capability profile you need from the registry:

```bash
# Coding agent basics: planning, debugging, tests, code review, GitHub workflows
hermes pkg install skills-dev-core --yes

# Maintainer agent: Hermes/NanoHermes internals and skill authoring
hermes pkg install skills-hermes-maintainer --yes

# Agent CLI delegation: Claude Code, Codex, OpenCode, OpenHands, etc.
hermes pkg install skills-agent-clis --yes

# Research agent basics
hermes pkg install skills-research --yes

# MLOps agent, split by workload
hermes pkg install skills-mlops-training --yes
hermes pkg install skills-mlops-inference --yes
hermes pkg install skills-mlops-vector-db --yes
hermes pkg install skills-mlops-cloud --yes
hermes pkg install skills-mlops-models --yes
hermes pkg install skills-mlops-eval-curation --yes
```

Tool packages can carry matching workflow skills too. For example, `spotify` installs the Spotify media skill, `homeassistant` installs the OpenHue smart-home skill, `web-search` installs lightweight web-search skills, `dashboard` installs Kanban skills, and `mcp` installs native MCP / FastMCP / mcporter skills.

For local registry testing, pass `--source` before the subcommand for each command that should read the checked-out index:

```bash
hermes pkg --source ../Hermes-Packages/registry/index.json update
hermes pkg --source ../Hermes-Packages/registry/index.json install skills-dev-core --yes --no-pip
```

---

## Package registry

The companion registry repo is:

https://github.com/quarker1337/Hermes-Packages

That repo contains package manifests, schemas, validation scripts, and the
generated `registry/index.json` consumed by NanoHermes.

The split is intentional:

- `nanoHermes` = downstream runtime and package-manager client;
- `Hermes-Packages` = package metadata and registry index.

---

## Repository layout

The root is intentionally kept for runtime import roots, entrypoints, packaging
metadata, and high-signal project files. Maintainer docs, release history,
plans, examples, and binary doc assets live under dedicated folders now.

Start here when auditing the repo:

- [`repository-layout.md`](repository-layout.md) — top-level map,
  audit entry points, and rules for future file placement;
- [`nanohermes/overview.md`](nanohermes/overview.md) — downstream
  fork purpose, remotes, package-manager basics, and upstream-sync policy;
- [`packages.md`](packages.md) — package-manager user/developer notes;
- [`upstream-sync.md`](upstream-sync.md) — slim fork sync workflow.

---

## Relationship to upstream Hermes

NanoHermes is a fork/downstream distribution of Hermes Agent, not a replacement
for the official project.

Upstream Hermes remains the source of truth for the main agent architecture,
core features, documentation, and stable releases. NanoHermes experiments with a
smaller default footprint and package-managed optional capabilities.

We aim to keep upstream sync reviewable instead of hiding it behind an opaque
auto-update process.

Useful sync/report commands for maintainers:

```bash
python scripts/upstream_sync_report.py
python scripts/sync_upstream.py --dry-run
```

---

## Development checks

Before calling a NanoHermes change ready, prefer at least:

```bash
python3 -m py_compile hermes_cli/main.py scripts/sync_upstream.py scripts/upstream_sync_report.py
uv run --with pytest python -m pytest tests/package_manager/test_package_manager_runtime/hermes_runtime/cli.py -q -o 'addopts='
```

Use temp homes or `--home` in smoke tests so package-manager experiments do not
accidentally mutate your real Hermes profile.

---

## License and attribution

NanoHermes is derived from Nous Research Hermes Agent and keeps the upstream MIT
license lineage. See upstream Hermes Agent for the original project, docs, and
community links:

https://github.com/NousResearch/hermes-agent
