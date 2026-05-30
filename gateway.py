"""Compatibility shim for the relocated gateway package.

The real package lives under ``runtime/gateway`` so the repository root stays
small while legacy imports such as ``import gateway`` and ``python -m gateway.x``
keep working from a source checkout.
"""
from __future__ import annotations

from pathlib import Path

_REAL_PACKAGE_DIR = Path(__file__).resolve().parent / "runtime" / "gateway"
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
