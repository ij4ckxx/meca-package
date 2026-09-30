#!/usr/bin/env python
"""Operator entry point: validate the configuration tree.

Thin wrapper around ``meca-engine validate-config``
(10_LLD_01_STRUCTURE_AND_PACKAGES.md §1: "small operator-facing entry
points, not part of the library API"). The real implementation lives in
:mod:`meca_engine.cli.main`.
"""

from __future__ import annotations

import sys

from meca_engine.cli.main import cli

if __name__ == "__main__":
    cli(["validate-config", *sys.argv[1:]])
