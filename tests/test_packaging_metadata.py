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
