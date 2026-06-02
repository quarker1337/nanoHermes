from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as importlib_metadata
import io
import json
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
import zipfile
from pathlib import Path
from pathlib import PurePosixPath
from urllib.parse import parse_qs
from urllib.parse import urljoin
from urllib.parse import urlparse

from .registry import (
    DEFAULT_REGISTRY_TIMEOUT_SECONDS,
    DEFAULT_REGISTRY_URL,
    PackageRegistry,
    PackageRegistryError,
    _fetch_url_with_deadline,
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


def _included_skills(package: dict) -> list[str]:
    contents = package.get("contents", {}) if isinstance(package.get("contents", {}), dict) else {}
    return sorted(str(skill) for skill in contents.get("skills", []) if str(skill).strip())


def _print_included_skills(package: dict) -> None:
    skills = _included_skills(package)
    if not skills:
        return
    print("Included skills:")
    for skill in skills:
        print(f"  - {skill}")


def _runtime_dependencies(packages: list[dict]) -> list[str]:
    deps: list[str] = []
    seen: set[str] = set()
    for package in packages:
        install = package.get("install", {}) if isinstance(package.get("install", {}), dict) else {}
        for dep in install.get("runtime_dependencies", []) or []:
            dep_name = str(dep).strip()
            if dep_name and dep_name not in seen:
                deps.append(dep_name)
                seen.add(dep_name)
    return deps


def _print_install_plan(packages: list[dict]) -> None:
    print("Install plan")
    for package in packages:
        install = package.get("install", {})
        extras = install.get("python_extras", [])
        assets = install.get("optional_assets", [])
        runtime_deps = [
            str(dep)
            for dep in install.get("runtime_dependencies", []) or []
            if str(dep).strip()
        ]
        npm_packages = [
            str(package_name)
            for package_name in install.get("npm_packages", []) or []
            if str(package_name).strip()
        ]
        tools = package.get("tools", {})
        permissions = _truthy_permission_names(package)
        print(f"  {package['name']} {package.get('version', '')}")
        if extras:
            print(f"    Python extras: {', '.join(extras)}")
        if assets:
            destinations = []
            for asset in assets:
                if isinstance(asset, dict) and asset.get("destination"):
                    destinations.append(str(asset["destination"]))
            if destinations:
                print(f"    Optional assets: {', '.join(destinations)}")
            else:
                print(f"    Optional assets: {len(assets)}")
        if runtime_deps:
            print(f"    Runtime dependencies: {', '.join(runtime_deps)}")
        if npm_packages:
            print(f"    NPM packages: {', '.join(npm_packages)}")
        included = _included_skills(package)
        if included:
            print(f"    Included skills: {len(included)}")
        if tools.get("toolsets"):
            print(f"    Toolsets: {', '.join(tools['toolsets'])}")
        if tools.get("tools"):
            print(f"    Tools: {', '.join(tools['tools'])}")
        if permissions:
            print(f"    Permissions: {', '.join(permissions)}")


_DISTRIBUTION_NAME = "hermes-agent"


def _extras_suffix(extras: list[str]) -> str:
    names = sorted({str(extra).strip() for extra in extras if str(extra).strip()})
    return "[{}]".format(",".join(names)) if names else ""


def _editable_project_root() -> Path | None:
    """Return the checkout root when this code is running from source.

    Installed wheels/archives put ``hermes_cli`` under site-packages, where
    ``parents[2]`` is not a project checkout.  Only use an editable local target
    when a pyproject is really present; package installs from remote archives
    need to reinstall the current distribution source instead.
    """
    project_root = Path(__file__).resolve().parents[2]
    return project_root if (project_root / "pyproject.toml").is_file() else None


def _direct_url_distribution_target(extras: list[str], distribution_name: str = _DISTRIBUTION_NAME) -> str | None:
    """Return ``name[extras] @ url`` for remote archive/VCS installs.

    Minimal NanoHermes installs are commonly installed by uv from the GitHub
    branch tarball.  PEP 610 metadata records that URL; preserving it prevents
    optional package installs from accidentally switching the tester back to the
    upstream PyPI ``hermes-agent`` package.
    """
    try:
        dist = importlib_metadata.distribution(distribution_name)
        raw = dist.read_text("direct_url.json")
        if not raw:
            return None
        data = json.loads(raw)
        url = str(data.get("url") or "").strip()
        if not url:
            return None
        if data.get("archive_info") is None and data.get("vcs_info") is None:
            return None
        if not url.startswith(("http://", "https://", "git+http://", "git+https://", "ssh://", "git+ssh://")):
            return None
        return f"{distribution_name}{_extras_suffix(extras)} @ {url}"
    except Exception:
        return None


def _python_extras_install_target(extras: list[str]) -> tuple[str, Path | None, bool]:
    project_root = _editable_project_root()
    if project_root is not None:
        return f".{_extras_suffix(extras)}", project_root, True
    direct_target = _direct_url_distribution_target(extras)
    if direct_target:
        return direct_target, None, False
    return f"{_DISTRIBUTION_NAME}{_extras_suffix(extras)}", None, False


def _install_python_extras(extras: list[str]) -> None:
    if not extras:
        return
    target, cwd, editable = _python_extras_install_target(extras)
    uv = shutil.which("uv")
    if uv:
        cmd = [uv, "pip", "install", "--python", sys.executable, "--upgrade"]
        if editable:
            cmd.extend(["-e", target])
        else:
            cmd.append(target)
    else:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
        if editable:
            cmd.extend(["-e", target])
        else:
            cmd.append(target)
    subprocess.check_call(cmd, cwd=cwd)


def _install_runtime_dependencies(deps: list[str], *, home: str | Path | None = None) -> None:
    if not deps:
        return
    from hermes_cli.dep_ensure import ensure_dependency

    for dep in deps:
        print(f"Installing runtime dependency: {dep}")
        ok = ensure_dependency(
            dep,
            interactive=False,
            respect_decline=False,
            home=home,
            force=True,
        )
        if not ok:
            raise PackageRegistryError(f"Runtime dependency install failed: {dep}")


_HOME_ASSET_ROOTS = {"skills", "optional-skills", "optional-mcps", "apps"}
_PYTHON_SITE_PACKAGES_ROOT = "python-site-packages"
_APP_ASSET_ROOT = "apps"
_ALLOWED_ASSET_ROOTS = _HOME_ASSET_ROOTS | {_PYTHON_SITE_PACKAGES_ROOT}


def _safe_relative_parts(path: str, *, label: str) -> tuple[str, ...]:
    pure = PurePosixPath(path.replace("\\", "/"))
    parts = tuple(part for part in pure.parts if part not in {"", "."})
    if pure.is_absolute() or not parts or any(part == ".." for part in parts):
        raise PackageRegistryError(f"Unsafe package asset {label}: {path}")
    return parts


def _python_site_packages_root() -> Path:
    purelib = sysconfig.get_paths().get("purelib")
    if not purelib:
        raise PackageRegistryError("Could not resolve Python site-packages directory")
    return Path(purelib).expanduser().resolve()


def _safe_asset_destination(home: str | Path | None, destination: str) -> Path:
    parts = _safe_relative_parts(destination, label="destination")
    root_name = parts[0]
    if root_name in _HOME_ASSET_ROOTS:
        if root_name == _APP_ASSET_ROOT and len(parts) < 2:
            raise PackageRegistryError(
                "apps asset destination must include an app subdirectory"
            )
        root = Path(home).expanduser().resolve() if home is not None else PackageState().home.resolve()
        relative_parts = parts
    elif root_name == _PYTHON_SITE_PACKAGES_ROOT:
        if len(parts) < 2:
            raise PackageRegistryError(
                "python-site-packages asset destination must include a package subdirectory"
            )
        root = _python_site_packages_root()
        relative_parts = parts[1:]
    else:
        allowed = ", ".join(sorted(_ALLOWED_ASSET_ROOTS))
        raise PackageRegistryError(
            f"Package asset destination must start with one of: {allowed}; got {destination!r}"
        )

    target = root.joinpath(*relative_parts).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise PackageRegistryError(f"Package asset destination escapes install root: {destination}") from exc
    return target


def _resolve_local_asset_source(source: str, registry_source: str | Path) -> Path:
    source_path = Path(source).expanduser()
    if source_path.is_absolute():
        return source_path

    registry_path = Path(str(registry_source)).expanduser()
    base = registry_path.parent
    # Registry files normally live under <repo>/registry/index.json. Resolve
    # relative asset paths from the repo root so manifests can use
    # assets/skills/foo.tar.gz consistently in tests and offline mirrors.
    if registry_path.parent.name == "registry" and registry_path.name.startswith("index"):
        base = registry_path.parent.parent
    return (base / source_path).resolve()


def _resolve_remote_asset_source(source: str, registry_source: str | Path) -> str:
    parts = _safe_relative_parts(source, label="source")
    source_rel = "/".join(parts)
    parsed = urlparse(str(registry_source))

    if parsed.netloc == "api.github.com" and "/contents/registry/index.json" in parsed.path:
        # GitHub Contents API default:
        #   /repos/<owner>/<repo>/contents/registry/index.json?ref=<branch>
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 5 and path_parts[0] == "repos":
            owner = path_parts[1]
            repo = path_parts[2]
            ref = parse_qs(parsed.query).get("ref", ["main"])[0]
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{source_rel}"

    if parsed.netloc == "raw.githubusercontent.com" and parsed.path.endswith("/registry/index.json"):
        base_path = parsed.path[: -len("/registry/index.json")]
        return f"{parsed.scheme}://{parsed.netloc}{base_path}/{source_rel}"

    return urljoin(str(registry_source), f"../{source_rel}")


def _read_asset_bytes(source: str, registry_source: str | Path, *, timeout: float) -> bytes:
    if is_http_source(source):
        return _fetch_url_with_deadline(source, timeout=max(float(timeout), 0.1))
    if is_http_source(str(registry_source)):
        return _fetch_url_with_deadline(
            _resolve_remote_asset_source(source, registry_source),
            timeout=max(float(timeout), 0.1),
        )
    local_source = _resolve_local_asset_source(source, registry_source)
    try:
        return local_source.read_bytes()
    except OSError as exc:
        raise PackageRegistryError(f"Failed to read package asset {source}: {exc}") from exc


def _verify_asset_sha256(payload: bytes, expected: str, *, source: str) -> None:
    expected = (expected or "").strip().lower()
    if not expected:
        return
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise PackageRegistryError(
            f"Package asset checksum mismatch for {source}: expected {expected}, got {actual}"
        )


def _assert_safe_archive_member(name: str) -> None:
    _safe_relative_parts(name, label="archive member")


def _extract_asset_archive(payload: bytes, fmt: str, target_dir: Path) -> None:
    fmt = fmt.lower().replace("_", "-")
    if fmt in {"tar.gz", "tgz", "tar", "tar.bz2", "tbz2", "tar.xz", "txz"}:
        try:
            with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
                for member in archive.getmembers():
                    _assert_safe_archive_member(member.name)
                    if member.issym() or member.islnk() or member.isdev():
                        raise PackageRegistryError(f"Unsafe package asset archive member: {member.name}")
                archive.extractall(target_dir)
            return
        except (tarfile.TarError, OSError) as exc:
            if isinstance(exc, PackageRegistryError):
                raise
            raise PackageRegistryError(f"Failed to extract package asset archive: {exc}") from exc

    if fmt == "zip":
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                for info in archive.infolist():
                    _assert_safe_archive_member(info.filename)
                archive.extractall(target_dir)
            return
        except (zipfile.BadZipFile, OSError) as exc:
            raise PackageRegistryError(f"Failed to extract package asset archive: {exc}") from exc

    raise PackageRegistryError(f"Unsupported package asset format: {fmt}")


def _infer_asset_format(source: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    lower = source.lower()
    for suffix, fmt in (
        (".tar.gz", "tar.gz"),
        (".tgz", "tgz"),
        (".tar.bz2", "tar.bz2"),
        (".tbz2", "tbz2"),
        (".tar.xz", "tar.xz"),
        (".txz", "txz"),
        (".tar", "tar"),
        (".zip", "zip"),
    ):
        if lower.endswith(suffix):
            return fmt
    raise PackageRegistryError(f"Could not infer package asset format from source: {source}")


def _merge_asset_tree(source_dir: Path, destination: Path, *, overwrite: bool) -> tuple[int, int]:
    copied = 0
    skipped = 0
    for path in sorted(source_dir.rglob("*")):
        rel = path.relative_to(source_dir)
        target = destination / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if not path.is_file():
            continue
        if target.exists() and not overwrite:
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    return copied, skipped


def _install_optional_assets(
    packages: list[dict],
    *,
    home: str | Path | None,
    registry_source: str | Path,
    timeout: float,
) -> None:
    for package in packages:
        install = package.get("install", {}) if isinstance(package.get("install", {}), dict) else {}
        assets = install.get("optional_assets", []) or []
        for asset in assets:
            if not isinstance(asset, dict):
                raise PackageRegistryError(f"Package {package['name']} has invalid optional asset entry: {asset!r}")
            source = str(asset.get("source", "")).strip()
            destination = str(asset.get("destination", "")).strip()
            if not source or not destination:
                raise PackageRegistryError(
                    f"Package {package['name']} optional asset requires source and destination"
                )
            payload = _read_asset_bytes(source, registry_source, timeout=timeout)
            _verify_asset_sha256(payload, str(asset.get("sha256", "")), source=source)
            fmt = _infer_asset_format(source, asset.get("format"))
            destination_path = _safe_asset_destination(home, destination)
            overwrite = bool(asset.get("overwrite", False))
            with tempfile.TemporaryDirectory(prefix="hermes-pkg-asset-") as tmp:
                extract_root = Path(tmp) / "extract"
                extract_root.mkdir()
                _extract_asset_archive(payload, fmt, extract_root)
                copied, skipped = _merge_asset_tree(extract_root, destination_path, overwrite=overwrite)
            print(
                f"Installed asset for {package['name']} -> {destination} "
                f"({copied} files copied, {skipped} existing kept)"
            )


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
                "Try `hermes pkg update --timeout 60`, check proxy/DNS access to GitHub,",
                file=sys.stderr,
            )
            print(
                "or use `hermes pkg --source /path/to/registry/index.json update` for an offline registry.",
                file=sys.stderr,
            )
        return None


def _print_registry_error(exc: PackageRegistryError) -> int:
    print(str(exc), file=sys.stderr)
    return 1


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
    try:
        matches = registry.search(args.query)
    except PackageRegistryError as exc:
        return _print_registry_error(exc)
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
    try:
        package = registry.get(args.name)
    except PackageRegistryError as exc:
        return _print_registry_error(exc)
    print(_format_package_line(package))
    print(f"Channel: {package.get('channel')}")
    print(f"Type: {package.get('type')}")
    dependencies = [str(dep) for dep in package.get("dependencies", []) if str(dep).strip()]
    if dependencies:
        print(f"Dependencies: {', '.join(dependencies)}")
    install = package.get("install", {})
    tools = package.get("tools", {})
    if install.get("python_extras"):
        print(f"Python extras: {', '.join(install['python_extras'])}")
    if tools.get("toolsets"):
        print(f"Toolsets: {', '.join(tools['toolsets'])}")
    _print_included_skills(package)
    permissions = _truthy_permission_names(package)
    if permissions:
        print(f"Permissions: {', '.join(permissions)}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    registry = PackageRegistry(home=args.home)
    source = _registry_source(args)
    if _update_registry(registry, source, timeout=_registry_timeout(args)) is None:
        return 1
    try:
        requested_names = {registry.resolve_name(name) for name in args.packages}
        packages = registry.resolve_with_dependencies(args.packages)
    except PackageRegistryError as exc:
        return _print_registry_error(exc)
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
    try:
        _install_optional_assets(
            packages,
            home=args.home,
            registry_source=source,
            timeout=_registry_timeout(args),
        )
        _install_runtime_dependencies(_runtime_dependencies(packages), home=args.home)
    except PackageRegistryError as exc:
        return _print_registry_error(exc)
    state = PackageState(home=args.home)
    for package in packages:
        state.mark_installed(
            package,
            source=str(source),
            requested=package["name"] in requested_names,
        )
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
    parser = argparse.ArgumentParser(prog="hermes pkg", description="NanoHermes package manager for optional tools, plugins, and skill packs")
    return _populate_parser(parser)


def register_parser(subparsers, name: str = "pkg", *, help_text: str | None = None) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        name,
        help=help_text or "Manage NanoHermes packages",
        description="Update, search, inspect, install, and remove NanoHermes packages, including optional skill packs.",
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
