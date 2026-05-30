from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from setuptools import setup


REPO_ROOT = Path(__file__).resolve().parents[2]


def _data_file_tree(root_name: str) -> list[tuple[str, list[str]]]:
    root = REPO_ROOT / root_name
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(REPO_ROOT)
        grouped[str(rel_path.parent)].append(str(rel_path))
    return sorted(grouped.items())


setup(
    data_files=[
        ("config", ["config/cli-config.yaml.example", "config/env.example"]),
        ("constraints", ["constraints/termux.txt"]),
        *_data_file_tree("resources/skills"),
        *_data_file_tree("resources/locales"),
        # Optional skill packs are installed through NanoHermes packages instead
        # of being copied into every base environment.
    ]
)
