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


def test_external_desktop_app_data_paths_recognizes_renderer_local_storage_marker(
    monkeypatch,
    tmp_path: Path,
):
    hermes_home = tmp_path / ".hermes"
    external = tmp_path / "xdg-config" / "Hermes"
    leveldb = external / "Local Storage" / "leveldb"
    leveldb.mkdir(parents=True)
    (leveldb / "000003.log").write_bytes(b"\x00hermes-dashboard-theme\x00dark")

    monkeypatch.setattr(uninstall, "desktop_app_data_candidates", lambda: [external])

    assert uninstall.external_desktop_app_data_paths(hermes_home) == [external]


def test_external_desktop_app_data_paths_ignores_plain_chromium_cache_without_marker(
    monkeypatch,
    tmp_path: Path,
):
    hermes_home = tmp_path / ".hermes"
    external = tmp_path / "xdg-config" / "Hermes"
    cache = external / "Cache" / "Cache_Data"
    cache.mkdir(parents=True)
    (cache / "data_0").write_bytes(b"generic chromium cache")

    monkeypatch.setattr(uninstall, "desktop_app_data_candidates", lambda: [external])

    assert uninstall.external_desktop_app_data_paths(hermes_home) == []


def test_remove_external_desktop_app_data_removes_recognized_dir_not_internal(monkeypatch, tmp_path: Path):
    hermes_home = tmp_path / ".hermes"
    external = tmp_path / "xdg-config" / "Hermes"
    leveldb = external / "Local Storage" / "leveldb"
    leveldb.mkdir(parents=True)
    (leveldb / "000003.log").write_bytes(b"\x00hermes-dashboard-theme\x00dark")
    (external / "Cache").mkdir()
    (external / "Cache" / "blob").write_text("cache", encoding="utf-8")

    internal = hermes_home / "apps" / "desktop-client" / "user-data"
    internal.mkdir(parents=True)
    (internal / "connection.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(uninstall, "desktop_app_data_candidates", lambda: [external, internal])

    assert uninstall.remove_external_desktop_app_data(hermes_home) == [external]
    assert not external.exists()
    assert internal.exists()
