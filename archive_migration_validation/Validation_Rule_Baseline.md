# Validation Rule Baseline

The validation model, now that real DTDs are vendored — what each
field means, how PASS/WARNING/ERROR is decided, and exactly what
changed from the prior (well-formedness-only) baseline.

## The problem this fixes

Before this milestone, `dtd_available` was `False` for every file (no
DTDs were vendored), so `FileValidationReport.result` reflected
well-formedness only — but nothing in the report or dashboard made
that limitation visible at a glance. A package could show "PASS" while
being nowhere near DTD-valid, because DTD conformance was never
actually checked. Real DTDs are now vendored (see
`DTD_Compliance_Summary.md`) and DTD conformance is genuinely checked,
but well-formedness and DTD conformance remain **two separate
questions** with two separate answers — a document can be
well-formed and still violate its DTD (this is, in fact, the normal
case for article.xml and reviews.xml in the current corpus).

## Model

`FileValidationReport` (`meca_engine.validation.models`) now reports
both, never merged into one hidden decision:

| Field | Meaning |
|---|---|
| `well_formed_result` | PASS/ERROR — pure XML parse check. Always computed, independent of any DTD. |
| `dtd_available` | Whether a real, vendored DTD file exists for this file type. |
| `dtd_result` | PASS/WARNING/ERROR when `dtd_available` and the document is well-formed; **`None`** ("not checked") otherwise — never defaults to PASS when nothing was actually checked. |
| `result` | The overall, backward-compatible field: the worse of `well_formed_result` and `dtd_result` (treating `None` as not contributing). Existing consumers reading only `result` keep working unchanged. |
| `issues[].check` | `"well-formed"` or `"dtd"` — which check produced this specific finding, so a report can filter/group by check. |

`PackageValidationReport` gained `overall_dtd_result` (the worst
`dtd_result` across a package's checked files, or `None` if none were
checked) alongside the existing `overall_result`.

## Decision order (never a false PASS)

1. Parse the document. If it fails, `well_formed_result = ERROR`,
   `dtd_result = None` (an unparseable document can't be meaningfully
   checked against a DTD) — validation stops there for this file.
2. If well-formed and no DTD is vendored for this file type,
   `dtd_result = None` — reported as "not checked", not "pass".
3. If well-formed and a DTD is vendored, run DTD validation;
   `dtd_result` reflects exactly what lxml/libxml2 reports.

## Classification vocabulary (used across the deliverables)

Every DTD finding in this milestone was classified into exactly one of:

- **Engine defect** — the generator has all the needed information but
  emits something invalid (wrong order, duplicate id). Fixed when
  confirmed and safely fixable without inventing data.
- **Source-data issue** — the defect is already present, verbatim, in
  the original source XML; the engine faithfully reproduces it.
- **Missing/needed Business Rule** — a genuine gap with no current
  rule to fix it correctly (e.g. renaming an attribute changes
  declared semantics; splitting a name would fabricate data) —
  recommended, not silently implemented.
- **Validation error / warning** — the DTD/well-formedness outcome
  itself, as reported per file.

See `DTD_Compliance_Summary.md` for every finding classified this way.

## What did *not* change

- `ConversionReport.validation_report` — still the same field, same
  attachment point (`service/worker.py`, via `dataclasses.replace`).
  It now simply carries richer per-file data.
- The standalone HTML report and dashboard endpoints — same routes,
  same files; only their content grew the two new fields (see
  `Dashboard_Validation_Alignment.md`).
- Package generation, `PackageOutcomeStatus`, Recovery Rules,
  Certification — untouched. Validation still runs strictly after a
  package is built and never affects whether that package is
  generated.

## Tests

`tests/unit/validation/test_xml_validator.py` — rewritten against the
real vendored DTDs (previously tested only against the "no DTD
vendored" path, since none existed yet):
- well-formed document with no matching file-type → `dtd_result is None`
- malformed document → `well_formed_result = ERROR`, `dtd_result = None`,
  DTD check correctly skipped
- all 4 official NISO MECA example files validate PASS against their
  real DTDs (both `well_formed_result` and `dtd_result`)
- a deliberately DTD-invalid-but-well-formed manifest.xml (missing a
  required child) → `well_formed_result = PASS`, `dtd_result = ERROR`,
  confirming the two are reported independently, not conflated
