# NanoHermes

> **UNDER CONSTRUCTION:** NanoHermes is a work-in-progress downstream fork of
> [Nous Research Hermes Agent](https://github.com/NousResearch/hermes-agent).
> It is not the official upstream Hermes release and is still an experimental
> package-managed distribution.

NanoHermes experiments with a smaller Hermes base install plus an apt-like
package layer for optional tools, plugins, skills, and desktop payloads.

If you want the stable official agent today, use upstream Hermes Agent:

- Docs: https://hermes-agent.nousresearch.com/docs/
- Repo: https://github.com/NousResearch/hermes-agent

## What is different?

NanoHermes keeps Hermes' core CLI and agent behavior, but moves heavier or
niche capabilities into package-managed installs:

- optional tool modules such as browser, web search, image generation, TTS,
  Home Assistant, Feishu, Yuanbao, and messaging;
- skill packs for development, research, MLOps, productivity, media, security,
  and maintainer workflows;
- desktop/dashboard payloads;
- explicit runtime packages such as `browser-engine` for local browser setup.

The package registry is a separate repo:

https://github.com/quarker1337/Hermes-Packages

## Current status

The current pushed `main` has passed a fresh default-registry all-package real
install smoke:

- NanoHermes installed from
  `git+https://github.com/quarker1337/nanoHermes.git@main`;
- default registry fetched from `quarker1337/Hermes-Packages`;
- all 46 registry packages installed without `--no-pip`;
- `browser-engine` installed the local agent-browser Chrome runtime;
- no invalid Python-extra warnings were emitted;
- package-restored first-party modules imported from `site-packages`;
- `hermes --version` stayed on the NanoHermes direct URL and reported
  `Up to date`.

Remaining caveat: the packaged desktop executable/build-only path has been
verified, but a real Electron GUI window smoke under Xvfb/CDP is still a future
validation step.

## Quick start

Requires Python 3.11+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install 'git+https://github.com/quarker1337/nanoHermes.git@main'

hermes --version
hermes --help
nanohermes --help
```

Windows users: native PowerShell installer support lives at
[`scripts/install.ps1`](scripts/install.ps1), but the NanoHermes-specific tested
install path is currently the direct-URL `uv` flow above until the PowerShell
installer source defaults are validated for this fork.

Fetch the package registry and inspect packages:

```bash
hermes pkg update
hermes pkg search ''
hermes pkg search web
hermes pkg show web-search
```

Install a small web/browser tool surface:

```bash
hermes pkg install web-search browser --yes

# Optional: local browser runtime bootstrap. This may download Chrome.
hermes pkg install browser-engine --yes
```

Install common profiles:

```bash
# Coding-agent workflows plus web/browser tools
hermes pkg install profile-developer --yes

# Research/productivity workflows plus web/browser tools
hermes pkg install profile-research --yes

# NanoHermes/Hermes maintainer workflows
hermes pkg install profile-maintainer --yes
```

Desktop/dashboard packages are opt-in:

```bash
hermes pkg install dashboard desktop --yes
hermes desktop --build-only --skip-build
```

## Development checkout

For local development against a checkout:

```bash
git clone https://github.com/quarker1337/nanoHermes.git
cd nanoHermes
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e .
```

For local registry testing, pass `--source` before every package subcommand that
should use the checked-out registry index:

```bash
hermes pkg --source ../Hermes-Packages/registry/index.json update
hermes pkg --source ../Hermes-Packages/registry/index.json install web-search --yes --no-pip
```

## Documentation

- [`docs/README.md`](docs/README.md) — longer project overview and contributor notes.
- [`docs/packages.md`](docs/packages.md) — package-manager commands, registry sources, and package-authoring notes.
- [`docs/repository-layout.md`](docs/repository-layout.md) — repository layout and audit map.
- [`docs/upstream-sync.md`](docs/upstream-sync.md) — downstream sync workflow.

## Relationship to upstream Hermes

NanoHermes is not a replacement for upstream Hermes. Upstream Hermes remains the
source of truth for the main agent architecture, docs, and stable release path.
NanoHermes keeps downstream changes reviewable and syncs selectively rather than
hiding upstream changes behind an opaque auto-update.

## License and attribution

NanoHermes is derived from Nous Research Hermes Agent and keeps the upstream MIT
license lineage. See upstream Hermes Agent for the original project and
community links:

https://github.com/NousResearch/hermes-agent
