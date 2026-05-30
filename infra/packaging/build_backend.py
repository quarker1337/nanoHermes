"""PEP 517 build backend for NanoHermes packaging.

The repository keeps runtime payloads such as bundled skills outside Python
packages under ``resources/``. Setuptools' declarative ``data-files`` table can
include globs, but a single destination flattens nested trees. The moved setup
script builds one data-file entry per directory so wheel installs preserve paths
like ``resources/skills/media/youtube-content/SKILL.md`` without requiring a
root-level ``setup.py``.
"""

from __future__ import annotations

from setuptools import build_meta as _build_meta


class _NanoHermesBuildBackend(_build_meta._BuildMetaBackend):
    def run_setup(self, setup_script: str = "setup.py") -> None:
        super().run_setup(setup_script="infra/packaging/setup.py")


_BACKEND = _NanoHermesBuildBackend()

get_requires_for_build_wheel = _BACKEND.get_requires_for_build_wheel
get_requires_for_build_sdist = _BACKEND.get_requires_for_build_sdist
get_requires_for_build_editable = _BACKEND.get_requires_for_build_editable
prepare_metadata_for_build_wheel = _BACKEND.prepare_metadata_for_build_wheel
prepare_metadata_for_build_editable = _BACKEND.prepare_metadata_for_build_editable
build_wheel = _BACKEND.build_wheel
build_sdist = _BACKEND.build_sdist
build_editable = _BACKEND.build_editable
