# NanoHermes packages

NanoHermes uses an apt-like package layer for optional tools/plugins. The registry source is `quarker1337/Hermes-Packages`.

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

## Skill packs and optional assets

Large first-party skill categories are intentionally not copied into the base
wheel. They are delivered as checksummed package assets from
`quarker1337/Hermes-Packages` and install into the active Hermes home:

```bash
hermes pkg update
hermes pkg search skills
hermes pkg install skills-creative --yes
```

The installer verifies each asset's SHA-256 before extracting it, rejects
archives with unsafe paths/links, and only allows package assets under approved
Hermes data roots such as `skills/`, `optional-skills/`, and `optional-mcps/`.
Existing local files are kept unless a package explicitly opts into overwrite.

## Local package state

Package state is stored under the active Hermes home:

```text
$HERMES_HOME/packages/
  cache/registry-index.json
  installed.json
```

## Initial safety rules

- Official package source only by default.
- No arbitrary post-install scripts.
- Manifest permissions must be explicit.
- `install --dry-run` prints the plan without changing state.
- `install --yes` is required for state changes.
