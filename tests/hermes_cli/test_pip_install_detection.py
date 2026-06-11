import json
from unittest.mock import patch


def test_pip_install_detected_when_no_git_dir(tmp_path):
    """When PROJECT_ROOT has no .git, detect as pip install."""
    with patch("hermes_cli.config.get_managed_system", return_value=None), \
         patch("hermes_cli.config.get_hermes_home", return_value=tmp_path):
        from hermes_cli.config import detect_install_method
        method = detect_install_method(project_root=tmp_path)
        assert method == "pip"


def test_git_install_detected_when_git_dir_exists(tmp_path):
    """When PROJECT_ROOT has .git, detect as git install."""
    (tmp_path / ".git").mkdir()
    with patch("hermes_cli.config.get_managed_system", return_value=None), \
         patch("hermes_cli.config.get_hermes_home", return_value=tmp_path):
        from hermes_cli.config import detect_install_method
        method = detect_install_method(project_root=tmp_path)
        assert method == "git"


def test_managed_install_takes_precedence(tmp_path):
    """When HERMES_MANAGED is set, that takes precedence over git detection."""
    (tmp_path / ".git").mkdir()
    with patch("hermes_cli.config.get_managed_system", return_value="NixOS"), \
         patch("hermes_cli.config.get_hermes_home", return_value=tmp_path):
        from hermes_cli.config import detect_install_method
        method = detect_install_method(project_root=tmp_path)
        assert method == "nixos"


def test_recommended_update_command_pip():
    """Pip installs recommend pip install --upgrade."""
    from hermes_cli.config import recommended_update_command_for_method
    cmd = recommended_update_command_for_method("pip")
    assert "pip install" in cmd or "uv pip install" in cmd
    assert "--upgrade" in cmd
    assert "hermes-agent" in cmd


def test_recommended_update_command_preserves_direct_url_source():
    """Direct-url pip installs should not recommend replacing forks with PyPI."""
    from hermes_cli import config

    class FakeDistribution:
        def read_text(self, name):
            assert name == "direct_url.json"
            return json.dumps({
                "url": "https://github.com/quarker1337/nanoHermes.git",
                "vcs_info": {"vcs": "git", "requested_revision": "main"},
            })

    with patch("hermes_cli.config.get_managed_update_command", return_value=None), \
         patch("hermes_cli.config.detect_install_method", return_value="pip"), \
         patch("hermes_cli.config.importlib_metadata.distribution", return_value=FakeDistribution()), \
         patch("hermes_cli.config.shutil.which", return_value="/usr/bin/uv"):
        cmd = config.recommended_update_command()

    assert cmd.startswith("uv pip install --upgrade ")
    assert "hermes-agent @ git+https://github.com/quarker1337/nanoHermes.git@main" in cmd


def test_stamp_file_takes_precedence(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".install_method").write_text("docker\n")
    with patch("hermes_cli.config.get_managed_system", return_value=None), \
         patch("hermes_cli.config.get_hermes_home", return_value=tmp_path):
        from hermes_cli.config import detect_install_method
        assert detect_install_method(project_root=tmp_path) == "docker"


def test_docker_detected_via_dockerenv(tmp_path):
    with patch("hermes_cli.config.get_managed_system", return_value=None), \
         patch("hermes_cli.config.get_hermes_home", return_value=tmp_path), \
         patch("hermes_runtime.hermes_constants.is_container", return_value=True):
        from hermes_cli.config import detect_install_method
        assert detect_install_method(project_root=tmp_path) == "docker"


def test_recommended_update_command_docker():
    from hermes_cli.config import recommended_update_command_for_method
    assert "docker pull" in recommended_update_command_for_method("docker")
