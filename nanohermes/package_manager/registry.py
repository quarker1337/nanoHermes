from __future__ import annotations

import json
import shutil
import urllib.request
from pathlib import Path
from typing import Iterable

from hermes_constants import get_hermes_home

DEFAULT_REGISTRY_URL = (
    "https://raw.githubusercontent.com/quarker1337/Hermes-Packages/main/registry/index.json"
)


class PackageRegistry:
    """Cached Hermes package registry index."""

    def __init__(self, home: str | Path | None = None) -> None:
        self.home = Path(home) if home is not None else Path(get_hermes_home())
        self.cache_dir = self.home / "packages" / "cache"
        self.index_path = self.cache_dir / "registry-index.json"

    def update(self, source: str | Path = DEFAULT_REGISTRY_URL) -> dict:
        """Fetch/copy a registry index into the local cache and return it."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        source_str = str(source)
        if source_str.startswith(("http://", "https://")):
            with urllib.request.urlopen(source_str, timeout=30) as response:  # noqa: S310 - user-configured source
                payload = response.read()
            self.index_path.write_bytes(payload)
        else:
            shutil.copyfile(Path(source_str).expanduser(), self.index_path)
        return self.load()

    def load(self) -> dict:
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"No package registry cache at {self.index_path}. Run `hermes pkg update` first."
            )
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    @property
    def packages(self) -> dict[str, dict]:
        return self.load().get("packages", {})

    def get(self, name: str) -> dict:
        packages = self.packages
        if name not in packages:
            raise KeyError(f"Package not found: {name}")
        return packages[name]

    def search(self, query: str) -> list[dict]:
        q = query.lower()
        matches: list[dict] = []
        for package in self.packages.values():
            haystack = " ".join(
                str(package.get(key, ""))
                for key in ("name", "display_name", "description", "channel", "type")
            ).lower()
            if q in haystack:
                matches.append(package)
        return sorted(matches, key=lambda p: p.get("name", ""))

    def resolve_with_dependencies(self, names: Iterable[str]) -> list[dict]:
        resolved: list[dict] = []
        seen: set[str] = set()

        def visit(name: str) -> None:
            if name in seen:
                return
            package = self.get(name)
            for dep in package.get("dependencies", []):
                visit(dep)
            seen.add(name)
            resolved.append(package)

        for name in names:
            visit(name)
        return resolved
