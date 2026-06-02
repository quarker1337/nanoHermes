from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_runtime.hermes_constants import get_hermes_home


PACKAGE_DB_SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PackageState:
    """Apt-style local package database under $HERMES_HOME/packages.

    The registry cache answers "what could be installed?"; this database
    answers "what did `hermes pkg` install here?".  Keep this small, stable,
    and queryable so other runtime surfaces can reason about installed package
    ownership without scraping CLI output.
    """

    def __init__(self, home: str | Path | None = None) -> None:
        self.home = Path(home) if home is not None else Path(get_hermes_home())
        self.state_dir = self.home / "packages"
        self.installed_path = self.state_dir / "installed.json"

    def _empty_state(self) -> dict[str, Any]:
        return {
            "schema_version": PACKAGE_DB_SCHEMA_VERSION,
            "installed": {},
        }

    def _coerce_state(self, state: Any) -> dict[str, Any]:
        if not isinstance(state, dict):
            return self._empty_state()
        installed = state.get("installed")
        if not isinstance(installed, dict):
            installed = {}
        coerced = dict(state)
        coerced["schema_version"] = int(coerced.get("schema_version") or PACKAGE_DB_SCHEMA_VERSION)
        coerced["installed"] = installed
        return coerced

    def load(self) -> dict[str, Any]:
        if not self.installed_path.exists():
            return self._empty_state()
        return self._coerce_state(json.loads(self.installed_path.read_text(encoding="utf-8")))

    def save(self, state: dict[str, Any]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.installed_path.write_text(
            json.dumps(self._coerce_state(state), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @property
    def installed(self) -> dict[str, dict[str, Any]]:
        return self.load().get("installed", {})

    def mark_installed(
        self,
        package: dict[str, Any],
        *,
        source: str = "registry",
        requested: bool = True,
    ) -> None:
        state = self.load()
        installed = state.setdefault("installed", {})
        tools = package.get("tools", {}) if isinstance(package.get("tools", {}), dict) else {}
        install = package.get("install", {}) if isinstance(package.get("install", {}), dict) else {}
        name = package["name"]
        previous = installed.get(name, {}) if isinstance(installed.get(name), dict) else {}
        now = _utc_now()
        installed[name] = {
            "name": name,
            "display_name": package.get("display_name"),
            "version": package.get("version"),
            "description": package.get("description"),
            "type": package.get("type"),
            "channel": package.get("channel"),
            "status": "installed",
            "install_reason": "manual" if requested else "dependency",
            "requested": bool(requested),
            "source": source,
            "installed_at": previous.get("installed_at") or now,
            "updated_at": now,
            "dependencies": list(package.get("dependencies", [])),
            "toolsets": list(tools.get("toolsets", [])),
            "tools": list(tools.get("tools", [])),
            "python_extras": list(install.get("python_extras", [])),
            "python_packages": list(install.get("python_packages", [])),
            "system_packages": list(install.get("system_packages", [])),
            "npm_packages": list(install.get("npm_packages", [])),
            "runtime_dependencies": list(install.get("runtime_dependencies", [])),
            "optional_assets": list(install.get("optional_assets", [])),
            "permissions": package.get("permissions", {}),
            "env": package.get("env", {}),
            "manifest_path": package.get("manifest_path"),
            "manifest_sha256": package.get("manifest_sha256"),
        }
        self.save(state)

    def remove(self, name: str) -> bool:
        state = self.load()
        installed = state.setdefault("installed", {})
        existed = name in installed
        installed.pop(name, None)
        self.save(state)
        return existed

    def is_installed(self, name: str) -> bool:
        package = self.installed.get(name)
        return isinstance(package, dict) and package.get("status", "installed") == "installed"

    def installed_toolsets(self) -> list[str]:
        toolsets: set[str] = set()
        for package in self.installed.values():
            if not isinstance(package, dict) or package.get("status", "installed") != "installed":
                continue
            toolsets.update(str(toolset) for toolset in package.get("toolsets", []) if toolset)
        return sorted(toolsets)

    def installed_tools(self) -> list[str]:
        tools: set[str] = set()
        for package in self.installed.values():
            if not isinstance(package, dict) or package.get("status", "installed") != "installed":
                continue
            tools.update(str(tool) for tool in package.get("tools", []) if tool)
        return sorted(tools)

    def package_for_toolset(self, toolset: str) -> str | None:
        for name, package in sorted(self.installed.items()):
            if not isinstance(package, dict) or package.get("status", "installed") != "installed":
                continue
            if toolset in package.get("toolsets", []):
                return name
        return None
