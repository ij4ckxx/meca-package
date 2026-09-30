# Phase 1 Implementation Summary — Configuration & Provider Framework

## What changed

Extended the existing config system and introduced an Input/Output Provider
abstraction so the batch script no longer hand-builds its config or hardcodes
filesystem paths. No conversion logic (generators, `PackageBuilder`, ICAM,
business/recovery rules, reporting, intelligence, certification) was touched.

## Architecture decisions

**Config: extended, not duplicated.** Added `InputSettings`, `DashboardSettings`,
`LoggingSettings` to `config/schema.py`, wired through `ConfigLoader`, validated
by `schemas/config-schema/runtime.schema.json`. `OutputSettings` gained
`provider`/`local_path` as fields with defaults (16 existing call sites stay
valid). `RuntimeConfig` gained `input`/`dashboard`/`logging` as required fields
(consistent with its existing convention); all 15 existing construction sites
(scripts, golden tests, conftest fixtures) were updated to pass them.

**Provider architecture: Option B, not Option A.** The revised spec offered a
choice — Option A (promote the existing `input/readers/` package into the new
provider interfaces) or Option B (document those readers as superseded). I
implemented **Option B**, which is a deviation from what I originally told you
I'd do ("Option A: promote existing input/readers").

Reason: `LocalFolderReader` assumes a pre-extracted `<root>/<ArticleID>/<Round>/<file>`
layout. The real `Input/` holds `.zip` archives with a further nested
`<ArticleID>/<ArticleID>/<Round>/...` shape inside each zip, and extraction
itself was never part of `input/readers/`. Making Option A genuine (not just a
new class sitting next to the old ones) would have required modifying
`LocalFolderReader`'s core assumptions — out of scope for an infrastructure-only
phase that must not touch conversion-adjacent logic. `input/readers/`,
`input/discovery.py`, and `input/staging.py` had zero production call sites
before this phase and remain untouched; they're documented in
`providers/__init__.py` as superseded and candidates for removal in a later
cleanup. New code lives entirely in `providers/input.py` / `providers/output.py`.

**Output safety.** `LocalOutputProvider` defaults to
`./archive_migration_validation/generated_packages`, never `./Output` (the
folder holding the 3 hand-curated reference packages). Enforced by a dataclass
default plus a regression test (`test_output_settings_defaults_never_point_to_output_folder`).

**ZIP behavior preserved.** `LocalInputProvider.stage_article()` extracts the
zip internally (logic moved verbatim from the old inline batch-script code)
before handing off a `StagedArticle`, so the rest of the pipeline sees exactly
the same pre-extracted-folder shape it always has.

**Exception hierarchy reused.** Added `ProviderNotConfiguredError(ConfigurationError)`
in `exceptions/batch_errors.py` — no new hierarchy root.

**DI scope.** Only `scripts/archive_migration_batch.py` changed. It now calls
`ConfigLoader.load_runtime_config()` instead of hand-building `RuntimeConfig`,
resolves `input.local_path`/`output.local_path`/`dashboard.reports_path`
against `REPO_ROOT` via a new `_resolve_path()` helper, and constructs one
`InputProvider`/`OutputProvider` pair per batch run (construct-once, matching
`PackageBuilder`/`NamespaceManager`'s existing lifecycle).

## Files created

- `src/meca_engine/providers/__init__.py` — package docstring, documents Option B
- `src/meca_engine/providers/input.py` — `InputProvider`, `LocalInputProvider`, `S3InputProvider`, `create_input_provider`, `StagedArticle`
- `src/meca_engine/providers/output.py` — `OutputProvider`, `LocalOutputProvider`, `SftpOutputProvider`, `create_output_provider`
- `tests/unit/providers/__init__.py`, `test_input.py` (7 tests), `test_output.py` (6 tests)

## Files modified

- `src/meca_engine/config/schema.py` — new settings dataclasses, `RuntimeConfig`/`OutputSettings` extended
- `src/meca_engine/config/loader.py` — loads the 3 new sections
- `schemas/config-schema/runtime.schema.json` — schema for the 3 new sections + extended `output`
- `config/runtime.yaml`, `tests/fixtures/config/runtime.yaml` — new sections populated
- `src/meca_engine/exceptions/batch_errors.py`, `exceptions/__init__.py` — `ProviderNotConfiguredError`
- `scripts/archive_migration_batch.py` — config loading, provider wiring, removed hardcoded path constants
- 14 other `RuntimeConfig(...)` construction sites (golden tests, generator/packaging conftests, `production_validation_batch.py`, `verify_xslt_raw_article.py`) — added the 3 new required kwargs
- `tests/unit/config/test_loader.py` — assertions for the new fields

## Engine behavior

Unchanged. Full suite: 1052 passed. `PackageBuilder`, generators, ICAM,
business/recovery rules, reporting, intelligence, certification, transformation
layer, extraction logic were not modified.
