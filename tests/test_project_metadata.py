"""Regression tests for packaging metadata in pyproject.toml."""

from pathlib import Path
import tomllib


def _load_pyproject():
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject_path.open("rb") as handle:
        return tomllib.load(handle)


def _load_project_metadata():
    return _load_pyproject()["project"]


def _load_dependencies():
    return _load_project_metadata()["dependencies"]


def _load_optional_dependencies():
    return _load_project_metadata()["optional-dependencies"]


def _load_manifest_lines():
    manifest_path = Path(__file__).resolve().parents[1] / "MANIFEST.in"
    return manifest_path.read_text(encoding="utf-8").splitlines()


def _load_packaging_setup_text():
    setup_path = Path(__file__).resolve().parents[1] / "infra" / "packaging" / "setup.py"
    return setup_path.read_text(encoding="utf-8")


def _load_package_data():
    return _load_pyproject()["tool"]["setuptools"]["package-data"]


def test_build_backend_lives_under_infra_packaging():
    pyproject = _load_pyproject()
    build_system = pyproject["build-system"]

    assert build_system["build-backend"] == "infra.packaging.build_backend"
    assert build_system["backend-path"] == ["."]
    assert not (Path(__file__).resolve().parents[1] / "setup.py").exists()


def test_matrix_extra_not_in_all():
    """The [matrix] extra pulls `mautrix[encryption]` -> `python-olm`,
    which has Linux-only wheels and no native build path on Windows or
    modern macOS (archived libolm, C++ errors with Clang 21+).

    With matrix in [all], `uv sync --locked` on Windows tried to build
    python-olm from sdist and failed on `make`. As of 2026-05-12 the
    [matrix] extra is excluded from [all] entirely and routed through
    `tools/lazy_deps.py` (LAZY_DEPS["platform.matrix"]) — installs at
    first use, where the user is expected to have a toolchain.
    """
    optional_dependencies = _load_optional_dependencies()

    assert "matrix" in optional_dependencies, "[matrix] extra must still exist for explicit `pip install hermes-agent[matrix]`"
    # Must NOT appear in [all] in any form — neither unconditional nor
    # platform-gated. Lazy-install handles it.
    matrix_in_all = [
        dep for dep in optional_dependencies["all"]
        if "matrix" in dep
    ]
    assert not matrix_in_all, (
        "matrix must not appear in [all] — it's lazy-installed via "
        "tools/lazy_deps.py LAZY_DEPS['platform.matrix']. Found: "
        f"{matrix_in_all}"
    )


def test_lazy_installable_extras_excluded_from_all():
    """Policy (2026-05-12): every extra that has a `LAZY_DEPS` entry
    in `tools/lazy_deps.py` must be excluded from [all].

    The lazy-install system exists so one quarantined PyPI release
    (e.g. mistralai 2.4.6) can't break every fresh install. Putting a
    backend in BOTH [all] and LAZY_DEPS defeats that — fresh installs
    eager-install it and inherit whatever's broken upstream.

    If you're tempted to add an opt-in backend to [all] for "convenience,"
    add it to `LAZY_DEPS` instead so it installs at first use.
    """
    optional_dependencies = _load_optional_dependencies()

    # Hard-coded mirror of the extras that are in LAZY_DEPS as of
    # 2026-05-12. This list intentionally duplicates rather than
    # imports tools/lazy_deps.py so the test stays a contract — if
    # someone adds a new lazy-install backend, they have to update
    # this list AND verify [all] doesn't contain it.
    lazy_covered_extras = {
        "anthropic", "bedrock",
        "exa", "firecrawl", "parallel-web",
        "fal",
        "edge-tts", "tts-premium",
        "voice",  # faster-whisper / sounddevice / numpy
        "modal", "daytona",
        "messaging", "slack", "matrix", "dingtalk", "feishu",
        "honcho", "hindsight",
    }
    all_extra_specs = optional_dependencies["all"]
    for extra in lazy_covered_extras:
        offending = [
            spec for spec in all_extra_specs
            if f"hermes-agent[{extra}]" in spec
        ]
        assert not offending, (
            f"[{extra}] is in [all] but also in LAZY_DEPS. "
            f"Remove it from [all] in pyproject.toml — it lazy-installs "
            f"at first use. Found in [all]: {offending}"
        )


def test_messaging_extra_includes_qrcode_for_weixin_setup():
    optional_dependencies = _load_optional_dependencies()

    messaging_extra = optional_dependencies["messaging"]
    assert any(dep.startswith("qrcode") for dep in messaging_extra)


def test_messaging_extra_does_not_install_discord_voice_crypto():
    """discord.py 2.7.1 caps voice crypto at vulnerable PyNaCl<1.6.

    Keep the default messaging extra on text/bot APIs only until upstream
    releases a voice extra compatible with the patched PyNaCl line.
    """
    optional_dependencies = _load_optional_dependencies()

    messaging_extra = optional_dependencies["messaging"]
    assert "discord.py==2.7.1" in messaging_extra
    assert not any("discord.py[voice]" in dep for dep in messaging_extra)
    assert not any(dep.lower().startswith("pynacl") for dep in messaging_extra)


def test_dingtalk_extra_includes_qrcode_for_qr_auth():
    """DingTalk's QR-code device-flow auth (hermes_cli/dingtalk_auth.py)
    needs the qrcode package."""
    optional_dependencies = _load_optional_dependencies()

    dingtalk_extra = optional_dependencies["dingtalk"]
    assert any(dep.startswith("qrcode") for dep in dingtalk_extra)


def test_feishu_extra_includes_qrcode_for_qr_login():
    """Feishu's QR login flow (gateway/platforms/feishu.py) needs the
    qrcode package."""
    optional_dependencies = _load_optional_dependencies()

    feishu_extra = optional_dependencies["feishu"]
    assert any(dep.startswith("qrcode") for dep in feishu_extra)


def test_github_app_jwt_crypto_is_optional():
    """GitHub App bot auth needs RSA signing, but PAT / gh CLI Skills Hub
    auth does not. Keep the cryptography wheel out of the base install.
    """
    dependencies = _load_dependencies()
    optional_dependencies = _load_optional_dependencies()

    assert "PyJWT==2.12.1" in dependencies
    assert not any("PyJWT[crypto]" in dep or "pyjwt[crypto]" in dep.lower() for dep in dependencies)
    assert "github-app" in optional_dependencies
    assert "PyJWT[crypto]==2.12.1" in optional_dependencies["github-app"]


def test_default_skills_not_grafted_into_base_sdist():
    """NanoHermes installs first-party skills through packages or the Skills Hub,
    not the base wheel/sdist payload.
    """
    manifest_lines = _load_manifest_lines()
    setup_py = _load_packaging_setup_text()
    repo_root = Path(__file__).resolve().parents[1]

    assert "include infra/packaging/build_backend.py" in manifest_lines
    assert "include infra/packaging/setup.py" in manifest_lines
    assert "graft resources/skills" not in manifest_lines
    assert not any(line.startswith("prune resources/skills/") for line in manifest_lines)
    assert "graft resources/locales" in manifest_lines
    assert "graft resources/optional-skills" not in manifest_lines
    assert (repo_root / "resources" / "skills" / ".no-bundled-sync").is_file()
    assert not (repo_root / "resources" / "skills" / "yuanbao").exists()
    assert (repo_root / "resources" / "optional-skills" / "yuanbao" / "SKILL.md").is_file()
    assert '("config", ["config/cli-config.yaml.example", "config/env.example"])' in setup_py
    assert '("constraints", ["constraints/termux.txt"])' in setup_py
    assert '*_data_file_tree("resources/skills"' not in setup_py
    assert '*_data_file_tree("resources/locales")' in setup_py
    assert '*_data_file_tree("resources/optional-skills")' not in setup_py


def test_non_wheel_install_paths_do_not_seed_default_skills():
    """Nix and installer fallbacks must follow the zero-default-skills base policy."""
    repo_root = Path(__file__).resolve().parents[1]
    nix_pkg = (repo_root / "infra" / "nix" / "hermes-agent.nix").read_text(encoding="utf-8")
    nix_checks = (repo_root / "infra" / "nix" / "checks.nix").read_text(encoding="utf-8")
    install_sh = (repo_root / "scripts" / "install.sh").read_text(encoding="utf-8")
    setup_sh = (repo_root / "scripts" / "setup-hermes.sh").read_text(encoding="utf-8")
    install_ps1 = (repo_root / "scripts" / "install.ps1").read_text(encoding="utf-8")

    assert "src = ../../resources/skills" not in nix_pkg
    assert "cp -r ${bundledSkills}" not in nix_pkg
    assert "$out/share/hermes-agent/skills/.no-bundled-sync" in nix_pkg
    assert 'test "$SKILL_COUNT" -eq 0' in nix_checks
    assert "no-bundled-sync marker present" in nix_checks

    for script_text in (install_sh, setup_sh):
        assert ".no-bundled-sync" in script_text
        assert "-name SKILL.md -print -quit" in script_text

    assert ".no-bundled-sync" in install_ps1
    assert 'Get-ChildItem $bundledSkills -Filter "SKILL.md" -Recurse -File' in install_ps1


def test_dashboard_plugin_manifests_and_assets_are_packaged():
    """Bundled dashboard plugins need their manifests and built assets in
    wheel installs so /api/dashboard/plugins can discover them outside a
    source checkout."""
    package_data = _load_package_data()
    plugin_data = package_data["plugins"]

    assert "*/dashboard/manifest.json" in plugin_data
    assert "*/dashboard/dist/*" in plugin_data
    assert "*/dashboard/dist/**/*" in plugin_data
