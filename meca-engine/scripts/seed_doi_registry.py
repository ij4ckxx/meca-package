#!/usr/bin/env python
"""Operator entry point: one-time import of historically-issued DOIs.

Thin wrapper around ``meca-engine seed-doi-registry``
(10_LLD_01_STRUCTURE_AND_PACKAGES.md §1). Placeholder in Milestone 1 — see
:mod:`meca_engine.cli.main`.
"""

from __future__ import annotations

import sys

from meca_engine.cli.main import cli

if __name__ == "__main__":
    cli(["seed-doi-registry", *sys.argv[1:]])
