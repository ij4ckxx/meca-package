"""Unit test for meca_engine.model.collections.

This module holds only `TYPE_CHECKING`-guarded alias assignments (see its
own module docstring) — nothing else in the codebase imports it at
runtime, so nothing exercises its two real top-level statements
(`from __future__ import annotations` / `from typing import
TYPE_CHECKING`) unless a test imports it directly, as below.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_module_imports_without_error() -> None:
    module = importlib.import_module("meca_engine.model.collections")
    assert module is not None
