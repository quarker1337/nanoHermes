"""Compatibility shim for the relocated providers package.

The real package lives under ``runtime/providers`` so the repository root stays
small while legacy imports such as ``import providers`` and ``python -m providers.x``
keep working from a source checkout.
"""
from __future__ import annotations

from pathlib import Path

_REAL_PACKAGE_DIR = Path(__file__).resolve().parent / "runtime" / "providers"
_REAL_INIT = _REAL_PACKAGE_DIR / "__init__.py"

__path__ = [str(_REAL_PACKAGE_DIR)]
__file__ = str(_REAL_INIT)
__package__ = __name__

try:
    __spec__.origin = __file__  # type: ignore[name-defined, union-attr]
    __spec__.submodule_search_locations = __path__  # type: ignore[name-defined, union-attr]
except Exception:
    pass

if _REAL_INIT.exists():
    exec(compile(_REAL_INIT.read_text(encoding="utf-8"), __file__, "exec"), globals())
