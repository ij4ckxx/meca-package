# MECA Package Generation Engine

An enterprise-grade engine that automatically produces NISO MECA packages
from journal article submissions, built strictly against a fully approved
documentation set — nothing in this codebase exists without a traceable
reference back to one of those documents.

**Status: Milestone 5B — Metadata → ICAM Transformation.** Milestones 1
(Foundation), 2 (Input & Staging Layer), 3 (XML Parsing Layer), 4
(Metadata Extraction Layer), and 5A (ICAM Domain Model) are complete and
approved. Milestone 5B implements the transformation layer that consumes
Milestone 4's extracted metadata and produces a fully populated, frozen
`ArticleModel` — 8 independent transformation services orchestrated by
`TransformationCoordinator`. All 3 real reference packages now run
through the complete pipeline (parse → extract → transform) with zero
structural-integrity issues. It does **not** generate a DOI, apply
business rules that modify values, generate MECA XML, run the
(business-rule) Validation Engine, or generate a package — see
["What This Milestone Deliberately Does Not Do"](#what-this-milestone-deliberately-does-not-do) below.

---

## Project Overview

Given a journal article's Kriyadocs-exported metadata XML plus its
submitted files (manuscript, figures, supplements, correspondence), this
engine produces a complete NISO MECA package: 5 generated XML files
(`raw`, `article`, `manifest`, `reviews`, `transfer`) plus the original
submitted files, assembled into one archive — at a target production
scale of 6,000–10,000+ articles per run.

Every behavior this engine will ever have is derived from ten approved
project documents, produced in this order:

1. **Reverse Engineering Report** — how 3 real, manually-built MECA
   packages were actually constructed from their source submissions.
2. **Functional Specification** — field-by-field mapping rules extracted
   from that analysis.
3. **Business Rule Book** — every rule atomized, classified
   (Confirmed / Strongly Inferred / Requires Business Confirmation), and
   prioritized.
4. **Architecture Decision Records (ADRs)** — every open question and
   design decision, each with a recommendation pending business sign-off.
5. **Test Specification** — the QA plan every rule and every ADR maps to.
6. **Product Backlog** — the Agile breakdown of the whole system.
7. **System Module Breakdown / Data Flow Document** — the High-Level
   Design (HLD).
8. **Low-Level Design (LLD)** — the software blueprint this codebase
   implements directly (package structure, canonical model, class
   design, configuration/logging/exception design, pipeline, testing and
   deployment architecture, coding standards).
9. **Risk Register** — tracked technical and business risks.
10. **Implementation Roadmap** — the phased plan this milestone is Phase 1 of.

If you are about to make an implementation decision that isn't obviously
answered by reading the code and its docstrings, the answer lives in one
of these ten documents (or, if it doesn't, that is itself a signal to
stop and ask — see `CONTRIBUTING` conventions below).

---

## Architecture Summary

The engine is a strictly layered system — see
`10_LLD_01_STRUCTURE_AND_PACKAGES.md` §2.3 for the authoritative diagram.
In one sentence per layer, bottom to top:

- **Foundation** (`model`, `config`, `exceptions`, `utils`) — depends on
  nothing else in the package; everything else depends on this.
- **Extraction** (`input`, `extraction`, `transform`) — turns a staged
  article into the Internal Canonical Article Model (ICAM).
- **Generation** (`generators.raw_xml`, `.article_xml`, `.manifest_xml`,
  `.reviews_xml`, `.transfer_xml`) — five independent generators, none of
  which may import another, none of which may parse source XML directly.
  Every generator reads only the ICAM.
- **Validation & Packaging** (`validation`, `packaging`, `output`) —
  validation never lives inside a generator; it runs afterward, against
  the generators' output documents only.
- **Reliability** (`checkpoint`, `retry`, `recovery`, `registry`) —
  restartability, retry classification, and DOI uniqueness.
- **Observability** (`logging_`, `reporting`, `monitoring`) — structured,
  correlation-id-aware logging feeding reporting and monitoring.
- **Orchestration** (`orchestrator`) — the only package permitted to
  import every other package.

**Milestone 1 implemented the Foundation layer fully** (`config`,
`exceptions`, `logging_`) plus the application bootstrap (`container.py`)
and the CLI (`cli/`). **Milestone 2 added the Input & Staging Layer in
full**: `input` (models, `readers.local_reader`/`readers.s3_reader`,
`discovery`, `staging`), `checkpoint` (the full `ArticleStage` state
machine, the `CheckpointStore` interface, and an in-memory backend), and
`orchestrator` (`RunController`, a deterministic `WorkerScheduler`, queue
preparation with resume support). **Milestone 3 added the XML Parsing
Layer**: `extraction` (`XmlLoader`, the generic `ParsedDocument`/
`ParsedElement` object model, `navigation` helpers, `file_relationships`
reference discovery, and `diagnostics`) — the generic, business-rule-free
layer metadata extraction is built on top of. **Milestone 4 adds the
Metadata Extraction Layer**: seven pure extractor functions
(`article_metadata_extractor`, `contributor_metadata_extractor`,
`journal_metadata_extractor`, `workflow_metadata_extractor`,
`custom_metadata_extractor`, `asset_metadata_extractor`,
`cross_reference_extractor`), each returning a typed model plus
diagnostics, and `metadata_extraction.extract_all_metadata` — the one
orchestrator that runs all seven with logging/performance timing — still
not the ICAM: it groups and types extracted source values without
normalizing, classifying, or interpreting them for publishing purposes.
**Milestone 5A added the ICAM itself** (`model`): `ArticleModel` and every
sub-object (`ArticleIdentity`, `JournalMeta`, `ArticleMeta`,
`Contributor`/`Affiliation`, `BodyFragment`, `CustomMetaStore` and its 5
nested collections, `RoundInfo`, `ResolvedFile`) — 21 frozen dataclasses
built via `ArticleModelBuilder`'s write-once-then-freeze lifecycle, plus
`model.validation` (structural integrity only, never a business rule) and
`model.serialization` (JSON, versioned; no XML serialization).
**Milestone 5B adds the transformation layer that actually populates it**:
`extraction.round_resolver`/`.custom_meta_classifier`/`.file_resolver`
(round/custom-meta/file resolution, needing raw structural or filesystem
access no Milestone 4 extractor provides) and `transform.*` (identity/
journal/contributor/workflow/body-fragment transformers plus
`TransformationCoordinator`, the single orchestrating entry point). All 3
real reference packages now produce a structurally sound `ArticleModel`
end to end (see `tests/golden/`). Every other package listed above still
exists only as an empty, documented, importable stub — the directory
structure matches the LLD exactly, but each stub's docstring states
plainly that it is not yet implemented and names the LLD section and
roadmap phase that will implement it.

A **Golden Baseline Repository** (`golden_baseline/` at the project root)
was started at Milestone 4 and extended at Milestone 5B: real Parsed
Object, Extracted Metadata, and (now) ICAM snapshots for all 3 sample
packages, with generated-XML stages left as documented placeholders
until the milestones that produce them.

---

## Build Instructions

**Requirements:** Python 3.12+ (see [Known Limitations](#known-limitations-of-this-environment) below).

```bash
# Clone and enter the repository
cd meca-engine

# Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"

# Install the pre-commit hooks (lint/format/type-check on every commit)
pre-commit install
```

## Local Setup

```bash
# Copy the environment template and adjust if needed (safe defaults for local dev)
cp .env.example .env

# Validate the configuration tree
make validate-config
# or directly:
python -m meca_engine.cli.main validate-config

# Discover and stage a batch of articles from a local folder
# (<root>/<ArticleID>/<Round>/<file> — no XML parsing, Milestone 2 only)
python -m meca_engine.cli.main run --source-dir /path/to/local/batch

# Run the full test suite
make test

# Run just the fast unit tests
make test-unit
```

No S3 or database access is required to exercise Milestone 1 or 2 locally
— the Configuration Framework reads local YAML files, the Checkpoint
Store defaults to an in-memory backend, and the `run` CLI command's
`--source-dir` path uses `LocalFolderReader` end-to-end. `S3Reader` exists
and is fully unit-tested against a fake client, but is not yet wired into
the CLI (`--source-prefix` remains a placeholder pending TQ-04).

## Development Workflow

1. **Read the relevant baseline document(s) first.** Every module's
   docstring names which document/section it implements — start there.
2. **If something is ambiguous or not covered by the docs, stop and ask**
   rather than inventing a new business rule (this is a standing project
   rule, not a suggestion — see `CONTRIBUTING`/Coding Standards below).
3. Write the code, following the package/class structure already defined
   in `10_LLD_01...`/`11_LLD_02...` for anything in scope for the current
   milestone.
4. Write unit tests alongside the code — every public class requires
   tests (see Testing Conventions below).
5. Run `make lint && make typecheck && make test` locally before pushing;
   `pre-commit` runs a subset of this automatically on commit.
6. Open a PR. CI (once implemented — see `.github/workflows/README.md`)
   will run the same checks, plus the golden-file regression suite once
   there is a generation pipeline to regress-test.

## Coding Standards

Full detail in `14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md` §13; summarized:

- **Python 3.12+**, fully statically typed (`mypy --strict`) — no `Any`
  at a public interface boundary.
- **Formatting/linting**: `ruff format` + `ruff check`, enforced via
  `pre-commit` and (once implemented) CI. Google-style docstrings,
  required on every public class/function.
- **Logging**: never call `logging.getLogger(...)` or `print()` directly
  outside `meca_engine.logging_` — always go through
  `meca_engine.logging_.get_logger`.
- **Exceptions**: never raise a bare stdlib exception — always a
  `meca_engine.exceptions` subclass, so retry/recovery classification
  works without inspecting message text.
- **Configuration**: never hard-code a journal-, publisher-, DOI-,
  license-, or media-type-specific value in code — it belongs in
  `config/`, validated by `schemas/config-schema/`.
- **Testing**: one test file per source module, mirroring the `src/`
  tree; every public class requires unit tests; see
  `14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md` §13.6 for the full
  convention set (fixture-first, one assertion concept per test, etc.).

## Contribution Guide

- Every implementation decision must be traceable back to one of the ten
  baseline documents. If you can't point to where a behavior is
  specified, don't guess — raise it for business/architecture
  clarification before writing the code.
- Never bypass the Internal Canonical Article Model (once implemented) —
  a generator that parses source XML directly, or that contains its own
  validation logic, is a defect regardless of whether it "works."
- Never replicate a defect found in the 3 real hand-built sample
  packages as if it were a business rule — see ADR-031 and the Business
  Rule Book's human-mistakes catalogue. When in doubt, the clean-mode
  behavior is correct; strict-replication mode exists only for the
  golden-file regression test suite.
- Follow the package structure, dependency-direction rules, and
  exception hierarchy exactly as defined in the LLD — this repository's
  directory structure is not a suggestion, it is the approved design.

---

## What This Milestone Deliberately Does Not Do

Per the current implementation task's explicit scope:

- **No DOI generation, business-rule transformation that modifies values,
  MECA generation, (business-rule) validation, or packaging.** Every
  `generators.*` subpackage, `validation` (the business-rule Validation
  Engine — distinct from `model.validation`'s structural-only checker),
  `packaging`, `output`, `registry`, `retry`, `recovery`, `reporting`, and
  `monitoring` remain empty, documented stubs. Milestone 5B's
  transformers copy, classify, or structurally resolve extracted values
  into the ICAM — they never generate a DOI (`ArticleIdentity.doi_article_id_value`
  is the verbatim source field only) and never apply a business rule that
  *changes* a value (e.g. `CustomMetaStore.form_answers` still includes
  every unclassified `custom-meta` entry, unfiltered — the deny-list
  pruning BR-066–071 describes is a generation-time, Milestone 7 concern).
- **No DTD validation.** `XmlLoader` detects and records a `<!DOCTYPE>`
  declaration's shape (name/public id/system id) but never fetches or
  validates against the referenced DTD grammar (ADR-025, a later
  milestone).
- **No real parallel execution.** `SequentialWorkerScheduler` is the only
  `WorkerScheduler` implementation; the interface is ready for a future
  parallel implementation (ADR-021) but none exists yet.
- **No durable Checkpoint Store backend.** `InMemoryCheckpointStore` is
  process-local and not persisted across restarts; a database-backed
  implementation is deferred (TQ-03).
- **No business-value configuration populated.** `config/journals/` and
  `config/publishers/` are intentionally empty — see their `README.md`
  files for exactly which ADRs must be confirmed before real journal/
  publisher configuration can be added. `config/runtime.yaml` and
  `config/feature-flags.yaml` **are** populated, since those are
  operational/behavioral settings, not business-value data.
- **No production S3 wiring in the CLI.** `S3Reader` is implemented and
  fully unit-tested against `FakeS3Client`, and `Boto3S3Client` exists
  behind an optional `aws` dependency group — but the CLI's `run` command
  only wires up `LocalFolderReader` so far; real AWS credentials/bucket
  wiring is deferred pending TQ-04.
- **No CI/CD, Docker, or infrastructure-as-code content.** The
  directory structure for all of these exists (per "create the complete
  project directory structure exactly as defined in the LLD"), each with
  a `README.md` explaining what's planned and which roadmap phase
  implements it.

---

## Known Limitations of This Environment

This codebase was developed and verified in a sandbox whose only
available Python interpreter is **3.9.6** — no 3.10, 3.11, 3.12, or 3.13
interpreter, and no tool capable of installing one (no `pyenv`, `uv`, or
`brew`), was available. The project's declared target
(`requires-python = ">=3.12"` in `pyproject.toml`, per
`14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md` §13.1) has **not** been
changed — this is a statement about the verification environment, not
about the target.

Concretely, this meant:

- The full test suite (488 tests as of Milestone 5B, plus 3 golden-regression
  tests run separately outside `testpaths` — see `tests/golden/`), `ruff check`/`ruff
  format --check`, and `mypy --strict` were all actually run and pass —
  but against Python 3.9.6, not 3.12, since `pip install -e .` refuses to
  install a package declaring `>=3.12` onto a 3.9 interpreter.
  Verification used a virtual environment with dependencies installed
  directly, relying on `pyproject.toml`'s `[tool.pytest.ini_options]
  pythonpath = ["src", "tests"]` (rather than a `PYTHONPATH` env var) so
  both `meca_engine` and the shared `tests/mocks/` test doubles resolve
  without a package install.
- `boto3`/`botocore` (the optional `aws` dependency group, used only by
  `Boto3S3Client`) are not installed in this environment either;
  `Boto3S3Client`'s thin adapter methods are marked `# pragma: no cover`
  and its module excluded from mypy's strict resolution via a targeted
  `ignore_missing_imports` override — every branch of `S3Reader`'s own
  logic (the translation into the approved exception hierarchy) is fully
  covered against `FakeS3Client` instead.
- `defusedxml` (Milestone 3's safe-XML-parsing dependency, a core, not
  optional, dependency) installed and verified normally in this
  environment, including its `types-defusedxml` type stubs — no
  workaround was needed for it, unlike `boto3`.
- All code deliberately avoids any syntax or stdlib feature introduced
  after Python 3.9, specifically so this verification would be
  meaningful rather than vacuous. Two `ruff` "pyupgrade" suggestions
  (`UP042`: use `enum.StrEnum`; `UP017`: use `datetime.UTC`) were
  encountered and are silenced in `pyproject.toml` with a comment
  explaining why — both suggested forms require Python 3.11+, and the
  forms actually used (`class X(str, Enum)`, `datetime.timezone.utc`)
  remain fully correct on Python 3.12, just marginally less idiomatic.
- **Before the first real CI run on a genuine Python 3.12 interpreter**:
  re-run the full suite there, and reconsider re-enabling `UP042`/`UP017`
  once that's confirmed to work — nothing else in this codebase is
  expected to behave differently between 3.9 and 3.12, but this has not
  been independently verified on 3.12 itself.
