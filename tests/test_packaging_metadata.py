from pathlib import Path
import tomllib


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_faster_whisper_is_not_a_base_dependency():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = data["project"]["dependencies"]

    assert not any(dep.startswith("faster-whisper") for dep in deps)

    voice_extra = data["project"]["optional-dependencies"]["voice"]
    assert any(dep.startswith("faster-whisper") for dep in voice_extra)


def test_manifest_includes_bundled_skills():
    manifest = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "graft resources/skills" in manifest
    assert "graft resources/locales" in manifest
    assert "graft resources/optional-skills" not in manifest


def test_dashboard_extra_is_public_alias_for_web_dashboard_dependencies():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    optional = data["project"]["optional-dependencies"]

    assert optional["dashboard"] == ["hermes-agent[web]"]
    assert "fastapi==0.136.3" in optional["web"]
    assert "uvicorn[standard]==0.41.0" in optional["web"]


def test_optional_tool_modules_are_filtered_from_base_wheel():
    """NanoHermes base wheels should not install optional tool code.

    Tool packages can still provide these modules later, but a plain base wheel
    should only ship the bundled core tool surface plus load-bearing helpers.
    """
    setup_py = (REPO_ROOT / "infra/packaging/setup.py").read_text(encoding="utf-8")

    assert "class NanoHermesBuildPy" in setup_py
    assert "cmdclass={\"build_py\": NanoHermesBuildPy}" in setup_py
    assert "OPTIONAL_TOOL_MODULES = frozenset({" in setup_py
    assert "OPTIONAL_TOOL_PACKAGES = frozenset({" in setup_py

    assert '"terminal_tool"' not in setup_py
    assert '"file_tools"' not in setup_py
    assert '"skills_tool"' not in setup_py
    for optional_module in [
        "web_tools",
        "browser_tool",
        "discord_tool",
        "image_generation_tool",
        "tts_tool",
        "vision_tools",
    ]:
        assert f'"{optional_module}"' in setup_py
    assert '"tools.computer_use"' in setup_py


def test_dashboard_kanban_cli_modules_are_filtered_from_base_wheel():
    """Dashboard/Kanban Python code is package-managed, not base-wheel code."""
    setup_py = (REPO_ROOT / "infra/packaging/setup.py").read_text(encoding="utf-8")

    assert "OPTIONAL_HERMES_CLI_MODULES = frozenset({" in setup_py
    assert "OPTIONAL_HERMES_CLI_PACKAGES = frozenset({" in setup_py
    assert "OPTIONAL_HERMES_CLI_DATA_DIRS = frozenset({" in setup_py
    assert "OPTIONAL_PLUGIN_PACKAGES = frozenset({" in setup_py

    optional_modules_block = setup_py.split("OPTIONAL_HERMES_CLI_MODULES = frozenset({", 1)[1].split("})", 1)[0]

    for core_module in ["main", "config", "package_manager"]:
        assert f'"{core_module}"' not in optional_modules_block

    for optional_module in [
        "kanban",
        "kanban_db",
        "kanban_decompose",
        "kanban_diagnostics",
        "kanban_specify",
        "kanban_swarm",
        "web_server",
    ]:
        assert f'"{optional_module}"' in setup_py

    assert '"hermes_cli.dashboard_auth"' in setup_py
    assert '"plugins.kanban"' in setup_py
    assert '"web_dist"' in setup_py

def test_provider_and_regional_platform_plugins_are_filtered_from_base_wheel():
    """Provider-specific and regional gateway plugins are package-managed.

    The NanoHermes base wheel should not ship niche model-provider plugins or
    China-specific gateway platform implementations. Dedicated packages can
    restore those files later via python_module_pack assets.
    """
    setup_py = (REPO_ROOT / "infra/packaging/setup.py").read_text(encoding="utf-8")

    assert "OPTIONAL_GATEWAY_PLATFORM_MODULES = frozenset({" in setup_py
    assert "OPTIONAL_GATEWAY_PLATFORM_PACKAGES = frozenset({" in setup_py
    assert "OPTIONAL_RUNTIME_PLUGIN_PATHS = frozenset({" in setup_py

    gateway_block = setup_py.split("OPTIONAL_GATEWAY_PLATFORM_MODULES = frozenset({", 1)[1].split("})", 1)[0]
    plugin_path_block = setup_py.split("OPTIONAL_RUNTIME_PLUGIN_PATHS = frozenset({", 1)[1].split("})", 1)[0]

    for core_gateway_module in ["base", "helpers", "webhook", "api_server"]:
        assert f'"{core_gateway_module}"' not in gateway_block

    for regional_module in [
        "dingtalk",
        "feishu",
        "feishu_comment",
        "feishu_comment_rules",
        "wecom",
        "wecom_callback",
        "wecom_crypto",
        "weixin",
        "yuanbao",
        "yuanbao_media",
        "yuanbao_proto",
        "yuanbao_sticker",
    ]:
        assert f'"{regional_module}"' in gateway_block

    assert '"gateway.platforms.qqbot"' in setup_py

    for provider_path in [
        "plugins/model-providers/alibaba",
        "plugins/model-providers/alibaba-coding-plan",
        "plugins/model-providers/deepseek",
        "plugins/model-providers/kimi-coding",
        "plugins/model-providers/minimax",
        "plugins/model-providers/qwen-oauth",
        "plugins/model-providers/stepfun",
        "plugins/model-providers/xiaomi",
        "plugins/model-providers/zai",
    ]:
        assert f'"{provider_path}"' in plugin_path_block
