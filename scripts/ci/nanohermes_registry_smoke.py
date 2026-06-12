#!/usr/bin/env python3
"""NanoHermes installed-user package registry smoke.

The default mode is intentionally CI-friendly: install NanoHermes into a fresh
venv, fetch the default pushed package registry, install a representative set of
package-managed tool modules with ``--no-pip``, and verify restored imports.

Set ``--mode all-real`` only for manual/release verification. It installs every
package from the default registry without ``--no-pip`` and can download runtime
payloads such as the local browser engine.
"""

from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPRESENTATIVE_PACKAGES = [
    "web-search",
    "browser",
    "tts",
    "image-gen",
    "gateway",
    "homeassistant",
    "feishu",
    "yuanbao",
]

RESTORED_MODULES = [
    "tools.web_tools",
    "tools.browser_tool",
    "tools.tts_tool",
    "tools.image_generation_tool",
    "tools.send_message_tool",
    "tools.homeassistant_tool",
    "tools.feishu_doc_tool",
    "tools.feishu_drive_tool",
    "tools.yuanbao_tools",
]

INVALID_EXTRA_PATTERNS = [
    re.compile(r"does not have an extra", re.IGNORECASE),
    re.compile(r"invalid.*extra", re.IGNORECASE),
    re.compile(r"No such extra", re.IGNORECASE),
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    log_file: Path,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    rendered = " ".join(cmd)
    print(f"$ {rendered}", flush=True)
    with log_file.open("a", encoding="utf-8") as log:
        log.write(f"\n$ {rendered}\n")
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        log.write(proc.stdout)
    if proc.stdout:
        print(proc.stdout, end="", flush=True)
    if proc.returncode != 0:
        raise SystemExit(f"command failed with exit {proc.returncode}: {rendered}")
    return proc


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _venv_bin(venv: Path) -> Path:
    return venv / ("Scripts" if os.name == "nt" else "bin")


def _clean_env(root: Path, venv: Path, hermes_home: Path) -> dict[str, str]:
    keep = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "SystemRoot": os.environ.get("SystemRoot", ""),
        "TEMP": os.environ.get("TEMP", ""),
        "TMP": os.environ.get("TMP", ""),
    }
    env = {k: v for k, v in keep.items() if v}
    env.update(
        {
            "HOME": str(root / "home"),
            "HERMES_HOME": str(hermes_home),
            "NO_COLOR": "1",
            "PYTHONHASHSEED": "0",
            "TZ": "UTC",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": f"{_venv_bin(venv)}{os.pathsep}{os.environ.get('PATH', '')}",
        }
    )
    return env


def _load_package_names(registry_path: Path) -> list[str]:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    packages = sorted(registry.get("packages", {}))
    if not packages:
        raise SystemExit(f"no packages found in registry cache: {registry_path}")
    return packages


def _load_installed_names(state_path: Path) -> set[str]:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    return set(state.get("installed", {}))


def _check_invalid_extra_warnings(log_file: Path) -> None:
    text = log_file.read_text(encoding="utf-8", errors="replace")
    matches: list[str] = []
    for pattern in INVALID_EXTRA_PATTERNS:
        matches.extend(pattern.findall(text))
    print(f"invalid_extra_warning_count={len(matches)}")
    if matches:
        raise SystemExit("invalid Python-extra warning detected")


def _check_restored_imports(python: Path, env: dict[str, str], cwd: Path, log_file: Path) -> None:
    code = """
import importlib
mods = %r
for mod in mods:
    module = importlib.import_module(mod)
    print('ok', mod, getattr(module, '__file__', None))
""" % (RESTORED_MODULES,)
    _run([str(python), "-c", code], cwd=cwd, env=env, log_file=log_file, timeout=120)


def _check_direct_url(python: Path, env: dict[str, str], cwd: Path, log_file: Path) -> None:
    code = """
from importlib import metadata
print(metadata.distribution('hermes-agent').read_text('direct_url.json'))
"""
    _run([str(python), "-c", code], cwd=cwd, env=env, log_file=log_file, timeout=60)


def run_smoke(mode: str, install_source: str, python_version: str) -> None:
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("uv is required for NanoHermes registry smoke")

    root = Path(tempfile.mkdtemp(prefix="nanohermes-ci-registry-smoke-"))
    venv = root / "venv"
    hermes_home = root / "hermes-home"
    home = root / "home"
    log_file = root / "registry-smoke.log"
    home.mkdir(parents=True, exist_ok=True)
    hermes_home.mkdir(parents=True, exist_ok=True)

    env = _clean_env(root, venv, hermes_home)
    print(f"root={root}")
    print(f"hermes_home={hermes_home}")
    print(f"log={log_file}")
    print(f"mode={mode}")
    print(f"install_source={install_source}")

    _run([uv, "venv", str(venv), "--python", python_version], cwd=root, env=env, log_file=log_file, timeout=180)
    python = _venv_python(venv)
    _run([uv, "pip", "install", "--python", str(python), install_source], cwd=root, env=env, log_file=log_file, timeout=600)

    _run(["hermes", "--version"], cwd=root, env=env, log_file=log_file, timeout=120)
    _check_direct_url(python, env, root, log_file)

    _run(["hermes", "pkg", "--home", str(hermes_home), "update", "--timeout", "120"], cwd=root, env=env, log_file=log_file, timeout=180)
    registry_path = hermes_home / "packages" / "cache" / "registry-index.json"
    packages = _load_package_names(registry_path)
    print(f"registry_package_count={len(packages)}")

    if mode == "representative-no-pip":
        selected = REPRESENTATIVE_PACKAGES
        missing_from_registry = sorted(set(selected) - set(packages))
        if missing_from_registry:
            raise SystemExit(f"representative packages missing from registry: {missing_from_registry}")
        install_cmd = [
            "hermes",
            "pkg",
            "--home",
            str(hermes_home),
            "install",
            *selected,
            "--yes",
            "--no-pip",
            "--timeout",
            "180",
        ]
    elif mode == "all-real":
        if "browser-engine" not in packages:
            raise SystemExit("browser-engine missing from registry package list")
        selected = packages
        install_cmd = [
            "hermes",
            "pkg",
            "--home",
            str(hermes_home),
            "install",
            *selected,
            "--yes",
            "--timeout",
            "240",
        ]
    else:
        raise SystemExit(f"unknown mode: {mode}")

    print(f"install_package_count={len(selected)}")
    print("install_packages=" + " ".join(selected))
    _run(install_cmd, cwd=root, env=env, log_file=log_file, timeout=1800 if mode == "all-real" else 360)

    state_path = hermes_home / "packages" / "installed.json"
    installed = _load_installed_names(state_path)
    missing = sorted(set(selected) - installed)
    print(f"installed_count={len(installed)}")
    print(f"missing_count={len(missing)}")
    if missing:
        raise SystemExit("packages missing from installed state: " + ", ".join(missing))

    _check_restored_imports(python, env, root, log_file)
    _run(["hermes", "--version"], cwd=root, env=env, log_file=log_file, timeout=120)
    _check_direct_url(python, env, root, log_file)
    _check_invalid_extra_warnings(log_file)

    if mode == "all-real":
        browser_cache = home / ".agent-browser" / "browsers"
        print(f"agent_browser_cache={browser_cache}")
        if browser_cache.exists():
            for child in sorted(browser_cache.iterdir()):
                print(f"browser-cache-entry={child.name}")
        else:
            raise SystemExit("browser-engine did not create an agent-browser cache")

    print("RESULT: PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["representative-no-pip", "all-real"],
        default=os.environ.get("NANOHERMES_REGISTRY_SMOKE_MODE", "representative-no-pip"),
    )
    parser.add_argument(
        "--install-source",
        default=os.environ.get("NANOHERMES_INSTALL_SOURCE", str(_repo_root())),
        help="Package source passed to uv pip install (default: current checkout).",
    )
    parser.add_argument(
        "--python",
        default=os.environ.get("NANOHERMES_PYTHON", "3.11"),
        help="Python version passed to uv venv.",
    )
    args = parser.parse_args()
    run_smoke(args.mode, args.install_source, args.python)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
