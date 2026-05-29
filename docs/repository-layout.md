# NanoHermes repository layout

This repo is a downstream Hermes Agent snapshot plus NanoHermes-specific package-management work. The layout intentionally keeps Python import roots at the repository root for now so upstream patch-syncs stay reviewable and editable installs keep working.

## Top-level buckets

| Path | Role | Audit notes |
|---|---|---|
| `agent/`, `tools/`, `hermes_cli/`, `gateway/`, `tui_gateway/`, `cron/`, `acp_adapter/`, `acp_registry/`, `providers/`, `plugins/` | Runtime Python packages inherited from Hermes Agent. | Treat as core runtime. Moving these requires `pyproject.toml`, imports, tests, and upstream-sync review. |
| `nanohermes/` | NanoHermes-specific runtime code. | Package-manager client lives in `nanohermes/package_manager/`; keep this surface small and heavily tested. |
| Root Python modules: `cli.py`, `run_agent.py`, `toolsets.py`, `toolset_distributions.py`, `hermes_bootstrap.py`, `hermes_constants.py`, `hermes_state.py`, `hermes_time.py`, `hermes_logging.py`, `utils.py`, `model_tools.py`, `batch_runner.py`, `trajectory_compressor.py`, `mcp_serve.py`, `mini_swe_runner.py` | Legacy import/entrypoint modules listed in `pyproject.toml` or used by scripts. | Do not move casually; first confirm imports and `tool.setuptools.py-modules`. |
| `skills/` | Bundled base skill corpus installed with the base distribution. | Size-sensitive. If base install grows, audit here first. |
| `optional-skills/`, `optional-mcps/` | Optional payload candidates for package-managed install. | Should not be bundled into every base wheel/sdist. Check `MANIFEST.in` and `setup.py`. |
| `tests/` | Test suite. | Focused NanoHermes package-manager tests are under `tests/package_manager/`. |
| `scripts/` | Maintainer scripts, installer scripts, sync scripts, and small operational helpers. | Public installer scripts are packaging-sensitive; sync scripts are NanoHermes-critical. |
| `docker/`, `Dockerfile`, `docker-compose*.yml` | Container runtime and compose entrypoints. | Kept at root because Docker tooling and tests expect the default paths. |
| `nix/`, `packaging/`, `setup.py`, `pyproject.toml`, `uv.lock`, `MANIFEST.in` | Build, packaging, dependency, and distro surfaces. | High-risk audit area for base-size and supply-chain changes. |
| `web/`, `ui-tui/`, `website/`, `locales/` | Web dashboard, terminal UI, documentation site, and translations. | Large but mostly product/docs surface; keep generated build outputs ignored. |
| `.github/` | CI/workflow automation. | Review whenever test gates or release automation changes. |
| `.nanohermes/` | Downstream metadata. | `upstream-base.txt` records the upstream commit represented by the squashed snapshot. |
| `docs/` | Human-readable docs, notes, release history, plans, and audit maps. | Prefer adding maintainer docs here instead of root-level one-off files. |
| `examples/` | Curated runnable examples. | Scratch/generated example output belongs in `examples/generated/` or `examples/local/`, both ignored. |
| `assets/` | Root README assets. | Kept only for files directly referenced by root-facing docs. |

## Docs substructure

| Path | Contents |
|---|---|
| `docs/nanohermes/` | NanoHermes overview and downstream-specific maintainer docs. |
| `docs/releases/` | Historical release notes moved out of the repository root. |
| `docs/plans/` | Implementation plans worth keeping in git. |
| `docs/notes/` | Historical notes and design scraps that should not clutter root. |
| `docs/security/` | Security hardening docs. |
| `docs/assets/` | Images and other assets referenced by docs. |

## Fast audit entry points

### Package manager

- `nanohermes/package_manager/`
- `hermes_cli/main.py` (`pkg` / `plug` command wiring)
- `tests/package_manager/`
- `docs/packages.md`

### Upstream sync

- `.nanohermes/upstream-base.txt`
- `scripts/sync_upstream.py`
- `scripts/upstream_sync_report.py`
- `docs/upstream-sync.md`

### Base install size and package contents

- `pyproject.toml`
- `uv.lock`
- `setup.py`
- `MANIFEST.in`
- `skills/`
- `optional-skills/`
- `optional-mcps/`

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
- `docker/`
- `docker-compose*.yml`

## Layout rules for future changes

1. Keep runtime Python packages at root until there is a dedicated `src/` migration branch with broad import tests.
2. Do not add new one-off markdown files to root. Put them under `docs/nanohermes/`, `docs/notes/`, `docs/plans/`, or `docs/releases/`.
3. Keep generated output out of git: `.hermes/`, `.venv/`, `build/`, `dist/`, web build outputs, and scratch examples.
4. Keep NanoHermes-specific code under `nanohermes/` unless it must wire into upstream Hermes CLI/runtime paths.
5. When moving files, update references in docs/tests in the same commit and run at least the focused package-manager gate.
