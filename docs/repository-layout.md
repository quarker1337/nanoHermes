# NanoHermes repository layout

This repo is a downstream Hermes Agent snapshot plus NanoHermes-specific package-management work.

The guiding rule is: keep the root readable. Root-level directories should be broad buckets; legacy Python import names stay stable through small root shim files that point at `runtime/`.

## Root buckets

| Path | What belongs here |
|---|---|
| `runtime/` | Relocated runtime Python packages inherited from Hermes Agent: `agent/`, `gateway/`, `tui_gateway/`, `cron/`, `acp_adapter/`, `providers/`, and `plugins/`. Root shim files preserve legacy imports and `python -m ...` entrypoints. |
| `tools/`, `hermes_cli/` | Runtime packages still left at root because they own many repo-root-relative paths and frontend/package-manager surfaces. |
| `hermes_cli/package_manager/` | NanoHermes package-manager implementation. The `nanohermes` executable is just an alias into `hermes_cli.main`; there is no separate root `nanohermes/` package anymore. |
| `apps/dashboard/` | Browser dashboard frontend. Formerly root `web/`. |
| `apps/tui/` | Terminal UI frontend. Formerly root `ui-tui/`. |
| `docs/` | Human-readable docs, notes, release history, plans, examples, assets, and the docs site. |
| `docs/examples/` | Curated runnable examples only. Scratch/generated examples belong in ignored subdirectories. |
| `docs/site/` | Docusaurus documentation site. Formerly root `website/`. |
| `docs/assets/` | Images/assets referenced by README/docs, including `banner.png`. |
| `infra/docker/` | Container support files used by the root `Dockerfile`. |
| `infra/nix/` | Nix expressions used by root `flake.nix`. |
| `infra/packaging/` | Distro/package-manager packaging helpers such as Homebrew formula files. |
| `infra/nanohermes/` | Downstream metadata such as `upstream-base.txt`. |
| `resources/acp/registry/` | ACP registry metadata (`agent.json`, icon). Formerly root `acp_registry/`. |
| `resources/locales/` | Runtime translation catalogs. Formerly root `locales/`. |
| `resources/skills/` | Bundled base skill corpus installed with the base distribution. |
| `resources/optional-skills/`, `resources/optional-mcps/` | Optional payloads for package-managed install, not base-wheel payloads. |
| `scripts/` | Maintainer scripts, installer scripts, sync scripts, and operational helpers. |
| `tests/` | Test suite. Focused package-manager tests live under `tests/package_manager/`. |
| `.github/` | CI/workflow automation. |

## Root files that remain intentionally

| Path | Why it stays at root |
|---|---|
| `README.md`, `README.zh-CN.md`, `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `AGENTS.md` | Project identity and contributor entrypoints. |
| `pyproject.toml`, `setup.py`, `MANIFEST.in`, `uv.lock` | Python build/install contract. |
| `package.json`, `package-lock.json` | Root Node dependency surface for browser tooling. |
| `Dockerfile`, `docker-compose*.yml`, `.dockerignore` | Standard Docker defaults expect these at root. The implementation files are in `infra/docker/`. |
| `flake.nix`, `flake.lock`, `.envrc` | Standard Nix/dev-shell entrypoints. Implementation files are in `infra/nix/`. |
| Root Python modules such as `cli.py`, `run_agent.py`, `toolsets.py`, `hermes_constants.py`, `utils.py` plus shim files such as `agent.py`, `gateway.py`, and `tui_gateway.py` | Legacy import/entrypoint modules listed in `pyproject.toml` or compatibility shims for packages relocated under `runtime/`. |

## Fast audit entry points

### Package manager

- `hermes_cli/package_manager/`
- `hermes_cli/main.py` (`pkg` / `plug` command wiring)
- `tests/package_manager/`
- `docs/packages.md`

### Frontends

- Dashboard: `apps/dashboard/`
- TUI: `apps/tui/`
- Docs site: `docs/site/`

### Upstream sync

- `infra/nanohermes/upstream-base.txt`
- `scripts/sync_upstream.py`
- `scripts/upstream_sync_report.py`
- `docs/upstream-sync.md`

### Base install size and package contents

- `pyproject.toml`
- `uv.lock`
- `setup.py`
- `MANIFEST.in`
- `resources/locales/`
- `resources/skills/`
- `resources/optional-skills/`
- `resources/optional-mcps/`

### Tool availability and runtime surface

- `toolsets.py`
- `toolset_distributions.py`
- `tools/registry.py`
- `tools/lazy_deps.py`
- `plugins/`
- `providers/`

### Installer/container surface

- `scripts/install.sh`
- `scripts/install.ps1`
- `setup-hermes.sh`
- `Dockerfile`
- `infra/docker/`
- `docker-compose*.yml`

## Layout rules for future changes

1. Do not add new top-level directories unless they are broad buckets like `apps/`, `docs/`, `infra/`, or stable Python import roots.
2. Keep runtime Python packages at root until there is a dedicated `src/` migration branch with broad import/package tests.
3. Put product frontends under `apps/`, not root.
4. Put docs/static websites under `docs/`, not root.
5. Put container, Nix, and distro packaging support under `infra/`, while keeping standard root entrypoint files (`Dockerfile`, `flake.nix`) where tools expect them.
6. Do not add one-off markdown files to root. Put them under `docs/nanohermes/`, `docs/notes/`, `docs/plans/`, or `docs/releases/`.
7. Keep generated output out of git: `.hermes/`, `.venv/`, `build/`, `dist/`, frontend build outputs, and scratch examples.
8. Keep large corpus/resource payloads under `resources/` instead of root-level folders.
9. When moving files, update references in docs/tests in the same commit and run focused gates for every affected surface.
