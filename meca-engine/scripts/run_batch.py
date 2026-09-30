#!/usr/bin/env python
"""Operator entry point: trigger a batch run.

Thin wrapper around ``meca-engine run``
(10_LLD_01_STRUCTURE_AND_PACKAGES.md §1). The ``run`` command itself is a
placeholder in Milestone 1 — see :mod:`meca_engine.cli.main`.
"""

from __future__ import annotations

import sys

from meca_engine.cli.main import cli

if __name__ == "__main__":
    cli(["run", *sys.argv[1:]])
