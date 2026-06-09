"""Regression tests for runtime-vs-source install behavior in install.sh.

The default installer should be an end-user runtime install, not a developer
source checkout. Source/editable installs remain available explicitly for
contributors and branch testing.
"""

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"


def _script() -> str:
    return INSTALL_SH.read_text(encoding="utf-8")


def test_install_script_has_valid_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(INSTALL_SH)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def _function_body(text: str, name: str) -> str:
    marker = f"{name}() {{\n"
    assert marker in text, f"{name}() not found"
    body = text.split(marker, 1)[1]
    body, _, _ = body.partition("\n}\n")
    assert body, f"{name}() body not found"
    return body


def test_default_install_mode_uses_nanohermes_runtime_archive_with_source_escape_hatch() -> None:
    text = _script()

    assert 'INSTALL_MODE="${HERMES_INSTALL_MODE:-runtime}"' in text
    assert 'REPO_URL_SSH="git@github.com:quarker1337/nanoHermes.git"' in text
    assert 'REPO_URL_HTTPS="https://github.com/quarker1337/nanoHermes.git"' in text
    assert (
        'RUNTIME_PACKAGE_SPEC="${HERMES_PACKAGE_SPEC:-https://github.com/quarker1337/nanoHermes/archive/refs/heads/main.tar.gz}"'
        in text
    )
    assert 'RUNTIME_PACKAGE_SPEC="${HERMES_PACKAGE_SPEC:-hermes-agent}"' not in text
    assert 'hermes-agent[all]' not in text.split('RUNTIME_PACKAGE_SPEC=', 1)[1].split('\n', 1)[0]
    assert "--source|--dev|--editable)" in text
    assert "--runtime|--wheel)" in text
    assert "Runtime package spec (default: NanoHermes main archive)" in text
    assert "Default: lean NanoHermes runtime wheel install" in text
    assert "Source/dev mode: clones the NanoHermes repo" in text


def test_branch_install_implies_source_mode_instead_of_silently_ignoring_branch() -> None:
    text = _script()
    branch_case = text.split("--branch|-Branch)", 1)[1].split(";;", 1)[0]

    assert 'BRANCH="$2"' in branch_case
    assert 'INSTALL_MODE="source"' in branch_case
    assert '"$INSTALL_MODE_EXPLICIT" = false' in branch_case


def test_default_main_path_does_not_require_git_or_clone_repo() -> None:
    text = _script()
    main_body = _function_body(text, "main")

    assert 'select_install_mode' in main_body
    assert 'if [ "$INSTALL_MODE" = "source" ]; then' in main_body
    assert 'check_git' in main_body
    assert 'clone_repo' in main_body
    assert 'else' in main_body
    assert 'prepare_runtime_install_dir' in main_body

    # The old bug: fresh end-user installs always cloned the full repo before
    # creating the venv, pulling docs/tests/.git into runtime installs.
    assert "\n    check_git\n" not in main_body
    assert "\n    clone_repo\n" not in main_body


def test_runtime_install_uses_package_spec_and_stamps_pip_install_method() -> None:
    text = _script()
    runtime_body = _function_body(text, "install_runtime_package")

    assert '$UV_CMD pip install "$RUNTIME_PACKAGE_SPEC"' in runtime_body
    assert '"$PYTHON_PATH" -m pip install "$RUNTIME_PACKAGE_SPEC"' in runtime_body
    assert 'log_success "Main package installed (runtime wheel: $RUNTIME_PACKAGE_SPEC)"' in runtime_body

    main_body = _function_body(text, "main")
    assert 'echo "pip" > "$HERMES_HOME/.install_method"' in main_body
    assert 'echo "git" > "$HERMES_HOME/.install_method"' in main_body


def test_wheel_config_and_skill_sync_use_installed_data_not_repo_paths() -> None:
    text = _script()
    config_body = _function_body(text, "copy_config_templates")
    data_body = _function_body(text, "get_packaged_data_dir")

    assert 'get_packaged_data_dir' in config_body
    assert 'template_base="$PACKAGED_DATA_DIR/config"' in config_body
    assert '"$INSTALL_DIR/venv/bin/python" -m tools.skills_sync' in config_body
    assert '"$PYTHON_PATH" -m tools.skills_sync' in config_body
    assert '"$INSTALL_DIR/tools/skills_sync.py"' in config_body
    assert 'python_for_data="$INSTALL_DIR/venv/bin/python"' in data_body
    assert 'python_for_data="$PYTHON_PATH"' in data_body


def test_existing_source_checkout_stays_source_unless_user_forces_runtime() -> None:
    text = _script()
    selector_body = _function_body(text, "select_install_mode")
    source_body = _function_body(text, "is_source_checkout")
    runtime_body = _function_body(text, "prepare_runtime_install_dir")

    assert '[ -e "$dir/.git" ]' in source_body
    assert 'is_source_checkout "$INSTALL_DIR"' in selector_body
    assert 'is_source_checkout "$INSTALL_DIR"' in runtime_body
    assert 'INSTALL_MODE="source"' in selector_body
    assert 'Existing source checkout detected' in selector_body
