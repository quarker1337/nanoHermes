from types import SimpleNamespace


def test_postinstall_ignores_remembered_install_declines(monkeypatch, capsys):
    """`hermes postinstall` is explicit, so prior startup declines must not suppress it."""
    from hermes_cli import main as cli_main

    calls = []

    def fake_ensure(dep, interactive=True, respect_decline=True):
        calls.append((dep, interactive, respect_decline))
        return True

    monkeypatch.setattr("hermes_cli.config.stamp_install_method", lambda method: None)
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
