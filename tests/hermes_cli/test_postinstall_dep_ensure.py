from types import SimpleNamespace


def test_base_postinstall_does_not_ensure_runtime_dependencies(monkeypatch, capsys):
    """NanoHermes base postinstall must leave runtime deps to package installs."""
    from hermes_cli import main as cli_main

    calls = []

    class RuntimePackagesInstalled:
        def package_for_toolset(self, toolset):
            return {"browser": "browser"}.get(toolset)

        def is_installed(self, package):
            return package in {"browser", "dashboard", "web-search"}

    def fake_ensure(dep, interactive=True, respect_decline=True):
        calls.append((dep, interactive, respect_decline))
        return True

    monkeypatch.setattr("hermes_cli.config.stamp_install_method", lambda method: None)
    monkeypatch.setattr("hermes_cli.package_manager.state.PackageState", RuntimePackagesInstalled)
    monkeypatch.setattr("hermes_cli.dep_ensure.ensure_dependency", fake_ensure)
    monkeypatch.setattr(cli_main, "_has_any_provider_configured", lambda: True)

    cli_main.cmd_postinstall(SimpleNamespace())

    assert calls == []
    assert "Post-install complete" in capsys.readouterr().out
