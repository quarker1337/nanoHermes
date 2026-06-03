"""Tests for the remote-only package-managed Desktop client command."""

from __future__ import annotations

import argparse
import json
import stat
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_cli import main as cli_main


def _ns(**kw):
    defaults = dict(
        skip_build=False,
        build_only=False,
        source=False,
        fake_boot=False,
        ignore_existing=False,
        hermes_root=None,
        cwd=None,
        remote_url=None,
        remote_token=None,
        remote_token_file=None,
        desktop_user_data_dir=None,
        desktop_client_mode=False,
        load_desktop_client_connection=False,
        require_remote=False,
        launch=False,
        yes=False,
        dry_run=False,
        registry_source=None,
        package="desktop-client",
    )
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def _make_desktop_tree(tmp_path: Path) -> Path:
    root = tmp_path / "desktop-workspace"
    desktop_dir = root / "apps" / "desktop"
    desktop_dir.mkdir(parents=True)
    (desktop_dir / "package.json").write_text("{}", encoding="utf-8")
    return root


def _make_packaged_executable(root: Path, monkeypatch, platform: str = "linux") -> Path:
    monkeypatch.setattr(cli_main.sys, "platform", platform)
    desktop_dir = root / "apps" / "desktop"
    if platform == "darwin":
        exe = desktop_dir / "release" / "mac-arm64" / "Hermes.app" / "Contents" / "MacOS" / "Hermes"
    elif platform == "win32":
        exe = desktop_dir / "release" / "win-unpacked" / "Hermes.exe"
    else:
        exe = desktop_dir / "release" / "linux-unpacked" / "hermes"
    exe.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    return exe


def test_desktop_client_install_saves_remote_config_without_local_runtime(tmp_path):
    token_file = tmp_path / "token.txt"
    token_file.write_text("secret-token\n", encoding="utf-8")
    user_data = tmp_path / "desktop-client-user-data"

    with patch("hermes_cli.package_manager.cli.main", return_value=0) as mock_pkg, \
         patch("hermes_cli.main._run_desktop", return_value=0) as mock_run:
        rc = cli_main.cmd_desktop_client_install(_ns(
            yes=True,
            dry_run=False,
            registry_source=str(tmp_path / "registry.json"),
            remote_url="https://gateway.example.test/",
            remote_token_file=str(token_file),
            desktop_user_data_dir=str(user_data),
            skip_build=True,
            launch=False,
        ))

    assert rc == 0
    mock_pkg.assert_called_once_with([
        "--source", str(tmp_path / "registry.json"),
        "install", "desktop-client",
        "--yes", "--no-pip",
    ])
    mock_run.assert_not_called()

    connection_path = user_data / "connection.json"
    payload = json.loads(connection_path.read_text(encoding="utf-8"))
    assert payload == {
        "mode": "remote",
        "remote": {
            "url": "https://gateway.example.test",
            "token": {"encoding": "plain", "value": "secret-token"},
        },
    }
    assert stat.S_IMODE(connection_path.stat().st_mode) == 0o600


def test_desktop_client_launch_loads_saved_remote_config_and_skips_local_bootstrap(tmp_path, monkeypatch):
    root = _make_desktop_tree(tmp_path)
    desktop_dir = root / "apps" / "desktop"
    monkeypatch.setattr(cli_main, "_desktop_workspace_root", lambda: root)
    packaged_exe = _make_packaged_executable(root, monkeypatch)
    user_data = tmp_path / "client-user-data"
    cli_main._write_desktop_client_connection(user_data, "https://gateway.example.test/api/", "secret-token")

    launch_ok = subprocess.CompletedProcess([str(packaged_exe)], 0)

    with patch("hermes_cli.main.subprocess.run", return_value=launch_ok) as mock_run:
        rc = cli_main.cmd_desktop_client_launch(_ns(
            desktop_user_data_dir=str(user_data),
            skip_build=True,
        ))

    assert rc == 0
    mock_run.assert_called_once()
    assert mock_run.call_args.args[0] == [str(packaged_exe)]
    assert mock_run.call_args.kwargs["cwd"] == desktop_dir
    launch_env = mock_run.call_args.kwargs["env"]
    assert launch_env["HERMES_DESKTOP_USER_DATA_DIR"] == str(user_data)
    assert launch_env["HERMES_DESKTOP_REMOTE_URL"] == "https://gateway.example.test/api"
    assert launch_env["HERMES_DESKTOP_REMOTE_TOKEN"] == "secret-token"
    assert "HERMES_DESKTOP_BOOT_FAKE" not in launch_env
    assert "HERMES_DESKTOP_HERMES_ROOT" not in launch_env


def test_desktop_client_launch_requires_remote_config(tmp_path, monkeypatch, capsys):
    root = _make_desktop_tree(tmp_path)
    monkeypatch.setattr(cli_main, "_desktop_workspace_root", lambda: root)
    _make_packaged_executable(root, monkeypatch)

    rc = cli_main.cmd_desktop_client_launch(_ns(
        desktop_user_data_dir=str(tmp_path / "empty-user-data"),
        skip_build=True,
    ))

    assert rc == 2
    assert "Remote gateway URL/token required" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        ["hermes", "desktop-client"],
        ["hermes", "-m", "gpt5", "desktop-client"],
    ],
)
def test_desktop_client_is_known_builtin_for_plugin_gating(argv):
    with patch.object(sys, "argv", argv):
        assert cli_main._plugin_cli_discovery_needed() is False
