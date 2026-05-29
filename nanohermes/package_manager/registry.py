from __future__ import annotations

import base64
import binascii
import json
import queue
import shutil
import socket
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

from hermes_constants import get_hermes_home

DEFAULT_REGISTRY_URL = (
    "https://api.github.com/repos/quarker1337/Hermes-Packages/contents/registry/index.json?ref=main"
)
DEFAULT_REGISTRY_RAW_URL = (
    "https://raw.githubusercontent.com/quarker1337/Hermes-Packages/main/registry/index.json"
)
DEFAULT_REGISTRY_TIMEOUT_SECONDS = 15.0


class PackageRegistryError(RuntimeError):
    """User-facing package registry failure."""


def is_http_source(source: str | Path) -> bool:
    return str(source).startswith(("http://", "https://"))


def _fetch_url_with_deadline(url: str, timeout: float) -> bytes:
    """Fetch a URL while enforcing a wall-clock deadline.

    ``urllib.request.urlopen(..., timeout=N)`` covers socket connect/read
    operations, but some platform DNS/proxy failures can still look like a
    hang. Running the blocking fetch in a daemon thread gives the CLI a hard
    wall-clock deadline and lets the process exit cleanly after reporting a
    useful error.
    """
    result_queue: queue.Queue[tuple[bool, bytes | BaseException]] = queue.Queue(maxsize=1)

    def worker() -> None:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "NanoHermes-package-manager/0.1"})
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-configured source
                payload = response.read()
            result_queue.put_nowait((True, payload))
        except BaseException as exc:  # noqa: BLE001 - relayed to caller below
            try:
                result_queue.put_nowait((False, exc))
            except queue.Full:
                pass

    threading.Thread(target=worker, daemon=True).start()
    try:
        ok, result = result_queue.get(timeout=timeout)
    except queue.Empty as exc:
        raise PackageRegistryError(f"Timed out fetching package registry after {timeout:g}s: {url}") from exc

    if ok:
        return result  # type: ignore[return-value]

    if isinstance(result, urllib.error.URLError):
        reason = result.reason
        if isinstance(reason, socket.timeout) or "timed out" in str(reason).lower():
            raise PackageRegistryError(f"Timed out fetching package registry after {timeout:g}s: {url}") from result
        raise PackageRegistryError(f"Failed to fetch package registry from {url}: {reason}") from result
    if isinstance(result, TimeoutError | socket.timeout):
        raise PackageRegistryError(f"Timed out fetching package registry after {timeout:g}s: {url}") from result
    if isinstance(result, BaseException):
        raise PackageRegistryError(f"Failed to fetch package registry from {url}: {result}") from result
    raise PackageRegistryError(f"Failed to fetch package registry from {url}")


def _decode_registry_payload(payload: bytes) -> bytes:
    """Return registry JSON bytes from either raw JSON or GitHub Contents API JSON."""
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return payload

    if not isinstance(data, dict) or data.get("encoding") != "base64" or "content" not in data:
        return payload

    content = str(data["content"]).replace("\n", "")
    try:
        return base64.b64decode(content, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise PackageRegistryError("GitHub registry API response contained invalid base64 content") from exc


class PackageRegistry:
    """Cached Hermes package registry index."""

    def __init__(self, home: str | Path | None = None) -> None:
        self.home = Path(home) if home is not None else Path(get_hermes_home())
        self.cache_dir = self.home / "packages" / "cache"
        self.index_path = self.cache_dir / "registry-index.json"

    def update(self, source: str | Path = DEFAULT_REGISTRY_URL, *, timeout: float = DEFAULT_REGISTRY_TIMEOUT_SECONDS) -> dict:
        """Fetch/copy a registry index into the local cache and return it."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        source_str = str(source)
        if is_http_source(source_str):
            payload = _fetch_url_with_deadline(source_str, timeout=max(float(timeout), 0.1))
            payload = _decode_registry_payload(payload)
            self.index_path.write_bytes(payload)
        else:
            try:
                shutil.copyfile(Path(source_str).expanduser(), self.index_path)
            except OSError as exc:
                raise PackageRegistryError(f"Failed to copy package registry from {source_str}: {exc}") from exc
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
