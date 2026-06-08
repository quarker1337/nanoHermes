"""Legacy flat import shim for NanoHermes runtime-bucket layout.

The implementation lives in :mod:`hermes_runtime.toolsets`.  Replace this
module entry with the canonical runtime module so older callers and tests that
still do ``import toolsets`` patch the same object used by runtime code.
"""

from importlib import import_module
import sys

_module = import_module("hermes_runtime.toolsets")
sys.modules[__name__] = _module
