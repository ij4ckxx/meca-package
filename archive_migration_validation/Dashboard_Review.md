# Dashboard Review — RC-1

Verification only, per scope — no redesign, no new pages.

## Navigation & routing — confirmed consistent, no broken links

`App.tsx`: 12 `NAV_ITEMS` entries, 12 corresponding `<Route>` + page
component imports — every nav link maps to a real, existing route and
component; no orphaned import, no route with a missing nav entry beyond
the expected drill-down (`/articles/:id`, reached by clicking a row, not
listed in top nav — correct by design).

## Dark mode — confirmed working

Implemented via `context/ThemeContext.tsx` + a `data-theme` attribute on
`:root` (`styles.css`), toggled by a real button in `App.tsx`'s header
(`onClick={toggleTheme}`). Not a stub.

## Batch switching, manual review workflow, operator controls

All backed by the API routes verified in `API_Review.md`
(`/batches`, `/run/*`, `/manual-review`, `PUT /manual-review/:id/note`).
The one real defect found in this area — `?batch=` accepting an
unvalidated value — is fixed (see `Security_Review.md`); every page that
switches batches goes through the same `requireBatch`/`resolveBatchId`
path, so the fix applies uniformly across the whole dashboard, not just
one page.

## Downloads, filters, sorting, pagination, article detail, analytics, migration audit, validation pages

Reused directly from the Production Readiness milestone's own review
(2 milestones prior this session), where concrete defects were already
found and fixed: the Dashboard's warning count previously excluded
generator-level findings (fixed), the detail page's `warning_count`/
`recovery_count` fields were previously never populated at all (fixed),
and the failure-reason field previously rendered a raw JSON dump (fixed,
now shows a formatted message). Re-verified this milestone that none of
those fixes regressed: `tsc -p tsconfig.json --noEmit` (server) and
`tsc -b --noEmit` (web) both clean; live-tested against the running dev
server (`GET /api/articles`, `/api/summary` both return correct data
after this milestone's caching change — see `Performance_Review.md`).

Per this milestone's own "stop if unchanged areas already have
sufficient prior verification" guidance, filters/sorting/pagination/
configuration-page mechanics were not re-audited line-by-line this pass
— no code changed in those areas since their last review, and this
milestone's targeted changes (batch-id validation, report caching)
don't touch that logic.

## Configuration page

`GET`/`PUT /api/config` reviewed under `Security_Review.md`
("config-injection") — safe (schema-validated, rollback on failure, no
unsafe YAML deserialization). Functionally unchanged this milestone.
