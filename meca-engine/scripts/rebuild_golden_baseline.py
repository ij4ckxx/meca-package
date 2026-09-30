#!/usr/bin/env python
"""Operator entry point: regenerate the golden-file regression baseline.

Thin wrapper around ``meca-engine rebuild-golden-baseline``
(10_LLD_01_STRUCTURE_AND_PACKAGES.md §1). Placeholder in Milestone 1 — see
:mod:`meca_engine.cli.main` and 14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md §11.3.
"""

from __future__ import annotations

import sys

from meca_engine.cli.main import cli

if __name__ == "__main__":
    cli(["rebuild-golden-baseline", *sys.argv[1:]])
