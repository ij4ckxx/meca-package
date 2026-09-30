# XML Validation — Milestone 2

Structural (DTD conformance + well-formedness) validation for
`article.xml`, `reviews.xml`, `manifest.xml`, and `transfer.xml`. Runs
strictly after a package is already built; never stops or alters
package generation.

## What was reused, not rebuilt

- `generators/validation_hooks.py` — the reserved Milestone-6A
  extension point (`ValidationIssue`, `ValidationIssueSeverity`,
  `DtdValidationHook` ABC) already existed, empty. Extended it
  additively with `line`/`xpath` fields on `ValidationIssue`; no
  existing field changed.
- `schemas/dtd/{jats-archiving-1.2,jats-publishing-1.3,meca-1.0}/` — the
  reserved-but-empty directories from ADR-025/RISK-023. Left empty, per
  explicit instruction not to fetch anything from the internet.
- `packaging/conversion_report.py` — `ConversionReport` gained one
  additive field, `validation_report: PackageValidationReport | None`,
  same pattern as every other additive field this program has used.
- `reporting/package_embed.py` / `reporting/certification_report.py` —
  their patterns (reopen the finished zip; render a self-contained HTML
  page) were followed exactly for the new validation writer/reporter,
  not modified themselves.

## New code

- `validation/models.py` — `ValidationResult` (PASS/WARNING/ERROR),
  `FileValidationReport` (filename, dtd_name, dtd_available, result,
  error_count, warning_count, issues), `PackageValidationReport`
  (article_id, files, plus `overall_result`/`total_errors`/
  `total_warnings`).
- `validation/xml_validator.py` — `LxmlDtdValidationHook` implements the
  existing `DtdValidationHook` ABC using `lxml.etree.DTD`; maps each
  generated filename's suffix to its expected DTD
  (`_article.xml`→jats-archiving-1.2, the other 3→meca-1.0).
  `validate_generated_file()` is the public entry point: always checks
  well-formedness; checks DTD conformance only if the DTD file is
  actually present on disk at the expected vendored path.
- `validation/package_validator.py` — `validate_staged_package()` reopens
  the already-built zip (read-only), reads back the 4 relevant XML
  files' bytes, and validates each.
- `reporting/validation_report.py` — renders one package's
  `PackageValidationReport` as a self-contained HTML page (same style
  as the Certification Report).
- `service/worker.py` — after a package is built, calls
  `validate_staged_package()`, attaches the result to the
  `ConversionReport` via `dataclasses.replace()`, embeds it in
  `conversion-report.json` (same mechanism as every other report field),
  and writes `MECA_<ArticleID>_Validation_Report.html` alongside the
  Certification Report.

## DTD availability — documented, not fabricated

No DTD files are vendored in this repository. Every file's
`dtd_available` is `false` and its report says so explicitly — this is
never conflated with a passing DTD-conformance result. Well-formedness
is still always checked and always meaningful. The moment real,
version-pinned DTDs are vendored under `schemas/dtd/<name>/<expected
filename>` (see `_DTD_BY_SUFFIX` in `xml_validator.py` for the exact
expected filenames), DTD-conformance validation activates automatically
with no code change.

## Report fields

Each `FileValidationReport` carries: filename, DTD name, DTD
availability, PASS/WARNING/ERROR result, error count, warning count,
and a list of issues (severity, message, line, xpath). Rolled up per
package into `PackageValidationReport` (overall result = worst of its
files; total error/warning counts). Both are `to_dict()`-serializable
and are exactly what's embedded in `conversion-report.json` and
rendered into the standalone HTML report.

## Verification

- 7/7 unit tests (`tests/unit/validation/test_xml_validator.py`):
  well-formed documents pass with no DTD vendored, malformed documents
  are reported as an ERROR with the correct line number, each of the 4
  filenames maps to its correct expected DTD name, unknown filenames
  still get well-formedness checked.
- `ruff check` / `ruff format` / `mypy --strict` clean.
- Full regression suite: 1124 passed (3 pre-existing, unrelated golden
  failures — see `05_Final_Implementation_Summary.md`).
- Full batch run against `Input/` (37/37 articles): every package now
  contains an embedded `validation_report` in `conversion-report.json`
  and a standalone `MECA_<ArticleID>_Validation_Report.html`. Spot-checked
  bcj-2025-3130: all 4 files well-formed, all `PASS`, `dtd_available:
  false` for all (expected, since no DTDs are vendored).
