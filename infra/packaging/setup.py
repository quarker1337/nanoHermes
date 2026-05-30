from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from setuptools import setup


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
    data_files=[
        ("config", ["config/cli-config.yaml.example", "config/env.example"]),
        ("constraints", ["constraints/termux.txt"]),
        *_data_file_tree("resources/skills", exclude_top_level=OPTIONAL_SKILL_PACKAGE_CATEGORIES),
        *_data_file_tree("resources/locales"),
        # Optional skill packs are installed through NanoHermes packages instead
        # of being copied into every base environment.
    ]
)
