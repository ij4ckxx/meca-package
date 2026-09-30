# Migration Service Verification

- `ruff check` / `ruff format --check` — clean on every file this phase touched — ✅
- `mypy --strict src/` — 152 files, 0 issues — ✅
- Targeted new tests: `tests/unit/service/test_router.py` (9), 2 new
  `category_root` tests in `tests/unit/providers/test_output.py`, plus
  updated `tests/unit/service/test_worker.py` (now asserts failed-article
  routing) — all passing — ✅
- Full suite: 1108 passed, same 3 pre-existing, unrelated failures as
  Phase 2 (confirmed unrelated — different subsystem, untouched files) — ✅
- One real end-to-end batch, the current `Input/` folder (37 real
  packages) — ✅:
  - Packages processed: 37/37 generated, 0 engine/fatal failures —
    identical outcome shape to before this phase (unchanged conversion
    behavior) — ✅
  - Decision routing worked: 33 → `uploaded/` (3 certified_with_warnings +
    30 certified_with_recovery), 4 → `manual_review/` (4
    partial_certification), 0 → `failed/` (0 failures this run) — ✅
  - Successful packages in `uploaded/`: verified zip + Certification
    Report present — ✅
  - Manual-review packages stored correctly: verified each of the 4
    contains the MECA zip, Certification Report HTML, and
    `conversion-report.json` — ✅
  - Failed-package retention: not exercised live (0 failures in this
    corpus) — covered instead by `test_router.py::test_route_failed_article_...`
    and `test_worker.py::test_reraises_batch_runner_failure_for_classification`,
    both asserting real files are written to `failed/<id>/` — ✅
  - Existing reports generated: `Migration_Summary.html`,
    `migration_dashboard.json`, all intelligence reports — unchanged,
    still written to `dashboard.reports_path` — ✅
  - Existing certification unchanged: same per-article Certification
    Report writer, same content, only its final location changed — ✅
  - `Output/` (3 protected reference packages) — untouched (MD5-verified
    before/after) — ✅
  - Old flat per-article staging directories are gone after routing
    (moved, not copied) — no orphaned intermediate directories left
    behind — ✅

## Not run, per scope

Exhaustive regression suites beyond the full unit/golden suite above —
this phase did not change any engine logic (extraction, transformation,
generation, business/recovery rules, `PackageBuilder`), only where
finished artifacts are routed.
