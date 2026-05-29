from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from hermes_constants import get_hermes_home


class PackageState:
    """Local installed-package state under $HERMES_HOME/packages."""

    def __init__(self, home: str | Path | None = None) -> None:
        self.home = Path(home) if home is not None else Path(get_hermes_home())
        self.state_dir = self.home / "packages"
        self.installed_path = self.state_dir / "installed.json"

    def load(self) -> dict:
        if not self.installed_path.exists():
            return {"installed": {}}
        return json.loads(self.installed_path.read_text(encoding="utf-8"))

    def save(self, state: dict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.installed_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @property
    def installed(self) -> dict[str, dict]:
        return self.load().get("installed", {})

    def mark_installed(self, package: dict, *, source: str = "registry") -> None:
        state = self.load()
        installed = state.setdefault("installed", {})
        tools = package.get("tools", {})
        install = package.get("install", {})
        installed[package["name"]] = {
            "version": package.get("version"),
            "source": source,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "toolsets": tools.get("toolsets", []),
            "tools": tools.get("tools", []),
            "python_extras": install.get("python_extras", []),
        }
        self.save(state)

    def remove(self, name: str) -> bool:
        state = self.load()
        installed = state.setdefault("installed", {})
        existed = name in installed
        installed.pop(name, None)
        self.save(state)
        return existed
