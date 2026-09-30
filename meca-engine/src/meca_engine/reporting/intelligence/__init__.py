"""Migration Intelligence Layer — Milestone 14.

Analytics and recommendation modules built strictly on top of already-produced
:class:`~meca_engine.packaging.conversion_report.ConversionReport` instances —
no validation is re-run, no generator/Business Rule/Recovery Rule/certification
logic is touched. This package answers one question for product owners:
"given everything the engine has already observed, what should we change
about the process?" — using simple, deterministic, evidence-backed rules
only. No AI, no heuristics that aren't directly traceable to counted data.
"""

from __future__ import annotations
