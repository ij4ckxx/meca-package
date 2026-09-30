"""Validation Engine.

Runs after a package is already built; never invoked from within a
generator, never able to stop package generation.

**XML structural validation (DTD conformance + well-formedness) is
implemented** — see :mod:`meca_engine.validation.xml_validator` and
:mod:`meca_engine.validation.models`.

**Business Rule Book content validation remains not implemented** — see
:mod:`meca_engine.validation.rules`'s own docstring,
13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md §10 for the full design, and
`08_IMPLEMENTATION_ROADMAP.md` for the phase that implements it. That
scope stays a stub deliberately: this milestone only validates XML
structure, and only *recommends* Business Rule changes — it never
changes any Business Rule automatically.
"""

from __future__ import annotations

from meca_engine.validation.models import (
    FileValidationReport,
    PackageValidationReport,
    ValidationResult,
)
from meca_engine.validation.package_validator import validate_staged_package
from meca_engine.validation.xml_validator import validate_generated_file

__all__ = [
    "FileValidationReport",
    "PackageValidationReport",
    "ValidationResult",
    "validate_generated_file",
    "validate_staged_package",
]
