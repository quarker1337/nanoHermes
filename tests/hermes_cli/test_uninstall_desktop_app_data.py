from __future__ import annotations

from pathlib import Path

from hermes_cli import uninstall


def test_desktop_app_data_candidates_include_linux_xdg_and_override(monkeypatch, tmp_path: Path):
    override = tmp_path / "override-user-data"
    xdg_config = tmp_path / "xdg-config"

    monkeypatch.setattr(uninstall.sys, "platform", "linux")
    monkeypatch.setenv("HERMES_DESKTOP_USER_DATA_DIR", str(override))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))

    assert uninstall.desktop_app_data_candidates() == [
        override,
        xdg_config / "Hermes",
        xdg_config / "hermes",
    ]


def test_external_desktop_app_data_paths_only_recognized_outside_hermes_home(monkeypatch, tmp_path: Path):
    hermes_home = tmp_path / ".hermes"
    external = tmp_path / "xdg-config" / "Hermes"
    external.mkdir(parents=True)
    (external / "connection.json").write_text("{}", encoding="utf-8")

    unrecognized = tmp_path / "xdg-config" / "hermes"
    unrecognized.mkdir(parents=True)

    internal = hermes_home / "apps" / "desktop-client" / "user-data"
    internal.mkdir(parents=True)
    (internal / "connection.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(uninstall, "desktop_app_data_candidates", lambda: [external, unrecognized, internal])

    assert uninstall.external_desktop_app_data_paths(hermes_home) == [external]


def test_remove_external_desktop_app_data_removes_recognized_dir_not_internal(monkeypatch, tmp_path: Path):
    hermes_home = tmp_path / ".hermes"
    external = tmp_path / "xdg-config" / "Hermes"
    (external / "Cache").mkdir(parents=True)
    (external / "connection.json").write_text("{}", encoding="utf-8")
    (external / "Cache" / "blob").write_text("cache", encoding="utf-8")

    internal = hermes_home / "apps" / "desktop-client" / "user-data"
    internal.mkdir(parents=True)
    (internal / "connection.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(uninstall, "desktop_app_data_candidates", lambda: [external, internal])

    assert uninstall.remove_external_desktop_app_data(hermes_home) == [external]
    assert not external.exists()
    assert internal.exists()
