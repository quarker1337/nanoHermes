import base64
import builtins
import hashlib
import json
import sys
import tarfile
import time
from pathlib import Path

import pytest

from hermes_cli.package_manager import cli as pkg_cli
from hermes_cli.package_manager import registry as registry_module
from hermes_cli.package_manager.registry import PackageRegistry, PackageRegistryError
from hermes_cli.package_manager.state import PackageState


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


def _write_registry_with_browser_dependency(tmp_path: Path) -> Path:
    path = _write_registry(tmp_path)
    registry = json.loads(path.read_text(encoding="utf-8"))
    registry["package_count"] = 2
    registry["packages"]["browser"] = {
        "name": "browser",
        "display_name": "Browser Automation",
        "version": "0.2.0",
        "type": "toolset",
        "channel": "official",
        "description": "Browser automation tools.",
        "dependencies": ["web-search"],
        "install": {
            "python_extras": [],
            "python_packages": [],
            "system_packages": [],
            "npm_packages": [],
            "optional_assets": [],
        },
        "tools": {
            "toolsets": ["browser"],
            "tools": ["browser_navigate", "browser_snapshot"],
        },
        "permissions": {
            "network": True,
            "filesystem": False,
            "shell": False,
            "browser": True,
            "audio": False,
            "microphone": False,
            "secrets": [],
        },
        "env": {"required": [], "optional": []},
        "security": {"post_install_scripts": False, "signed": False, "checksum": ""},
        "manifest_path": "packages/official/browser/package.toml",
        "manifest_sha256": "1" * 64,
    }
    path.write_text(json.dumps(registry), encoding="utf-8")
    return path


def _write_registry_with_python_asset(
    tmp_path: Path,
    *,
    destination: str = "python-site-packages/hermes_cli",
    sha256: str | None = None,
    members: dict[str, str] | None = None,
) -> Path:
    repo = tmp_path / "repo"
    asset_dir = repo / "assets" / "python"
    payload_dir = tmp_path / "payload"
    registry_dir = repo / "registry"
    asset_dir.mkdir(parents=True)
    payload_dir.mkdir(parents=True)
    archive_members = members or {"kanban.py": "PACKAGED_KANBAN = True\n"}
    for member_name, content in archive_members.items():
        member_path = payload_dir / member_name
        member_path.parent.mkdir(parents=True, exist_ok=True)
        member_path.write_text(content, encoding="utf-8")
    archive_path = asset_dir / "dashboard-hermes-cli.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for member_name in sorted(archive_members):
            archive.add(payload_dir / member_name, arcname=member_name)
    actual_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()

    registry = {
        "schema_version": 1,
        "generated_at": "2026-05-29T00:00:00Z",
        "package_count": 1,
        "packages": {
            "dashboard": {
                "name": "dashboard",
                "display_name": "Dashboard",
                "version": "0.1.0",
                "type": "toolset",
                "channel": "official",
                "description": "Dashboard and Kanban package.",
                "dependencies": [],
                "install": {
                    "python_extras": ["dashboard"],
                    "python_packages": [],
                    "system_packages": [],
                    "npm_packages": ["dashboard-frontend"],
                    "optional_assets": [
                        {
                            "type": "python_module_pack",
                            "source": "assets/python/dashboard-hermes-cli.tar.gz",
                            "format": "tar.gz",
                            "sha256": sha256 if sha256 is not None else actual_sha,
                            "destination": destination,
                        }
                    ],
                },
                "tools": {"toolsets": ["kanban"], "tools": []},
                "permissions": {
                    "network": True,
                    "filesystem": True,
                    "shell": True,
                    "browser": False,
                    "audio": False,
                    "microphone": False,
                    "secrets": [],
                },
                "env": {"required": [], "optional": []},
                "security": {"post_install_scripts": False, "signed": False, "checksum": actual_sha},
                "manifest_path": "packages/official/dashboard/package.toml",
                "manifest_sha256": "3" * 64,
            }
        },
    }
    registry_dir.mkdir(parents=True)
    path = registry_dir / "index.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    return path


def _write_registry_with_app_asset(
    tmp_path: Path,
    *,
    destination: str = "apps/desktop-workspace",
    sha256: str | None = None,
) -> Path:
    repo = tmp_path / "repo"
    asset_dir = repo / "assets" / "apps"
    payload_dir = tmp_path / "payload"
    registry_dir = repo / "registry"
    asset_dir.mkdir(parents=True)
    desktop_package = payload_dir / "apps" / "desktop" / "package.json"
    shared_package = payload_dir / "apps" / "shared" / "package.json"
    desktop_package.parent.mkdir(parents=True, exist_ok=True)
    shared_package.parent.mkdir(parents=True, exist_ok=True)
    (payload_dir / "package.json").write_text(
        '{"private": true, "workspaces": ["apps/*"]}\n',
        encoding="utf-8",
    )
    desktop_package.write_text('{"name": "hermes"}\n', encoding="utf-8")
    shared_package.write_text('{"name": "@hermes/shared"}\n', encoding="utf-8")
    archive_path = asset_dir / "desktop-workspace.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for member in sorted(payload_dir.rglob("*")):
            archive.add(member, arcname=member.relative_to(payload_dir))
    actual_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()

    registry = {
        "schema_version": 1,
        "generated_at": "2026-05-29T00:00:00Z",
        "package_count": 1,
        "packages": {
            "desktop": {
                "name": "desktop",
                "display_name": "Hermes Desktop",
                "version": "0.1.0",
                "type": "bundle",
                "channel": "official",
                "description": "Package-managed Electron desktop app workspace.",
                "dependencies": [],
                "install": {
                    "python_extras": [],
                    "python_packages": [],
                    "system_packages": [],
                    "npm_packages": ["electron workspace dependencies"],
                    "runtime_dependencies": ["node"],
                    "optional_assets": [
                        {
                            "type": "app_asset",
                            "source": "assets/apps/desktop-workspace.tar.gz",
                            "format": "tar.gz",
                            "sha256": sha256 if sha256 is not None else actual_sha,
                            "destination": destination,
                        }
                    ],
                },
                "tools": {"toolsets": [], "tools": []},
                "permissions": {
                    "network": True,
                    "filesystem": True,
                    "shell": True,
                    "browser": False,
                    "audio": True,
                    "microphone": True,
                    "secrets": [],
                },
                "env": {"required": [], "optional": []},
                "security": {"post_install_scripts": False, "signed": False, "checksum": actual_sha},
                "manifest_path": "packages/official/desktop/package.toml",
                "manifest_sha256": "6" * 64,
            }
        },
    }
    registry_dir.mkdir(parents=True)
    path = registry_dir / "index.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    return path


def _write_registry_with_skill_asset(
    tmp_path: Path,
    *,
    destination: str = "skills",
    sha256: str | None = None,
) -> Path:
    repo = tmp_path / "repo"
    asset_dir = repo / "assets" / "skills"
    payload_dir = tmp_path / "payload" / "creative" / "sample-skill"
    registry_dir = repo / "registry"
    asset_dir.mkdir(parents=True)
    payload_dir.mkdir(parents=True)
    (payload_dir / "SKILL.md").write_text(
        "---\nname: sample-skill\ndescription: packaged skill\n---\n\n# Sample\n",
        encoding="utf-8",
    )
    archive_path = asset_dir / "skills-creative.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(payload_dir.parent, arcname="creative")
    actual_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()

    registry = {
        "schema_version": 1,
        "generated_at": "2026-05-29T00:00:00Z",
        "package_count": 1,
        "packages": {
            "skills-creative": {
                "name": "skills-creative",
                "display_name": "Creative Skills",
                "version": "0.1.0",
                "type": "skill",
                "channel": "skills",
                "description": "Creative skill pack.",
                "dependencies": [],
                "install": {
                    "python_extras": [],
                    "python_packages": [],
                    "system_packages": [],
                    "npm_packages": [],
                    "optional_assets": [
                        {
                            "type": "skill_pack",
                            "source": "assets/skills/skills-creative.tar.gz",
                            "format": "tar.gz",
                            "sha256": sha256 if sha256 is not None else actual_sha,
                            "destination": destination,
                        }
                    ],
                },
                "tools": {"toolsets": [], "tools": []},
                "permissions": {
                    "network": False,
                    "filesystem": True,
                    "shell": False,
                    "browser": False,
                    "audio": False,
                    "microphone": False,
                    "secrets": [],
                },
                "env": {"required": [], "optional": []},
                "security": {"post_install_scripts": False, "signed": False, "checksum": actual_sha},
                "manifest_path": "packages/skills/skills-creative/package.toml",
                "manifest_sha256": "2" * 64,
            }
        },
    }
    registry_dir.mkdir(parents=True)
    path = registry_dir / "index.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    return path


def _write_registry_with_profile_bundle(tmp_path: Path) -> Path:
    path = _write_registry_with_browser_dependency(tmp_path)
    registry = json.loads(path.read_text(encoding="utf-8"))
    registry["package_count"] = 3
    registry["packages"]["profile-developer"] = {
        "name": "profile-developer",
        "display_name": "Developer Profile",
        "version": "0.1.0",
        "type": "bundle",
        "channel": "community",
        "description": "Coding agent profile.",
        "dependencies": ["web-search", "browser"],
        "install": {
            "python_extras": [],
            "python_packages": [],
            "system_packages": [],
            "npm_packages": [],
            "optional_assets": [],
        },
        "tools": {"toolsets": [], "tools": []},
        "permissions": {
            "network": True,
            "filesystem": True,
            "shell": False,
            "browser": True,
            "audio": False,
            "microphone": False,
            "secrets": [],
        },
        "env": {"required": [], "optional": []},
        "security": {"post_install_scripts": False, "signed": False, "checksum": ""},
        "manifest_path": "packages/community/profile-developer/package.toml",
        "manifest_sha256": "4" * 64,
    }
    path.write_text(json.dumps(registry), encoding="utf-8")
    return path


def _write_registry_with_runtime_dependency(tmp_path: Path) -> Path:
    path = _write_registry_with_browser_dependency(tmp_path)
    registry = json.loads(path.read_text(encoding="utf-8"))
    registry["package_count"] = 3
    registry["packages"]["browser-engine"] = {
        "name": "browser-engine",
        "display_name": "Headless Chromium Browser Engine",
        "version": "0.1.0",
        "type": "bundle",
        "channel": "official",
        "description": "Installs Node.js, agent-browser, and a local Chromium/headless-shell runtime.",
        "dependencies": ["browser"],
        "install": {
            "python_extras": [],
            "python_packages": [],
            "system_packages": [],
            "npm_packages": [],
            "runtime_dependencies": ["browser"],
            "optional_assets": [],
        },
        "tools": {"toolsets": [], "tools": []},
        "permissions": {
            "network": True,
            "filesystem": True,
            "shell": True,
            "browser": True,
            "audio": False,
            "microphone": False,
            "secrets": [],
        },
        "env": {"required": [], "optional": []},
        "security": {"post_install_scripts": True, "signed": False, "checksum": ""},
        "manifest_path": "packages/official/browser-engine/package.toml",
        "manifest_sha256": "5" * 64,
    }
    path.write_text(json.dumps(registry), encoding="utf-8")
    return path


# Package contents metadata helpers.
def _write_registry_with_skill_contents(tmp_path: Path) -> Path:
    path = _write_registry(tmp_path)
    registry = json.loads(path.read_text(encoding="utf-8"))
    package = registry["packages"].pop("web-search")
    package.update({
        "name": "skills-dev-core",
        "display_name": "Developer Core Skills",
        "type": "skill",
        "channel": "skills",
        "description": "Developer workflow skills.",
        "contents": {
            "skills": [
                "software-development/writing-plans",
                "software-development/test-driven-development",
                "github/github-pr-workflow",
            ]
        },
        "manifest_path": "packages/skills/skills-dev-core/package.toml",
    })
    package["install"]["python_extras"] = []
    package["permissions"]["network"] = False
    package["permissions"]["filesystem"] = True
    package["tools"] = {"toolsets": [], "tools": []}
    registry["packages"]["skills-dev-core"] = package
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


def test_relative_remote_asset_source_resolves_from_default_github_registry():
    url = pkg_cli._resolve_remote_asset_source(
        "assets/skills/skills-creative.tar.gz",
        registry_module.DEFAULT_REGISTRY_URL,
    )

    assert url == (
        "https://raw.githubusercontent.com/quarker1337/Hermes-Packages/main/"
        "assets/skills/skills-creative.tar.gz"
    )


def test_registry_update_decodes_github_contents_api_payload(tmp_path, monkeypatch):
    source = _write_registry(tmp_path)
    api_payload = json.dumps({
        "name": "index.json",
        "encoding": "base64",
        "content": base64.b64encode(source.read_bytes()).decode("ascii"),
    }).encode("utf-8")

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return api_payload

    monkeypatch.setattr(registry_module.urllib.request, "urlopen", lambda *args, **kwargs: Response())

    registry = PackageRegistry(home=tmp_path / "home")
    index = registry.update(registry_module.DEFAULT_REGISTRY_URL, timeout=1)

    assert index["package_count"] == 1
    assert registry.get("web-search")["version"] == "0.1.0"


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


def test_install_dry_run_prints_npm_and_runtime_work(tmp_path, capsys):
    source = _write_registry_with_app_asset(tmp_path)
    home = tmp_path / "home"

    rc = pkg_cli.main(["--home", str(home), "--source", str(source), "install", "desktop", "--dry-run"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "desktop 0.1.0" in out
    assert "Optional assets: apps/desktop-workspace" in out
    assert "Runtime dependencies: node" in out
    assert "NPM packages: electron workspace dependencies" in out
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
    assert installed["web-search"]["status"] == "installed"
    assert installed["web-search"]["install_reason"] == "manual"
    assert installed["web-search"]["requested"] is True


def test_install_runtime_dependency_package_runs_explicit_ensure(tmp_path, monkeypatch, capsys):
    from hermes_cli import dep_ensure

    source = _write_registry_with_runtime_dependency(tmp_path)
    home = tmp_path / "home"
    calls = []

    def fake_ensure_dependency(dep, **kwargs):
        calls.append((dep, kwargs))
        return True

    monkeypatch.setattr(dep_ensure, "ensure_dependency", fake_ensure_dependency)

    rc = pkg_cli.main([
        "--home",
        str(home),
        "--source",
        str(source),
        "install",
        "browser-engine",
        "--yes",
        "--no-pip",
    ])

    out = capsys.readouterr().out
    assert rc == 0
    assert "Runtime dependencies: browser" in out
    assert "Installing runtime dependency: browser" in out
    assert calls == [(
        "browser",
        {
            "interactive": False,
            "respect_decline": False,
            "home": home,
            "force": True,
        },
    )]
    installed = PackageState(home=home).installed
    assert installed["browser-engine"]["runtime_dependencies"] == ["browser"]
    assert installed["browser-engine"]["dependencies"] == ["browser"]
    assert installed["browser-engine"]["install_reason"] == "manual"
    assert installed["browser"]["install_reason"] == "dependency"


def test_install_yes_uses_uv_for_python_extras_in_pipless_venv(tmp_path, monkeypatch, capsys):
    source = _write_registry(tmp_path)
    home = tmp_path / "home"
    calls = []

    monkeypatch.setattr(pkg_cli.shutil, "which", lambda name: "/tmp/uv" if name == "uv" else None)
    monkeypatch.setattr(pkg_cli.sys, "executable", "/tmp/hermes-venv/bin/python3")

    def fake_check_call(cmd, cwd=None):
        calls.append((cmd, cwd))
        return 0

    monkeypatch.setattr(pkg_cli.subprocess, "check_call", fake_check_call)

    rc = pkg_cli.main([
        "--home",
        str(home),
        "--source",
        str(source),
        "install",
        "web-search",
        "--yes",
    ])

    out = capsys.readouterr().out
    assert rc == 0
    assert "Installed web-search 0.1.0" in out
    assert calls
    cmd, _cwd = calls[0]
    assert cmd[:5] == ["/tmp/uv", "pip", "install", "--python", "/tmp/hermes-venv/bin/python3"]
    assert "-m" not in cmd
    assert "pip" not in cmd[5:]


def test_python_extra_target_preserves_remote_archive_install_source(monkeypatch, tmp_path):
    class FakeDistribution:
        def read_text(self, name):
            assert name == "direct_url.json"
            return json.dumps({
                "url": "https://github.com/quarker1337/nanoHermes/archive/refs/heads/main.tar.gz",
                "archive_info": {"hash": "sha256=abc"},
            })

    monkeypatch.setattr(pkg_cli, "_editable_project_root", lambda: None)
    monkeypatch.setattr(
        pkg_cli.importlib_metadata,
        "distribution",
        lambda distribution_name: FakeDistribution(),
    )

    target, cwd, editable = pkg_cli._python_extras_install_target(["browser"])

    assert target == (
        "hermes-agent[browser] @ "
        "https://github.com/quarker1337/nanoHermes/archive/refs/heads/main.tar.gz"
    )
    assert cwd is None
    assert editable is False


def test_python_extra_target_preserves_local_directory_install_source(monkeypatch, tmp_path):
    class FakeDistribution:
        def read_text(self, name):
            assert name == "direct_url.json"
            return json.dumps({
                "url": "file:///home/wayne/hans/nanoHermes",
                "dir_info": {},
            })

    monkeypatch.setattr(pkg_cli, "_editable_project_root", lambda: None)
    monkeypatch.setattr(
        pkg_cli.importlib_metadata,
        "distribution",
        lambda distribution_name: FakeDistribution(),
    )

    target, cwd, editable = pkg_cli._python_extras_install_target(["dashboard", "cron"])

    assert target == "hermes-agent[cron,dashboard] @ file:///home/wayne/hans/nanoHermes"
    assert cwd is None
    assert editable is False


def test_install_optional_python_asset_extracts_into_site_packages(tmp_path, monkeypatch, capsys):
    source = _write_registry_with_python_asset(tmp_path)
    home = tmp_path / "home"
    site_packages = tmp_path / "venv" / "lib" / "python3.11" / "site-packages"
    site_packages.mkdir(parents=True)

    class FakeSysConfig:
        @staticmethod
        def get_paths():
            return {"purelib": str(site_packages)}

    monkeypatch.setattr(pkg_cli, "sysconfig", FakeSysConfig, raising=False)

    rc = pkg_cli.main([
        "--home",
        str(home),
        "--source",
        str(source),
        "install",
        "dashboard",
        "--yes",
        "--no-pip",
    ])

    captured = capsys.readouterr()
    assert rc == 0
    assert "Optional assets: python-site-packages/hermes_cli" in captured.out
    assert "Installed asset for dashboard -> python-site-packages/hermes_cli" in captured.out
    assert (site_packages / "hermes_cli" / "kanban.py").read_text(encoding="utf-8") == "PACKAGED_KANBAN = True\n"
    installed = PackageState(home=home).installed
    assert installed["dashboard"]["toolsets"] == ["kanban"]
    assert installed["dashboard"]["optional_assets"][0]["destination"] == "python-site-packages/hermes_cli"


def test_install_optional_python_asset_keeps_existing_site_package_files_by_default(tmp_path, monkeypatch, capsys):
    source = _write_registry_with_python_asset(
        tmp_path,
        members={
            "main.py": "MALICIOUS_REPLACEMENT = True\n",
            "dashboard_auth/new_file.py": "PACKAGED_DASHBOARD_AUTH=True\n",
        },
    )
    home = tmp_path / "home"
    site_packages = tmp_path / "venv" / "lib" / "python3.11" / "site-packages"
    hermes_cli_dir = site_packages / "hermes_cli"
    hermes_cli_dir.mkdir(parents=True)
    existing_main = hermes_cli_dir / "main.py"
    existing_main.write_text("CORE_MAIN = True\n", encoding="utf-8")

    class FakeSysConfig:
        @staticmethod
        def get_paths():
            return {"purelib": str(site_packages)}

    monkeypatch.setattr(pkg_cli, "sysconfig", FakeSysConfig, raising=False)

    rc = pkg_cli.main([
        "--home",
        str(home),
        "--source",
        str(source),
        "install",
        "dashboard",
        "--yes",
        "--no-pip",
    ])

    captured = capsys.readouterr()
    assert rc == 0
    assert "1 files copied, 1 existing kept" in captured.out
    assert existing_main.read_text(encoding="utf-8") == "CORE_MAIN = True\n"
    assert (
        site_packages / "hermes_cli" / "dashboard_auth" / "new_file.py"
    ).read_text(encoding="utf-8") == "PACKAGED_DASHBOARD_AUTH=True\n"


def test_install_optional_python_asset_requires_site_package_subdir(tmp_path, monkeypatch, capsys):
    source = _write_registry_with_python_asset(tmp_path, destination="python-site-packages")
    home = tmp_path / "home"
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()

    class FakeSysConfig:
        @staticmethod
        def get_paths():
            return {"purelib": str(site_packages)}

    monkeypatch.setattr(pkg_cli, "sysconfig", FakeSysConfig, raising=False)

    rc = pkg_cli.main([
        "--home",
        str(home),
        "--source",
        str(source),
        "install",
        "dashboard",
        "--yes",
        "--no-pip",
    ])

    captured = capsys.readouterr()
    assert rc == 1
    assert "python-site-packages asset destination must include a package subdirectory" in captured.err
    assert not PackageState(home=home).installed


def test_install_optional_app_asset_extracts_into_hermes_home_apps(tmp_path, monkeypatch, capsys):
    source = _write_registry_with_app_asset(tmp_path)
    home = tmp_path / "home"

    from hermes_cli import dep_ensure

    monkeypatch.setattr(dep_ensure, "ensure_dependency", lambda dep, **kwargs: True)

    rc = pkg_cli.main([
        "--home",
        str(home),
        "--source",
        str(source),
        "install",
        "desktop",
        "--yes",
        "--no-pip",
    ])

    captured = capsys.readouterr()
    assert rc == 0
    assert "Optional assets: apps/desktop-workspace" in captured.out
    assert "Installed asset for desktop -> apps/desktop-workspace" in captured.out
    assert (
        home / "apps" / "desktop-workspace" / "apps" / "desktop" / "package.json"
    ).read_text(encoding="utf-8") == '{"name": "hermes"}\n'
    assert (
        home / "apps" / "desktop-workspace" / "apps" / "shared" / "package.json"
    ).read_text(encoding="utf-8") == '{"name": "@hermes/shared"}\n'
    installed = PackageState(home=home).installed
    assert installed["desktop"]["optional_assets"][0]["destination"] == "apps/desktop-workspace"


def test_install_optional_app_asset_requires_app_subdir(tmp_path, monkeypatch, capsys):
    source = _write_registry_with_app_asset(tmp_path, destination="apps")
    home = tmp_path / "home"

    from hermes_cli import dep_ensure

    monkeypatch.setattr(dep_ensure, "ensure_dependency", lambda dep, **kwargs: True)

    rc = pkg_cli.main([
        "--home",
        str(home),
        "--source",
        str(source),
        "install",
        "desktop",
        "--yes",
        "--no-pip",
    ])

    captured = capsys.readouterr()
    assert rc == 1
    assert "apps asset destination must include an app subdirectory" in captured.err
    assert not PackageState(home=home).installed


def test_install_optional_skill_asset_extracts_into_hermes_home(tmp_path, capsys):
    source = _write_registry_with_skill_asset(tmp_path)
    home = tmp_path / "home"

    rc = pkg_cli.main([
        "--home",
        str(home),
        "--source",
        str(source),
        "install",
        "skills-creative",
        "--yes",
        "--no-pip",
    ])

    captured = capsys.readouterr()
    assert rc == 0
    assert "Optional assets: skills" in captured.out
    assert "Installed asset for skills-creative -> skills" in captured.out
    skill_md = home / "skills" / "creative" / "sample-skill" / "SKILL.md"
    assert "name: sample-skill" in skill_md.read_text(encoding="utf-8")
    installed = PackageState(home=home).installed
    assert installed["skills-creative"]["optional_assets"][0]["destination"] == "skills"


def test_install_optional_asset_checksum_mismatch_does_not_record_state(tmp_path, capsys):
    source = _write_registry_with_skill_asset(tmp_path, sha256="0" * 64)
    home = tmp_path / "home"

    rc = pkg_cli.main([
        "--home",
        str(home),
        "--source",
        str(source),
        "install",
        "skills-creative",
        "--yes",
        "--no-pip",
    ])

    captured = capsys.readouterr()
    assert rc == 1
    assert "checksum mismatch" in captured.err
    assert not PackageState(home=home).installed
    assert not (home / "skills" / "creative").exists()


def test_install_optional_asset_rejects_unsafe_destination(tmp_path, capsys):
    source = _write_registry_with_skill_asset(tmp_path, destination="../skills")
    home = tmp_path / "home"

    rc = pkg_cli.main([
        "--home",
        str(home),
        "--source",
        str(source),
        "install",
        "skills-creative",
        "--yes",
        "--no-pip",
    ])

    captured = capsys.readouterr()
    assert rc == 1
    assert "Unsafe package asset destination" in captured.err
    assert not PackageState(home=home).installed


def test_install_records_core_package_database_with_dependency_reasons(tmp_path, capsys):
    source = _write_registry_with_browser_dependency(tmp_path)
    home = tmp_path / "home"

    rc = pkg_cli.main([
        "--home",
        str(home),
        "--source",
        str(source),
        "install",
        "browser",
        "--yes",
        "--no-pip",
    ])

    capsys.readouterr()
    assert rc == 0
    state = PackageState(home=home)
    db = state.load()
    installed = db["installed"]
    assert db["schema_version"] == 1
    assert installed["browser"]["install_reason"] == "manual"
    assert installed["browser"]["requested"] is True
    assert installed["browser"]["dependencies"] == ["web-search"]
    assert installed["browser"]["python_extras"] == []
    assert installed["web-search"]["install_reason"] == "dependency"
    assert installed["web-search"]["requested"] is False
    assert installed["web-search"]["source"] == str(source)
    assert state.installed_toolsets() == ["browser", "web"]
    assert state.installed_tools() == ["browser_navigate", "browser_snapshot", "web_extract", "web_search"]
    assert state.package_for_toolset("web") == "web-search"


def test_show_accepts_unhyphenated_package_name(tmp_path, capsys):
    source = _write_registry(tmp_path)
    home = tmp_path / "home"
    assert pkg_cli.main(["--home", str(home), "--source", str(source), "update"]) == 0
    capsys.readouterr()

    rc = pkg_cli.main(["--home", str(home), "show", "websearch"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "web-search 0.1.0" in captured.out
    assert "Traceback" not in captured.err


def test_show_prints_included_skills(tmp_path, capsys):
    source = _write_registry_with_skill_contents(tmp_path)
    home = tmp_path / "home"
    assert pkg_cli.main(["--home", str(home), "--source", str(source), "update"]) == 0
    capsys.readouterr()

    rc = pkg_cli.main(["--home", str(home), "show", "skills-dev-core"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "Included skills:" in captured.out
    assert "software-development/writing-plans" in captured.out
    assert "github/github-pr-workflow" in captured.out


def test_show_prints_package_dependencies_for_profile_bundles(tmp_path, capsys):
    source = _write_registry_with_profile_bundle(tmp_path)
    home = tmp_path / "home"
    assert pkg_cli.main(["--home", str(home), "--source", str(source), "update"]) == 0
    capsys.readouterr()

    rc = pkg_cli.main(["--home", str(home), "show", "profile-developer"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "Dependencies:" in captured.out
    assert "web-search" in captured.out
    assert "browser" in captured.out


def test_search_matches_included_skill_names(tmp_path, capsys):
    source = _write_registry_with_skill_contents(tmp_path)
    home = tmp_path / "home"
    assert pkg_cli.main(["--home", str(home), "--source", str(source), "update"]) == 0
    capsys.readouterr()

    rc = pkg_cli.main(["--home", str(home), "search", "github-pr-workflow"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "skills-dev-core 0.1.0" in captured.out


def test_show_unknown_package_is_user_friendly(tmp_path, capsys):
    source = _write_registry(tmp_path)
    home = tmp_path / "home"
    assert pkg_cli.main(["--home", str(home), "--source", str(source), "update"]) == 0
    capsys.readouterr()

    rc = pkg_cli.main(["--home", str(home), "show", "web-serch"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "Package not found: web-serch" in captured.err
    assert "Did you mean: web-search" in captured.err
    assert "Traceback" not in captured.err


def test_install_unknown_package_is_user_friendly(tmp_path, capsys):
    source = _write_registry(tmp_path)
    home = tmp_path / "home"

    rc = pkg_cli.main(["--home", str(home), "--source", str(source), "install", "web-serch", "--dry-run"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "Package not found: web-serch" in captured.err
    assert "Did you mean: web-search" in captured.err
    assert "Traceback" not in captured.err


def test_search_without_registry_cache_is_user_friendly(tmp_path, capsys):
    rc = pkg_cli.main(["--home", str(tmp_path / "home"), "search", "web"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "No package registry cache" in captured.err
    assert "hermes pkg update" in captured.err
    assert "Traceback" not in captured.err


def test_registry_http_update_has_wall_clock_timeout(tmp_path, monkeypatch):
    def stalled_urlopen(*args, **kwargs):
        time.sleep(1)
        raise AssertionError("the registry fetch should have timed out already")

    monkeypatch.setattr(registry_module.urllib.request, "urlopen", stalled_urlopen)
    start = time.monotonic()

    with pytest.raises(PackageRegistryError, match="Timed out fetching package registry"):
        PackageRegistry(home=tmp_path / "home").update("https://example.invalid/index.json", timeout=0.05)

    assert time.monotonic() - start < 0.5


def test_pkg_update_timeout_failure_is_user_friendly(tmp_path, monkeypatch, capsys):
    def failed_update(self, source, *, timeout):
        raise PackageRegistryError(f"Timed out fetching package registry after {timeout:g}s: {source}")

    monkeypatch.setattr(PackageRegistry, "update", failed_update)

    rc = pkg_cli.main(["--home", str(tmp_path / "home"), "update", "--timeout", "0.1"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "Package registry update failed" in captured.err
    assert "--timeout 60" in captured.err
    assert "Traceback" not in captured.err


def test_pkg_install_default_timeout_allows_large_package_assets():
    parser = pkg_cli.build_parser()

    install_args = parser.parse_args(["install", "desktop-client"])
    update_args = parser.parse_args(["update"])

    assert install_args.timeout == pkg_cli.DEFAULT_INSTALL_TIMEOUT_SECONDS
    assert install_args.timeout > registry_module.DEFAULT_REGISTRY_TIMEOUT_SECONDS
    assert update_args.timeout == registry_module.DEFAULT_REGISTRY_TIMEOUT_SECONDS


def test_pkg_update_accepts_timeout_after_subcommand(tmp_path, monkeypatch, capsys):
    seen = {}

    def fake_update(self, source, *, timeout):
        seen["timeout"] = timeout
        return {"package_count": 0, "packages": {}}

    monkeypatch.setattr(PackageRegistry, "update", fake_update)

    rc = pkg_cli.main(["--home", str(tmp_path / "home"), "update", "--timeout", "3"])

    capsys.readouterr()
    assert rc == 0
    assert seen["timeout"] == 3


def test_pkg_and_plug_are_builtin_cli_commands():
    from hermes_cli.main import _BUILTIN_SUBCOMMANDS

    assert "pkg" in _BUILTIN_SUBCOMMANDS
    assert "plug" in _BUILTIN_SUBCOMMANDS
    assert "desktop" in _BUILTIN_SUBCOMMANDS
    assert "gui" in _BUILTIN_SUBCOMMANDS


def _hide_kanban_module(monkeypatch):
    monkeypatch.delitem(sys.modules, "hermes_cli.kanban", raising=False)
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "hermes_cli.kanban":
            raise ModuleNotFoundError(
                "No module named 'hermes_cli.kanban'",
                name="hermes_cli.kanban",
            )
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_top_level_hermes_help_tolerates_missing_package_managed_kanban(monkeypatch, capsys):
    from hermes_cli import main as hermes_main

    _hide_kanban_module(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["hermes", "setup", "--help"])

    with pytest.raises(SystemExit) as excinfo:
        hermes_main.main()

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "usage: hermes setup" in captured.out
    assert "ModuleNotFoundError" not in captured.err


def test_top_level_hermes_kanban_without_package_prints_install_hint(monkeypatch, capsys):
    from hermes_cli import main as hermes_main

    _hide_kanban_module(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["hermes", "kanban", "list"])

    rc = hermes_main.main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "Kanban is not installed in this NanoHermes base install" in captured.err
    assert "hermes pkg install dashboard --yes" in captured.err
    assert "ModuleNotFoundError" not in captured.err


def test_top_level_hermes_desktop_without_package_prints_install_hint(tmp_path, monkeypatch, capsys):
    from hermes_cli import main as hermes_main

    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(sys, "argv", ["hermes", "desktop", "--skip-build"])

    rc = hermes_main.main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "Desktop app is not installed in this NanoHermes base install" in captured.err
    assert "hermes pkg install desktop --yes" in captured.err
    assert "Node/Electron" in captured.err


def test_desktop_build_ref_env_falls_back_to_installed_asset_sha(tmp_path, monkeypatch):
    from hermes_cli import main as hermes_main

    home = tmp_path / "home"
    digest = "abcdef0123456789" * 4
    PackageState(home=home).mark_installed(
        {
            "name": "desktop",
            "display_name": "Hermes Desktop",
            "version": "0.1.0",
            "type": "bundle",
            "channel": "official",
            "description": "Desktop app package.",
            "dependencies": [],
            "install": {
                "python_extras": [],
                "python_packages": [],
                "system_packages": [],
                "npm_packages": ["electron workspace dependencies"],
                "runtime_dependencies": ["node"],
                "optional_assets": [
                    {
                        "type": "app_asset",
                        "source": "assets/apps/desktop-workspace.tar.gz",
                        "format": "tar.gz",
                        "sha256": digest,
                        "destination": "apps/desktop-workspace",
                    }
                ],
            },
            "tools": {"toolsets": [], "tools": []},
            "permissions": {},
            "env": {},
            "manifest_path": "packages/official/desktop/package.toml",
            "manifest_sha256": "7" * 64,
        }
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(hermes_main, "_runtime_git_ref", lambda: None)

    env: dict[str, str] = {}
    hermes_main._ensure_desktop_build_ref_env(env)

    assert env["GITHUB_SHA"] == digest[:40]
    assert env["GITHUB_REF_NAME"] == "package-managed"


def test_top_level_hermes_pkg_returns_subcommand_exit_code(tmp_path, monkeypatch, capsys):
    from hermes_cli import main as hermes_main

    monkeypatch.setattr(sys, "argv", ["hermes", "pkg", "--home", str(tmp_path / "home"), "search", "web"])

    assert hermes_main.main() == 1
    captured = capsys.readouterr()
    assert "No package registry cache" in captured.err
