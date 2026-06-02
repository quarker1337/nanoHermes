from types import SimpleNamespace


def test_postinstall_skips_browser_dependency_when_browser_package_not_installed(monkeypatch, capsys):
    """NanoHermes base postinstall must not prompt for optional browser tooling."""
    from hermes_cli import main as cli_main

    calls = []

    class NoPackagesInstalled:
        def package_for_toolset(self, toolset):
            return None

    def fake_ensure(dep, interactive=True, respect_decline=True):
        calls.append((dep, interactive, respect_decline))
        return True

    monkeypatch.setattr("hermes_cli.config.stamp_install_method", lambda method: None)
    monkeypatch.setattr("hermes_cli.package_manager.state.PackageState", NoPackagesInstalled)
    monkeypatch.setattr("hermes_cli.dep_ensure.ensure_dependency", fake_ensure)
    monkeypatch.setattr(cli_main, "_has_any_provider_configured", lambda: True)

    cli_main.cmd_postinstall(SimpleNamespace())

    assert calls == [
        ("node", True, False),
        ("ripgrep", True, False),
        ("ffmpeg", True, False),
    ]
    assert "Post-install complete" in capsys.readouterr().out


def test_postinstall_includes_browser_dependency_when_browser_package_installed(monkeypatch, capsys):
    """If the browser package/toolset is installed, postinstall remains an explicit setup path."""
    from hermes_cli import main as cli_main

    calls = []

    class BrowserPackageInstalled:
        def package_for_toolset(self, toolset):
            return "browser" if toolset == "browser" else None

    def fake_ensure(dep, interactive=True, respect_decline=True):
        calls.append((dep, interactive, respect_decline))
        return True

    monkeypatch.setattr("hermes_cli.config.stamp_install_method", lambda method: None)
    monkeypatch.setattr("hermes_cli.package_manager.state.PackageState", BrowserPackageInstalled)
    monkeypatch.setattr("hermes_cli.dep_ensure.ensure_dependency", fake_ensure)
    monkeypatch.setattr(cli_main, "_has_any_provider_configured", lambda: True)

    cli_main.cmd_postinstall(SimpleNamespace())

    assert calls == [
        ("node", True, False),
        ("browser", True, False),
        ("ripgrep", True, False),
        ("ffmpeg", True, False),
    ]
    assert "Post-install complete" in capsys.readouterr().out
