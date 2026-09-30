# API Review — RC-1

Reviewed all 33 routes in `dashboard/server/src/routes.ts`. No redesign
performed; naming/response-format/status-code consistency verified,
one real defect found and fixed (see Security_Review.md — the
`?batch=` path-traversal fix also directly improves this endpoint's
correctness, since it now behaves consistently for every route rather
than only some).

## Naming — consistent

Kebab-case throughout (`/manual-review`, `/migration-audit-report`,
`/stop-after-current`), consistent `:id` param naming for article
identifiers, consistent `download`/`view` sub-resource pattern for every
report type (`/articles/:id/download/certification` +
`/articles/:id/view/certification`, same pair for validation and
migration-audit). No inconsistent pluralization or verb usage found.

## Response format — consistent

Every success response is a bare JSON value (object or array, no
envelope wrapper) via `res.json(...)`. Every error response uses the
exact same shape, `{ "error": "<message>" }` — grepped for any
`res.status(...).json(...)` call not matching this shape: zero found.

## HTTP status codes — consistent, correctly chosen

- `400` (4 uses) — malformed/invalid request body or state (e.g.
  restarting a batch with no failed articles).
- `404` (13 uses) — unknown article/batch/report/file.
- `409` (7 uses) — a run-control action that conflicts with the current
  run state (e.g. starting a migration that's already running).
- Everything else defaults to Express's own `200`, which is correct for
  every plain-data `GET`.

No endpoint found returning `200` on failure or a generic `500` where a
more specific code applied.

## Duplicate / unreachable endpoints — none found

All 33 routes are distinct paths+methods, each with its own real
handler; none shadow or duplicate another. No dead route registrations
found (every route is reachable via the router mount in `index.ts`).

## Endpoint inventory (for reference)

`GET /batches`, `/summary`, `/journals`, `/articles`, `/articles/:id`,
`/articles/:id/download/{zip,certification,validation,migration-audit-report,migration-audit-json,report}`,
`/articles/:id/view/{certification,validation,migration-audit-report}`,
`/articles/:id/download/xml/:kind`, `/manual-review`, `/reports/:filename`,
`/analytics/{recovery-rules,warnings,business-rules,missing-files,confidence,validation}`,
`/run/{status,logs}`, `/config` — plus `PUT /manual-review/:id/note`,
`PUT /config`, and `POST /run/{start,pause,resume,stop-after-current,cancel,restart-failed,restart-manual-review}`.
