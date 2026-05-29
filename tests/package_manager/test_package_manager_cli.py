import json
from pathlib import Path

from nanohermes.package_manager import cli as pkg_cli
from nanohermes.package_manager.registry import PackageRegistry
from nanohermes.package_manager.state import PackageState


def _write_registry(tmp_path: Path) -> Path:
    registry = {
        "schema_version": 1,
        "generated_at": "2026-05-29T00:00:00Z",
        "package_count": 1,
        "packages": {
            "web-search": {
                "name": "web-search",
                "display_name": "Web Search",
                "version": "0.1.0",
                "type": "toolset",
                "channel": "official",
                "description": "Web search and page extraction tools.",
                "dependencies": [],
                "install": {
                    "python_extras": ["web-search"],
                    "python_packages": [],
                    "system_packages": [],
                    "npm_packages": [],
                    "optional_assets": [],
                },
                "tools": {
                    "toolsets": ["web"],
                    "tools": ["web_search", "web_extract"],
                },
                "permissions": {
                    "network": True,
                    "filesystem": False,
                    "shell": False,
                    "browser": False,
                    "audio": False,
                    "microphone": False,
                    "secrets": [],
                },
                "env": {"required": [], "optional": ["FIRECRAWL_API_KEY"]},
                "security": {"post_install_scripts": False, "signed": False, "checksum": ""},
                "manifest_path": "packages/official/web-search/package.toml",
                "manifest_sha256": "0" * 64,
            }
        },
    }
    path = tmp_path / "index.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    return path


def test_registry_update_search_and_show_use_local_source(tmp_path):
    source = _write_registry(tmp_path)
    home = tmp_path / "home"

    registry = PackageRegistry(home=home)
    registry.update(source)

    matches = registry.search("web")
    assert [pkg["name"] for pkg in matches] == ["web-search"]
    assert registry.get("web-search")["install"]["python_extras"] == ["web-search"]


def test_search_uses_cached_registry_when_source_is_omitted(tmp_path, capsys):
    source = _write_registry(tmp_path)
    home = tmp_path / "home"

    assert pkg_cli.main(["--home", str(home), "--source", str(source), "update"]) == 0
    capsys.readouterr()

    rc = pkg_cli.main(["--home", str(home), "search", "web"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "web-search 0.1.0" in out


def test_install_dry_run_prints_plan_without_writing_state(tmp_path, capsys):
    source = _write_registry(tmp_path)
    home = tmp_path / "home"

    rc = pkg_cli.main(["--home", str(home), "--source", str(source), "install", "web-search", "--dry-run"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "Install plan" in out
    assert "web-search 0.1.0" in out
    assert "Python extras: web-search" in out
    assert "Permissions: network" in out
    assert not PackageState(home=home).installed


def test_install_yes_no_pip_records_package_state(tmp_path, capsys):
    source = _write_registry(tmp_path)
    home = tmp_path / "home"

    rc = pkg_cli.main([
        "--home",
        str(home),
        "--source",
        str(source),
        "install",
        "web-search",
        "--yes",
        "--no-pip",
    ])

    out = capsys.readouterr().out
    assert rc == 0
    assert "Installed web-search 0.1.0" in out
    installed = PackageState(home=home).installed
    assert installed["web-search"]["version"] == "0.1.0"
    assert installed["web-search"]["toolsets"] == ["web"]


def test_pkg_and_plug_are_builtin_cli_commands():
    from hermes_cli.main import _BUILTIN_SUBCOMMANDS

    assert "pkg" in _BUILTIN_SUBCOMMANDS
    assert "plug" in _BUILTIN_SUBCOMMANDS
