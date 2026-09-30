"""Reporting Engine — Milestone 13 (Archive Migration Certification & Reporting).

Builds every human- and machine-readable report a real archive-migration
project needs, from a batch of
:class:`~meca_engine.packaging.conversion_report.ConversionReport`
instances: per-article Certification Reports, the executive Migration
Summary, the customer-facing audit log and manual-review queue,
management-facing recovery/business-rule analytics, and a dashboard-ready
JSON export. Reporting only — no transformation, generation, or
business-rule logic lives here; every function reads an already-built
``ConversionReport`` and reshapes it.
"""

from __future__ import annotations
