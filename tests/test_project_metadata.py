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


def test_optional_skills_not_grafted_into_base_sdist():
    """NanoHermes installs optional skill packs through packages, not the
    base wheel/sdist payload.
    """
    manifest_lines = _load_manifest_lines()
    setup_py = _load_packaging_setup_text()

    assert "include infra/packaging/build_backend.py" in manifest_lines
    assert "include infra/packaging/setup.py" in manifest_lines
    assert "graft resources/skills" in manifest_lines
    assert "graft resources/locales" in manifest_lines
    assert "graft resources/optional-skills" not in manifest_lines
    assert '("config", ["config/cli-config.yaml.example", "config/env.example"])' in setup_py
    assert '("constraints", ["constraints/termux.txt"])' in setup_py
    assert '*_data_file_tree("resources/skills")' in setup_py
    assert '*_data_file_tree("resources/locales")' in setup_py
    assert '*_data_file_tree("resources/optional-skills")' not in setup_py


def test_dashboard_plugin_manifests_and_assets_are_packaged():
    """Bundled dashboard plugins need their manifests and built assets in
    wheel installs so /api/dashboard/plugins can discover them outside a
    source checkout."""
    package_data = _load_package_data()
    plugin_data = package_data["plugins"]

    assert "*/dashboard/manifest.json" in plugin_data
    assert "*/dashboard/dist/*" in plugin_data
    assert "*/dashboard/dist/**/*" in plugin_data
