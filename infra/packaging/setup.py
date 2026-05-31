from __future__ import annotations

import shutil
from collections import defaultdict
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


REPO_ROOT = Path(__file__).resolve().parents[2]

# Large/niche first-party skill packs are installed through Hermes Packages
# instead of being copied into every base wheel environment. Keep source
# checkout paths intact; this filter only affects wheel/sdist payloads.
OPTIONAL_SKILL_PACKAGE_CATEGORIES = frozenset({
    "creative",
    "mlops",
    "productivity",
    "research",
})

# Optional first-party tool modules are distributed through Hermes Packages, not
# copied into every NanoHermes base wheel. Keep load-bearing runtime helpers and
# the bundled-core toolsets in the base package; filter niche/network/provider
# tool implementations out of wheel installs.
OPTIONAL_TOOL_MODULES = frozenset({
    "browser_camofox",
    "browser_camofox_state",
    "browser_cdp_tool",
    "browser_dialog_tool",
    "browser_supervisor",
    "browser_tool",
    "computer_use_tool",
    "debug_helpers",
    "discord_tool",
    "fal_common",
    "feishu_doc_tool",
    "feishu_drive_tool",
    "homeassistant_tool",
    "image_generation_tool",
    "kanban_tools",
    "mcp_oauth",
    "mcp_oauth_manager",
    "mcp_tool",
    "microsoft_graph_auth",
    "microsoft_graph_client",
    "mixture_of_agents_tool",
    "neutts_synth",
    "openrouter_client",
    "osv_check",
    "send_message_tool",
    "transcription_tools",
    "tts_tool",
    "video_generation_tool",
    "vision_tools",
    "voice_mode",
    "web_tools",
    "x_search_tool",
    "xai_http",
    "yuanbao_tools",
})

OPTIONAL_TOOL_PACKAGES = frozenset({
    "tools.computer_use",
})

# Dashboard/Kanban is distributed as one package-managed slice for now.  The
# command registry and lightweight dispatch stubs remain in the base CLI, but
# the actual dashboard server/auth bundle and Kanban implementation are omitted
# from base wheels and restored by the dashboard package asset.
OPTIONAL_HERMES_CLI_MODULES = frozenset({
    "kanban",
    "kanban_db",
    "kanban_decompose",
    "kanban_diagnostics",
    "kanban_specify",
    "kanban_swarm",
    "web_server",
})

OPTIONAL_HERMES_CLI_PACKAGES = frozenset({
    "hermes_cli.dashboard_auth",
})

OPTIONAL_HERMES_CLI_DATA_DIRS = frozenset({
    "web_dist",
})

OPTIONAL_PLUGIN_PACKAGES = frozenset({
    "plugins.kanban",
})

# Regional/high-touch gateway platform adapters are package-managed. The base
# wheel keeps generic gateway helpers and common low-friction platforms, but
# trims provider-specific China platform code until a package installs it.
OPTIONAL_GATEWAY_PLATFORM_MODULES = frozenset({
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
})

OPTIONAL_GATEWAY_PLATFORM_PACKAGES = frozenset({
    "gateway.platforms.qqbot",
})

# Runtime plugin directories use file-system plugin names, including hyphenated
# directories that are not normal import package identifiers. Match by build/lib
# path so stale output cannot leak optional providers back into the base wheel.
OPTIONAL_RUNTIME_PLUGIN_PATHS = frozenset({
    "plugins/model-providers/alibaba",
    "plugins/model-providers/alibaba-coding-plan",
    "plugins/model-providers/deepseek",
    "plugins/model-providers/kimi-coding",
    "plugins/model-providers/minimax",
    "plugins/model-providers/qwen-oauth",
    "plugins/model-providers/stepfun",
    "plugins/model-providers/xiaomi",
    "plugins/model-providers/zai",
    "plugins/platforms/discord",
    "plugins/platforms/google_chat",
    "plugins/platforms/irc",
    "plugins/platforms/line",
    "plugins/platforms/mattermost",
    "plugins/platforms/ntfy",
    "plugins/platforms/simplex",
    "plugins/platforms/teams",
    "plugins/memory/byterover",
    "plugins/memory/hindsight",
    "plugins/memory/holographic",
    "plugins/memory/honcho",
    "plugins/memory/mem0",
    "plugins/memory/openviking",
    "plugins/memory/retaindb",
    "plugins/memory/supermemory",
})


class NanoHermesBuildPy(_build_py):
    """Build a lean base wheel by omitting package-managed tool modules."""

    def run(self):
        super().run()
        self._remove_excluded_tool_outputs()
        self._remove_excluded_hermes_cli_outputs()
        self._remove_excluded_plugin_outputs()
        self._remove_excluded_gateway_platform_outputs()

    def _remove_excluded_tool_outputs(self) -> None:
        # bdist_wheel can reuse an existing build/lib tree. Delete filtered
        # outputs explicitly so a previous unfiltered build cannot leak
        # optional tool code back into the base wheel.
        build_lib = Path(self.build_lib)
        tools_build_dir = build_lib / "tools"
        for module in OPTIONAL_TOOL_MODULES:
            (tools_build_dir / f"{module}.py").unlink(missing_ok=True)
        for package in OPTIONAL_TOOL_PACKAGES:
            shutil.rmtree(build_lib.joinpath(*package.split(".")), ignore_errors=True)

    def _remove_excluded_hermes_cli_outputs(self) -> None:
        build_lib = Path(self.build_lib)
        hermes_cli_build_dir = build_lib / "hermes_cli"
        for module in OPTIONAL_HERMES_CLI_MODULES:
            (hermes_cli_build_dir / f"{module}.py").unlink(missing_ok=True)
        for package in OPTIONAL_HERMES_CLI_PACKAGES:
            shutil.rmtree(build_lib.joinpath(*package.split(".")), ignore_errors=True)
        for data_dir in OPTIONAL_HERMES_CLI_DATA_DIRS:
            shutil.rmtree(hermes_cli_build_dir / data_dir, ignore_errors=True)

    def _remove_excluded_plugin_outputs(self) -> None:
        build_lib = Path(self.build_lib)
        for package in OPTIONAL_PLUGIN_PACKAGES:
            shutil.rmtree(build_lib.joinpath(*package.split(".")), ignore_errors=True)
        for rel_path in OPTIONAL_RUNTIME_PLUGIN_PATHS:
            shutil.rmtree(build_lib / rel_path, ignore_errors=True)

    def _remove_excluded_gateway_platform_outputs(self) -> None:
        build_lib = Path(self.build_lib)
        gateway_platforms_build_dir = build_lib / "gateway" / "platforms"
        for module in OPTIONAL_GATEWAY_PLATFORM_MODULES:
            (gateway_platforms_build_dir / f"{module}.py").unlink(missing_ok=True)
        for package in OPTIONAL_GATEWAY_PLATFORM_PACKAGES:
            shutil.rmtree(build_lib.joinpath(*package.split(".")), ignore_errors=True)

    def find_package_modules(self, package, package_dir):
        package_path = package.replace(".", "/")
        if package in OPTIONAL_TOOL_PACKAGES or any(
            package.startswith(f"{optional_package}.")
            for optional_package in OPTIONAL_TOOL_PACKAGES
        ):
            return []
        if package in OPTIONAL_HERMES_CLI_PACKAGES or any(
            package.startswith(f"{optional_package}.")
            for optional_package in OPTIONAL_HERMES_CLI_PACKAGES
        ):
            return []
        if package in OPTIONAL_PLUGIN_PACKAGES or any(
            package.startswith(f"{optional_package}.")
            for optional_package in OPTIONAL_PLUGIN_PACKAGES
        ):
            return []
        if package in OPTIONAL_GATEWAY_PLATFORM_PACKAGES or any(
            package.startswith(f"{optional_package}.")
            for optional_package in OPTIONAL_GATEWAY_PLATFORM_PACKAGES
        ):
            return []
        if package_path in OPTIONAL_RUNTIME_PLUGIN_PATHS or any(
            package_path.startswith(f"{optional_path}/")
            for optional_path in OPTIONAL_RUNTIME_PLUGIN_PATHS
        ):
            return []

        modules = super().find_package_modules(package, package_dir)
        if package == "tools":
            return [
                module_entry
                for module_entry in modules
                if module_entry[1] not in OPTIONAL_TOOL_MODULES
            ]
        if package == "hermes_cli":
            return [
                module_entry
                for module_entry in modules
                if module_entry[1] not in OPTIONAL_HERMES_CLI_MODULES
            ]
        if package == "gateway.platforms":
            return [
                module_entry
                for module_entry in modules
                if module_entry[1] not in OPTIONAL_GATEWAY_PLATFORM_MODULES
            ]
        return modules


def _data_file_tree(root_name: str, *, exclude_top_level: frozenset[str] = frozenset()) -> list[tuple[str, list[str]]]:
    root = REPO_ROOT / root_name
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if exclude_top_level:
            try:
                rel_under_root = path.relative_to(root)
            except ValueError:
                rel_under_root = path
            if rel_under_root.parts and rel_under_root.parts[0] in exclude_top_level:
                continue
        rel_path = path.relative_to(REPO_ROOT)
        grouped[str(rel_path.parent)].append(str(rel_path))
    return sorted(grouped.items())


setup(
    cmdclass={"build_py": NanoHermesBuildPy},
    data_files=[
        ("config", ["config/cli-config.yaml.example", "config/env.example"]),
        ("constraints", ["constraints/termux.txt"]),
        *_data_file_tree("resources/skills", exclude_top_level=OPTIONAL_SKILL_PACKAGE_CATEGORIES),
        *_data_file_tree("resources/locales"),
        # Optional skill packs are installed through NanoHermes packages instead
        # of being copied into every base environment.
    ]
)
