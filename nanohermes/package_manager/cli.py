from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .registry import (
    DEFAULT_REGISTRY_TIMEOUT_SECONDS,
    DEFAULT_REGISTRY_URL,
    PackageRegistry,
    PackageRegistryError,
    is_http_source,
)
from .state import PackageState


def _truthy_permission_names(package: dict) -> list[str]:
    permissions = package.get("permissions", {})
    return sorted(
        name for name, value in permissions.items()
        if value is True and name != "secrets"
    )


def _format_package_line(package: dict) -> str:
    return f"{package['name']} {package.get('version', '')} - {package.get('description', '')}"


def _print_install_plan(packages: list[dict]) -> None:
    print("Install plan")
    for package in packages:
        install = package.get("install", {})
        extras = install.get("python_extras", [])
        tools = package.get("tools", {})
        permissions = _truthy_permission_names(package)
        print(f"  {package['name']} {package.get('version', '')}")
        if extras:
            print(f"    Python extras: {', '.join(extras)}")
        if tools.get("toolsets"):
            print(f"    Toolsets: {', '.join(tools['toolsets'])}")
        if tools.get("tools"):
            print(f"    Tools: {', '.join(tools['tools'])}")
        if permissions:
            print(f"    Permissions: {', '.join(permissions)}")


def _install_python_extras(extras: list[str]) -> None:
    if not extras:
        return
    project_root = Path(__file__).resolve().parents[2]
    extras_arg = ".[{}]".format(",".join(sorted(set(extras))))
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", extras_arg], cwd=project_root)


def _registry_source(args: argparse.Namespace) -> str | Path:
    return args.source or DEFAULT_REGISTRY_URL


def _registry_timeout(args: argparse.Namespace) -> float:
    return float(getattr(args, "timeout", DEFAULT_REGISTRY_TIMEOUT_SECONDS))


def _update_registry(registry: PackageRegistry, source: str | Path, *, timeout: float) -> dict | None:
    source_str = str(source)
    if is_http_source(source_str):
        print(f"Fetching package registry: {source_str} (timeout {timeout:g}s)", file=sys.stderr, flush=True)
    try:
        return registry.update(source, timeout=timeout)
    except PackageRegistryError as exc:
        print(f"Package registry update failed: {exc}", file=sys.stderr)
        if is_http_source(source_str):
            print(
                "Try `hermes pkg update --timeout 60`, check proxy/DNS access to raw.githubusercontent.com,",
                file=sys.stderr,
            )
            print(
                "or use `hermes pkg --source /path/to/registry/index.json update` for an offline registry.",
                file=sys.stderr,
            )
        return None


def cmd_update(args: argparse.Namespace) -> int:
    registry = PackageRegistry(home=args.home)
    index = _update_registry(registry, _registry_source(args), timeout=_registry_timeout(args))
    if index is None:
        return 1
    print(f"Updated package registry: {index.get('package_count', len(index.get('packages', {})))} packages")
    print(registry.index_path)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    registry = PackageRegistry(home=args.home)
    if args.source:
        if _update_registry(registry, args.source, timeout=_registry_timeout(args)) is None:
            return 1
    matches = registry.search(args.query)
    if not matches:
        print("No packages found")
        return 1
    for package in matches:
        print(_format_package_line(package))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    registry = PackageRegistry(home=args.home)
    if args.source:
        if _update_registry(registry, args.source, timeout=_registry_timeout(args)) is None:
            return 1
    package = registry.get(args.name)
    print(_format_package_line(package))
    print(f"Channel: {package.get('channel')}")
    print(f"Type: {package.get('type')}")
    install = package.get("install", {})
    tools = package.get("tools", {})
    if install.get("python_extras"):
        print(f"Python extras: {', '.join(install['python_extras'])}")
    if tools.get("toolsets"):
        print(f"Toolsets: {', '.join(tools['toolsets'])}")
    permissions = _truthy_permission_names(package)
    if permissions:
        print(f"Permissions: {', '.join(permissions)}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    registry = PackageRegistry(home=args.home)
    source = _registry_source(args)
    if _update_registry(registry, source, timeout=_registry_timeout(args)) is None:
        return 1
    packages = registry.resolve_with_dependencies(args.packages)
    _print_install_plan(packages)
    if args.dry_run:
        return 0
    if not args.yes:
        print("Refusing to install without --yes or --dry-run.", file=sys.stderr)
        return 2
    extras: list[str] = []
    for package in packages:
        extras.extend(package.get("install", {}).get("python_extras", []))
    if not args.no_pip:
        _install_python_extras(extras)
    state = PackageState(home=args.home)
    for package in packages:
        state.mark_installed(package, source=str(source))
        print(f"Installed {package['name']} {package.get('version', '')}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    state = PackageState(home=args.home)
    installed = state.installed
    if not installed:
        print("No packages installed")
        return 0
    for name, package in sorted(installed.items()):
        print(f"{name} {package.get('version', '')}")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    state = PackageState(home=args.home)
    rc = 0
    for name in args.packages:
        if state.remove(name):
            print(f"Removed {name}")
        else:
            print(f"Package is not installed: {name}", file=sys.stderr)
            rc = 1
    return rc


def cmd_doctor(args: argparse.Namespace) -> int:
    registry = PackageRegistry(home=args.home)
    state = PackageState(home=args.home)
    print(f"Home: {registry.home}")
    print(f"Registry cache: {registry.index_path} ({'present' if registry.index_path.exists() else 'missing'})")
    print(f"Installed packages: {len(state.installed)}")
    return 0


def _populate_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--home", type=Path, default=None, help="Override HERMES_HOME for package state")
    parser.add_argument("--source", default=None, help="Registry index URL or local path")
    sub = parser.add_subparsers(dest="pkg_command")

    update = sub.add_parser("update", help="Refresh registry cache")
    update.add_argument("--timeout", type=float, default=DEFAULT_REGISTRY_TIMEOUT_SECONDS, help="Registry fetch timeout in seconds")
    update.set_defaults(func=cmd_update)

    search = sub.add_parser("search", help="Search packages")
    search.add_argument("query")
    search.add_argument("--timeout", type=float, default=DEFAULT_REGISTRY_TIMEOUT_SECONDS, help="Registry fetch timeout in seconds")
    search.set_defaults(func=cmd_search)

    show = sub.add_parser("show", help="Show package details")
    show.add_argument("name")
    show.add_argument("--timeout", type=float, default=DEFAULT_REGISTRY_TIMEOUT_SECONDS, help="Registry fetch timeout in seconds")
    show.set_defaults(func=cmd_show)

    install = sub.add_parser("install", help="Install packages")
    install.add_argument("packages", nargs="+")
    install.add_argument("--dry-run", action="store_true", help="Print plan without changing state")
    install.add_argument("--yes", "-y", action="store_true", help="Apply install plan without prompting")
    install.add_argument("--no-pip", action="store_true", help="Record package state without invoking pip")
    install.add_argument("--timeout", type=float, default=DEFAULT_REGISTRY_TIMEOUT_SECONDS, help="Registry fetch timeout in seconds")
    install.set_defaults(func=cmd_install)

    remove = sub.add_parser("remove", aliases=["rm"], help="Remove packages from local state")
    remove.add_argument("packages", nargs="+")
    remove.set_defaults(func=cmd_remove)

    list_cmd = sub.add_parser("list", aliases=["ls"], help="List installed packages")
    list_cmd.set_defaults(func=cmd_list)

    doctor = sub.add_parser("doctor", help="Inspect package-manager state")
    doctor.set_defaults(func=cmd_doctor)
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes pkg", description="NanoHermes package manager")
    return _populate_parser(parser)


def register_parser(subparsers, name: str = "pkg", *, help_text: str | None = None) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        name,
        help=help_text or "Manage NanoHermes packages",
        description="Update, search, inspect, install, and remove NanoHermes packages.",
    )
    return _populate_parser(parser)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return int(args.func(args) or 0)


def cmd_pkg(args: argparse.Namespace) -> int:
    return main(getattr(args, "pkg_args", []))


if __name__ == "__main__":
    raise SystemExit(main())
