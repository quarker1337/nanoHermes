# NanoHermes packages

NanoHermes uses an apt-like package layer for optional tools, plugins, and skills. The default registry source is `quarker1337/Hermes-Packages`.

NanoHermes base intentionally starts with **zero installed skills**. The base runtime stays small and unopinionated; capabilities are installed explicitly from package-managed, checksummed assets.

## Command shape

```bash
hermes pkg update
hermes pkg search web
hermes pkg show web-search
hermes pkg install web-search --dry-run
hermes pkg install web-search --yes
hermes pkg list
hermes pkg remove web-search
hermes pkg doctor
```

`hermes plug ...` is an alias for `hermes pkg ...`.

Package-manager global options go before the subcommand:

```bash
hermes pkg --home /tmp/nanohermes-home update
hermes pkg --source /path/to/registry/index.json search github-pr-workflow
hermes pkg --source https://raw.githubusercontent.com/YOU/Hermes-Packages/main/registry/index.json install my-tools --dry-run
```

Useful globals:

- `--home PATH` points package state at a temporary or alternate Hermes home.
- `--source URL_OR_PATH` selects the registry index for this command.
- `--timeout SECONDS` belongs after subcommands that fetch a registry, for example `hermes pkg update --timeout 60`.

Use `--home` for experiments so package tests do not mutate your real `~/.hermes`.

## First useful skill packs

For a fresh coding-oriented NanoHermes install, start here:

```bash
hermes pkg update
hermes pkg show skills-dev-core
hermes pkg install skills-dev-core --yes
```

Useful optional follow-ups:

```bash
# Hermes/NanoHermes maintainer workflows
hermes pkg install skills-hermes-maintainer --yes

# Delegation workflows for Claude Code, Codex, OpenCode, OpenHands, etc.
hermes pkg install skills-agent-clis --yes

# Dashboard/Kanban runtime plus matching Kanban skills
hermes pkg install dashboard --yes

# Browser automation Python tools + historical web_search helper (no local Chromium download)
hermes pkg install browser --yes

# Explicit local browser engine bootstrap: Node.js, agent-browser, Chromium/headless-shell
hermes pkg install browser-engine --yes
```

Broader capability packs are split so users can install only what they need:

```bash
# Apple/macOS workflows
hermes pkg install skills-apple-macos --yes

# Media workflows
hermes pkg install skills-media --yes

# Finance workflows
hermes pkg install skills-finance --yes

# DevOps/container/tunnel/watchers
hermes pkg install skills-devops --yes

# Security and OSINT workflows
hermes pkg install skills-security-osint --yes

# MLOps split packs
hermes pkg install skills-mlops-training --yes
hermes pkg install skills-mlops-inference --yes
hermes pkg install skills-mlops-vector-db --yes
hermes pkg install skills-mlops-cloud --yes
hermes pkg install skills-mlops-models --yes
hermes pkg install skills-mlops-eval-curation --yes
```

Integration packages can also install matching skills automatically. For example, `spotify` includes `media/spotify`, `homeassistant` includes `smart-home/openhue`, `web-search` includes lightweight web-search skills, and `mcp` includes native MCP / FastMCP / mcporter skills.

`hermes pkg show <package>` lists included skills when the registry manifest advertises them, and `hermes pkg search <skill-name>` can discover packages by included skill path, for example:

```bash
hermes pkg search github-pr-workflow
hermes pkg show skills-dev-core
```

## Registry sources: the sources.list-like part

The package client currently keeps one registry cache per Hermes home:

```text
$HERMES_HOME/packages/cache/registry-index.json
```

There is not yet a persistent multi-entry `sources.list` merge. The supported sources.list-like pattern is:

1. Pick one registry index for a command with `--source`.
2. Use the same `--source` on every command that should read that registry.
3. For repeated use, make a shell alias or wrapper.
4. To combine official and personal packages, fork or mirror `Hermes-Packages`, add your packages, rebuild its `registry/index.json`, and point NanoHermes at that combined index.

Examples:

```bash
# Official default. This is what plain `hermes pkg update` uses.
hermes pkg update

# Local checkout of a registry repo.
hermes pkg --source ~/src/Hermes-Packages/registry/index.json update
hermes pkg --source ~/src/Hermes-Packages/registry/index.json search my-package
hermes pkg --source ~/src/Hermes-Packages/registry/index.json install my-package --dry-run

# Raw GitHub URL for your own registry fork.
hermes pkg --source https://raw.githubusercontent.com/YOU/Hermes-Packages/main/registry/index.json update

# GitHub Contents API URL, useful when raw.githubusercontent.com is blocked.
hermes pkg --source 'https://api.github.com/repos/YOU/Hermes-Packages/contents/registry/index.json?ref=main' update
```

Wrapper example:

```bash
cat > ~/.local/bin/hpkg <<'SH'
#!/usr/bin/env bash
exec hermes pkg --source "$HOME/src/Hermes-Packages/registry/index.json" "$@"
SH
chmod +x ~/.local/bin/hpkg

hpkg update
hpkg search my-package
hpkg install my-package --yes
```

Important: if you run `hermes pkg install ...` without `--source`, NanoHermes fetches the default official registry again. Pass `--source` before `install` when installing from a local or personal registry.

## Local package state

Package state is stored under the active Hermes home:

```text
$HERMES_HOME/packages/
  cache/registry-index.json   # what could be installed from the last selected source
  installed.json              # what `hermes pkg` installed in this home
```

The installed database records package ownership, requested-vs-dependency installs, toolsets/tools, Python extras, package assets, permissions, and source metadata. Runtime surfaces use this state to decide which optional toolsets are available; they should not scrape CLI output.

## Creating your own registry repo

A package registry is just manifests plus a generated index. The official repo layout is:

```text
Hermes-Packages/
  packages/
    official/<name>/package.toml
    skills/<name>/package.toml
    mcp/<name>/package.toml
    community/<name>/package.toml
  assets/
    skills/<pack>.tar.gz
    python/<module-pack>.tar.gz
  registry/
    index.json
    index.min.json
    checksums.txt
  schemas/
    package.schema.json
    registry.schema.json
  scripts/
    build_index.py
    validate_package.py
```

For personal use, the easiest path is to fork `quarker1337/Hermes-Packages`, add packages under `packages/community/`, rebuild the index, and point NanoHermes at your fork with `--source`.

```bash
git clone git@github.com:YOU/Hermes-Packages.git
cd Hermes-Packages
mkdir -p packages/community/my-dev-skills assets/skills
# add package.toml and asset archives
python3 scripts/build_index.py
python3 scripts/build_index.py --check
git add packages assets registry
git commit -m "pkg: add my personal dev skills"
git push
```

Then install from the fork:

```bash
hermes pkg --source https://raw.githubusercontent.com/YOU/Hermes-Packages/main/registry/index.json update
hermes pkg --source https://raw.githubusercontent.com/YOU/Hermes-Packages/main/registry/index.json show my-dev-skills
hermes pkg --source https://raw.githubusercontent.com/YOU/Hermes-Packages/main/registry/index.json install my-dev-skills --yes
```

## Packaging personal skills

If your addition is procedural memory, workflows, prompts, or project-specific instructions, package it as a `skill_pack`. This is the best-supported personal customization path.

Archive shape matters: the archive is extracted directly into `$HERMES_HOME/skills`, so the archive should contain category/name directories, not a top-level `skills/` folder.

Example:

```bash
cd ~/src/Hermes-Packages
mkdir -p /tmp/my-skills/software-development/my-debug-flow
cp ~/.hermes/skills/software-development/my-debug-flow/SKILL.md \
  /tmp/my-skills/software-development/my-debug-flow/SKILL.md

tar -C /tmp/my-skills -czf assets/skills/my-dev-skills.tar.gz \
  software-development/my-debug-flow
```

Minimal manifest at `packages/community/my-dev-skills/package.toml`:

```toml
schema_version = 1
name = "my-dev-skills"
display_name = "My Developer Skills"
version = "0.1.0"
type = "skill"
channel = "community"
description = "Personal development workflow skills."
license = "private"
maintainer = "YOU"
dependencies = []

[nanohermes]
min_version = "0.15.1"
max_version = "<1.0.0"

[install]
python_extras = []
python_packages = []
system_packages = []
npm_packages = []
runtime_dependencies = []
optional_assets = [
  { type = "skill_pack", source = "assets/skills/my-dev-skills.tar.gz", format = "tar.gz", destination = "skills", overwrite = false },
]

[contents]
skills = [
  "software-development/my-debug-flow",
]

[tools]
toolsets = []
tools = []

[permissions]
network = false
filesystem = true
shell = false
browser = false
audio = false
microphone = false
secrets = []

[env]
required = []
optional = []

[checks]
commands = []
python_imports = []

[security]
checksum = ""
signed = false
post_install_scripts = false
```

Run `python3 scripts/build_index.py` after editing. The builder fills missing asset SHA-256 values into the generated registry index.

## Packaging tools for your personal install

There are three different cases. Pick the smallest one that matches what you are doing.

### 1. Existing optional NanoHermes toolset

If NanoHermes already has the tool implementation but it is optional, package metadata only needs to describe the dependency and the exposed toolset/tools.

Example shape:

```toml
schema_version = 1
name = "my-web-stack"
display_name = "My Web Stack"
version = "0.1.0"
type = "toolset"
channel = "community"
description = "Install web search plus my web-search skills."
license = "private"
maintainer = "YOU"
dependencies = ["web-search"]

[install]
python_extras = []
python_packages = []
system_packages = []
npm_packages = []
runtime_dependencies = []
optional_assets = []

[tools]
toolsets = ["web"]
tools = ["web_search", "web_extract"]

[permissions]
network = true
filesystem = true
shell = false
browser = false
audio = false
microphone = false
secrets = []
```

This records ownership and availability. Users may still need to enable the toolset for their platform with `hermes tools enable web` or the interactive `hermes tools` picker, then start a fresh session.

### 2. New pure-Python tool module

Advanced packages can install Python module assets into the active environment with a `python_module_pack` asset. The destination must be rooted under `python-site-packages/<package-or-module-root>`.

For a tool module, the asset should add a file under the installed `tools` package. That file must call `registry.register(...)` at module import time, just like built-in Hermes tools.

Manifest asset example:

```toml
[install]
python_extras = []
python_packages = []
system_packages = []
npm_packages = []
optional_assets = [
  { type = "python_module_pack", source = "assets/python/my-tools.tar.gz", format = "tar.gz", destination = "python-site-packages/tools", overwrite = false },
]

[tools]
toolsets = ["my-tools"]
tools = ["my_tool"]
```

Notes:

- This is for installed environments. Source checkouts can shadow site-packages, so smoke-test from outside the repo root or in a fresh venv.
- The archive is merged non-destructively by default; existing files are kept unless `overwrite = true`.
- No arbitrary package-provided post-install scripts run. If a package needs one of NanoHermes' built-in runtime bootstraps, use `runtime_dependencies` (currently `browser` for the explicit `browser-engine` package). Otherwise express Python extras in `python_extras`; treat `python_packages`, system packages, env vars, and commands as metadata/user instructions until a first-class installer handles them.
- Start a new Hermes session after installing so tool discovery imports the new module.

### 3. External tool server or plugin

For larger custom tools, prefer a normal Hermes plugin or MCP server and use a package only to deliver assets and advertise ownership. This avoids patching NanoHermes core and keeps the base runtime small.

Current package assets may install into approved roots only:

- `skills/`
- `optional-skills/`
- `optional-mcps/`
- `python-site-packages/<subdir>`

If your package needs more than that, it probably needs a first-class installer feature before it should be published broadly.

## Enabling installed tools

Installing a package makes its declared toolsets available to the active Hermes home. It does not force every session to use them.

Typical flow:

```bash
hermes pkg install browser --yes
hermes tools enable browser
# Start a fresh CLI session or use /reset in chat after changing tool config.
hermes
```

For dry runs and offline CI, use:

```bash
tmp_home=$(mktemp -d)
hermes pkg --home "$tmp_home" --source ~/src/Hermes-Packages/registry/index.json install browser --dry-run
hermes pkg --home "$tmp_home" --source ~/src/Hermes-Packages/registry/index.json install browser --yes --no-pip
hermes pkg --home "$tmp_home" list
```

`--no-pip` records package state and installs archive assets but skips pip dependency installation. It is useful for tests, not for a normal end-user install when the package declares Python extras.

## Skill packs and optional assets

Large first-party skill categories are intentionally not copied into the base wheel. They are delivered as checksummed package assets from `quarker1337/Hermes-Packages` and install into the active Hermes home:

```bash
hermes pkg update
hermes pkg search skills
hermes pkg install skills-creative --yes
```

The installer verifies each asset's SHA-256 before extracting it, rejects archives with unsafe paths/links/devices, and only allows package assets under approved Hermes data roots. Existing local files are kept unless a package explicitly opts into overwrite.

## Initial safety rules

- Base install has zero default skills.
- Official package source only by default.
- Alternate registries are explicit through `--source`.
- No arbitrary post-install scripts.
- Manifest permissions must be explicit.
- Archive assets must be checksum-verified and path-safe.
- `install --dry-run` prints the plan without changing state.
- `install --yes` is required for state changes.
