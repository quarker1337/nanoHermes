"""Agent internals -- extracted modules from runtime/hermes_runtime/run_agent.py.

These modules contain pure utility functions and self-contained classes
that were previously embedded in the 3,600-line runtime/hermes_runtime/run_agent.py. Extracting
them makes runtime/hermes_runtime/run_agent.py focused on the AIAgent orchestrator class.
"""

from . import jiter_preload as _jiter_preload  # noqa: F401
