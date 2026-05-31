# NanoHermes packages

NanoHermes uses an apt-like package layer for optional tools, plugins, and skills. The default registry source is `quarker1337/Hermes-Packages`.

NanoHermes base intentionally starts with **zero installed skills**. The base runtime stays small and unopinionated; capabilities are installed explicitly from package-managed, checksummed assets.

## Commands

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
```

`hermes pkg show <package>` lists included skills when the registry manifest advertises them, and `hermes pkg search <skill-name>` can discover packages by included skill path, for example:

```bash
hermes pkg search github-pr-workflow
hermes pkg show skills-dev-core
```

## Skill packs and optional assets

Large first-party skill categories are intentionally not copied into the base wheel. They are delivered as checksummed package assets from `quarker1337/Hermes-Packages` and install into the active Hermes home:

```bash
hermes pkg update
hermes pkg search skills
hermes pkg install skills-creative --yes
```

The installer verifies each asset's SHA-256 before extracting it, rejects archives with unsafe paths/links, and only allows package assets under approved Hermes data roots such as `skills/`, `optional-skills/`, and `optional-mcps/`. Existing local files are kept unless a package explicitly opts into overwrite.

## Local package state

Package state is stored under the active Hermes home:

```text
$HERMES_HOME/packages/
  cache/registry-index.json
  installed.json
```

## Initial safety rules

- Base install has zero default skills.
- Official package source only by default.
- No arbitrary post-install scripts.
- Manifest permissions must be explicit.
- `install --dry-run` prints the plan without changing state.
- `install --yes` is required for state changes.
