"""Test package namespace bridge for source-tree imports.

When a test inserts tests/ onto sys.path, this package can shadow the real
source package of the same name.  Append the matching source package path so
imports like `gateway.run` or `plugins.browser.browserbase` still resolve
without root-level shim files.
"""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REL = Path(__file__).resolve().parent.relative_to(_REPO_ROOT / "tests")
for _base in (_REPO_ROOT / "runtime", _REPO_ROOT):
    _candidate = _base / _REL
    if _candidate.is_dir():
        _candidate_s = str(_candidate)
        if _candidate_s not in __path__:
            __path__.append(_candidate_s)
