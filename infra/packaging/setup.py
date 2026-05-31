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
    "url_safety",
    "video_generation_tool",
    "vision_tools",
    "voice_mode",
    "web_tools",
    "website_policy",
    "x_search_tool",
    "xai_http",
    "yuanbao_tools",
})

OPTIONAL_TOOL_PACKAGES = frozenset({
    "tools.computer_use",
})


class NanoHermesBuildPy(_build_py):
    """Build a lean base wheel by omitting package-managed tool modules."""

    def run(self):
        super().run()
        self._remove_excluded_tool_outputs()

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

    def find_package_modules(self, package, package_dir):
        if package in OPTIONAL_TOOL_PACKAGES or any(
            package.startswith(f"{optional_package}.")
            for optional_package in OPTIONAL_TOOL_PACKAGES
        ):
            return []

        modules = super().find_package_modules(package, package_dir)
        if package != "tools":
            return modules

        return [
            module_entry
            for module_entry in modules
            if module_entry[1] not in OPTIONAL_TOOL_MODULES
        ]


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
