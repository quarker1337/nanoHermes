# NanoHermes repository layout

This repo is a downstream Hermes Agent snapshot plus NanoHermes-specific package-management work.

The guiding rule is: keep the root readable. Root-level directories should be broad buckets; implementation-heavy Python modules live under package buckets such as `runtime/` instead of the repository root.

## Root buckets

| Path | What belongs here |
|---|---|
| `runtime/` | Relocated runtime Python packages inherited from Hermes Agent: `agent/`, `gateway/`, `tui_gateway/`, `cron/`, `acp_adapter/`, `providers/`, `plugins/`, and `hermes_runtime/`. `pyproject.toml` discovers packages from this bucket. |
| `tools/`, `hermes_cli/` | Runtime packages still left at root because they own many repo-root-relative paths and frontend/package-manager surfaces. |
| `hermes_cli/package_manager/` | NanoHermes package-manager implementation. The `nanohermes` executable is just an alias into `hermes_cli.main`; there is no separate root `nanohermes/` package anymore. |
| `apps/dashboard/` | Browser dashboard frontend. Formerly root `web/`. |
| `apps/tui/` | Terminal UI frontend. Formerly root `ui-tui/`. |
| `docs/` | Human-readable docs, notes, release history, plans, examples, assets, and the docs site. |
| `docs/examples/` | Curated runnable examples only. Scratch/generated examples belong in ignored subdirectories. |
| `docs/site/` | Docusaurus documentation site. Formerly root `website/`. |
| `docs/assets/` | Images/assets referenced by README/docs, including `banner.png`. |
| `config/` | Default templates seeded into user homes or packaged data, such as `env.example` and `cli-config.yaml.example`. |
| `constraints/` | Platform-specific dependency constraints, e.g. Termux. |
| `infra/docker/` | Container entrypoints: Dockerfile, Compose files, hadolint config, s6-overlay service files, and container boot hooks. |
| `infra/nix/` | Nix flake entrypoint (`flake.nix` / `flake.lock`) and implementation expressions. Use `nix develop 'path:.?dir=infra/nix'` or `nix build 'path:.?dir=infra/nix'`. |
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
| `LICENSE` | Legal entrypoint. |
| `pyproject.toml`, `setup.py`, `MANIFEST.in`, `uv.lock` | Python build/install contract. |
| `.gitattributes`, `.gitignore` | Root-level Git ignore and attribute contracts. |
| `.envrc` | Root direnv entrypoint; delegates to `use flake "path:.?dir=infra/nix"`. |

## Root-adjacent files moved into buckets

| Path | Why it is not at root |
|---|---|
| `.github/CONTRIBUTING.md`, `.github/SECURITY.md` | GitHub-recognized community health files; `.github/` keeps them discoverable without root clutter. |
| `docs/README.md`, `docs/README.zh-CN.md`, `docs/contributing/AGENTS.md`, `docs/contributing/mailmap` | Main GitHub README, localized README, agent contributor guide, and author map belong with docs/contributor material. GitHub recognizes `docs/README.md` when root has none. |
| `infra/nix/flake.nix`, `infra/nix/flake.lock` | Nix flake entrypoint and lockfile are infra; root `.envrc` points direnv at them. |
| `infra/docker/Dockerfile.dockerignore` | Dockerfile-specific build-context ignore file; Docker documents this as taking precedence over root `.dockerignore`, so the root file is not needed. |
| `scripts/hermes` | Source-checkout CLI launcher; installed `hermes`/`nanohermes` entrypoints still come from `pyproject.toml`. |

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

- `runtime/hermes_runtime/toolsets.py`
- `toolset_distributions.py`
- `tools/registry.py`
- `tools/lazy_deps.py`
- `plugins/`
- `providers/`

### Installer/container surface

- `scripts/install.sh`
- `scripts/install.ps1`
- `scripts/setup-hermes.sh`
- `infra/docker/Dockerfile`
- `infra/docker/docker-compose*.yml`
- `infra/docker/`

## Layout rules for future changes

1. Do not add new top-level directories unless they are broad buckets like `apps/`, `docs/`, `infra/`, or stable Python import roots.
2. Keep runtime Python packages at root until there is a dedicated `src/` migration branch with broad import/package tests.
3. Put product frontends under `apps/`, not root.
4. Put docs/static websites under `docs/`, not root.
5. Put container, Nix, distro packaging, contributor guides, GitHub community files, READMEs, and localized docs under `infra/`, `docs/`, or `.github/`, while keeping only tool-discovery contracts such as `.envrc`, `.gitignore`, and `.gitattributes` at root when moving them would break default tooling.
6. Do not add one-off markdown files to root. Put them under `docs/nanohermes/`, `docs/notes/`, `docs/plans/`, or `docs/releases/`.
7. Keep generated output out of git: `.hermes/`, `.venv/`, `build/`, `dist/`, frontend build outputs, and scratch examples.
8. Keep large corpus/resource payloads under `resources/` instead of root-level folders.
9. When moving files, update references in docs/tests in the same commit and run focused gates for every affected surface.
