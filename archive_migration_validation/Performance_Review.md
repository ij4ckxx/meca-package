# Performance Review — RC-1

Lightweight — obvious bottlenecks only, no algorithm rewrites.

## Fixed: repeated JSON parsing on every Dashboard API call

**`dashboard/server/src/dataStore.ts`, `loadConversionReports()`.**
Called independently by 8 different route handlers (articles, summary,
journals, analytics, manual-review, ...) — every one of them re-read and
re-`JSON.parse`'d the *entire* `conversion_reports.json` from disk, on
every single request, with zero caching. For a large batch (up to
100,000 articles), this file can be tens-to-hundreds of MB; re-parsing
it on every dashboard page load is a real, "obvious" bottleneck matching
this review's own example ("repeated report loading").

**Fixed**: added a small in-memory cache keyed by batch id, invalidated
by the file's own mtime (checked via a cheap `statSync`, not a content
hash) — a live-running batch's periodic incremental snapshot writes
(the mid-run refresh added in the Production Readiness milestone) are
still picked up correctly; the cache never serves data staler than
what's actually on disk. Verified: `tsc --noEmit` clean; live-tested
against the running dev server — `/api/articles` and `/api/summary`
both return correct, unchanged data after the change.

## Investigated, not fixed: repeated directory scans

`scanArticleLocations()` (also in `dataStore.ts`) is called by the same
8 route handlers, each doing a fresh `readdirSync()` over all 3 output
categories and then every article subdirectory within them — for
100,000 articles, that's 100,000+ individual directory-listing syscalls
per API request. This is a real inefficiency, but a correct cache
requires invalidating on new article directories appearing mid-run
(distinct staleness behavior from the JSON cache above, since the
Dashboard is explicitly meant to reflect newly-completed articles as a
batch runs). Given this milestone's "do not rewrite algorithms, only
investigate obvious bottlenecks" scope and the added complexity of
getting multi-level cache invalidation exactly right, this is
**documented, not fixed** — recommended as a follow-up with its own
targeted testing.

## Reviewed, confirmed no issue

- **DTD file re-parsing** and **config-checksum recomputation** — both
  already fixed in the Production Readiness milestone (cached per
  batch/worker lifetime); re-confirmed still in place, unaffected by
  this milestone's changes.
- **Unnecessary file copies**: no new copy-then-copy-again pattern found
  in the code paths touched this milestone (`providers/input.py`'s
  extraction, the Dashboard's report/zip serving) — files are read once
  and either streamed (`res.sendFile`) or read directly into memory for
  a single response, no intermediate duplication.
