"""MECA Package Generation Engine.

Automated NISO MECA package builder for journal submissions, built against the
approved project documentation set (Reverse Engineering Report, Functional
Specification, Business Rule Book, ADRs, Test Specification, Product Backlog,
HLD, LLD, Risk Register, Implementation Roadmap).

This module intentionally exposes nothing but the package version. Every
piece of behaviour lives in a dedicated subpackage per the layered structure
defined in 10_LLD_01_STRUCTURE_AND_PACKAGES.md §2.
"""

from __future__ import annotations

__version__ = "1.0.0-rc1"

__all__ = ["__version__"]
