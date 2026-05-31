from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


PUBLIC_DOCS = [
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "packages.md",
    ROOT / "docs" / "site" / "docs" / "guides" / "work-with-skills.md",
    ROOT / "docs" / "site" / "docs" / "reference" / "skills-catalog.md",
    ROOT / "docs" / "site" / "docs" / "reference" / "profile-commands.md",
    ROOT / "docs" / "site" / "docs" / "reference" / "slash-commands.md",
    ROOT / "docs" / "site" / "docs" / "user-guide" / "profiles.md",
    ROOT / "docs" / "site" / "docs" / "user-guide" / "profile-distributions.md",
    ROOT / "docs" / "site" / "docs" / "user-guide" / "docker.md",
    ROOT / "docs" / "site" / "docs" / "user-guide" / "features" / "skills.md",
    ROOT / "docs" / "site" / "scripts" / "generate-llms-txt.py",
    ROOT / "docs" / "site" / "scripts" / "generate-skill-docs.py",
]


STALE_BUNDLED_SKILL_PHRASES = [
    "Bundled Skills Catalog",
    "bundled skills",
    "bundled set",
    "fresh profile with bundled",
    "ships with bundled skills",
]


def test_public_docs_present_nanohermes_as_zero_skill_package_managed_base():
    readme = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    assert "Tiny base, package-managed capabilities" in readme
    assert "zero installed skills" in readme
    assert "profile-developer" in readme
    assert "profile-maintainer" in readme
    assert "profile-research" in readme
    assert "profile-mlops" in readme


def test_public_docs_do_not_reintroduce_bundled_skill_positioning():
    offenders: list[str] = []
    for path in PUBLIC_DOCS:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in STALE_BUNDLED_SKILL_PHRASES:
            if phrase.lower() in lowered:
                offenders.append(f"{path.relative_to(ROOT)} contains {phrase!r}")

    assert not offenders, "\n".join(offenders)
