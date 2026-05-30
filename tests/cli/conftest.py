"""CLI test isolation helpers.

Several CLI tests intentionally reload or evict ``hermes_runtime.cli`` to test
startup-time config behavior.  Python packages keep submodules as attributes on
the parent package, so removing ``sys.modules['hermes_runtime.cli']`` can leave
``hermes_runtime.cli`` pointing at a stale module object.  That was harmless
when ``cli.py`` lived at repo root, but after moving it under
``runtime/hermes_runtime/`` stale parent-package attributes can make string
patches hit one module while direct imports call another.
"""

from __future__ import annotations

import sys

import pytest


def _sync_cli_parent_attr() -> None:
    pkg = sys.modules.get("hermes_runtime")
    if pkg is None:
        return
    mod = sys.modules.get("hermes_runtime.cli")
    if mod is None:
        # Ensure the next import does real import resolution instead of returning
        # a stale package attribute left by a prior module eviction test.
        if getattr(pkg, "cli", None) is not None:
            try:
                delattr(pkg, "cli")
            except AttributeError:
                pass
        return
    setattr(pkg, "cli", mod)


@pytest.fixture(autouse=True)
def _repair_hermes_runtime_cli_module_alias():
    _sync_cli_parent_attr()
    yield
    _sync_cli_parent_attr()
