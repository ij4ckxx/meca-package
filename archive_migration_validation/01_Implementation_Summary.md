# Implementation Summary — Recovery + Warning Framework (Milestone 11)

## Philosophy change

The engine's job changed from *submission validation* (reject anything imperfect) to *archive migration* (**"always generate the best possible MECA package whenever technically possible"**). No architecture was redesigned — the existing pipeline (extraction → `TransformationCoordinator` → 5 generators → `PackageBuilder`) and every existing generator are reused unchanged in shape. What changed is what happens at each point that used to raise an exception.

## What was built

**1. Finding taxonomy** (`model/warnings.py`): a new `FindingOrigin` enum — `ENGINE_DEFECT`, `SOURCE_DATA_ISSUE`, `BUSINESS_RULE_VIOLATION`, `CONFIGURATION_ISSUE`, `INFORMATIONAL` — added as a field on the existing `EngineWarning` type (not a rewrite of it). A new `is_recovery: bool` field on `EngineWarning` distinguishes "the engine changed something to produce this package" from "this is worth reviewing but nothing was altered."

**2. Package statuses** (`packaging/models.py`): `PackageStatus` extended from `{PASS, PASS_WITH_WARNINGS, FAILED}` to `{PASS, PASS_WITH_WARNINGS, PASS_WITH_RECOVERY, FAILED_ENGINE, FAILED_FATAL}`. Computed automatically in `PackageBuilder.build()` from the warnings and generator diagnostics already collected — no new collection mechanism.

**3. Recovery, not silence, at 5 exception sites** (full rationale per site in `07_Recovery_Matrix.md`):
- `extraction/round_resolver.py` — a malformed `<article-version>` is skipped (not fatal); duplicate `(sequence_number, label)` snapshot events are deduplicated to one round. A genuine label *conflict* still raises (ADR-013 unchanged).
- `extraction/file_resolver.py` — fixed a real bug in the tier-3 filename-matching tolerance (compared the wrong string, so a disambiguating "(N)" suffix could never match, despite the code's own docstring claiming to handle it); non-exact matches now emit a warning instead of resolving silently; a missing file in any category **other than `manuscript`** is skipped with a warning instead of failing the whole package.
- `generators/article_xml/generator.py` — an unmapped License Type (a config gap) now omits the `<license>` block with a warning, matching the already-existing non-CC-BY no-op path, instead of raising.
- `generators/reviews_xml/review_builder.py` — a reviewer scorecard with real recommendation content but no identity now keeps the content and omits the identity, with a warning, instead of discarding it.

**4. Conversion Report model** (`packaging/conversion_report.py`, new module): `ConversionReport` — JSON-ready via `to_dict()` — with `status`, `confidence_score`, `warnings` (advisory), `recoveries` (`is_recovery=True`), `generator_findings` (the pre-existing `GeneratorDiagnostic` system, carried through unmodified), `unrecoverable_error`, and `business_rule_findings` (extracted from both sources). Built by `build_conversion_report()` from either a successful `StagedPackage` or a raised exception — no new orchestrator.

## What was deliberately not touched

- No generator's XML-producing logic changed shape — only what happens when an input is missing/unmappable.
- `input/`, `orchestrator/`, `registry/`, `retry/` — unused by the real batch pipeline today, out of scope.
- `GeneratorDiagnostic` itself — reused as-is; its existing `warn()`/`info()` methods already meant "recoverable issue" / "informational," which is exactly what was needed.
- The Business Rule Book text — not rewritten (per standing instruction from the prior validation round).

## Result

Re-running the full 37-package corpus (see `03_End_to_End_Batch_Summary.md`): **37/37 packages now generate**, up from 30/37 before this milestone. All 7 previously-failing packages recover; zero packages required fabrication to do so.
