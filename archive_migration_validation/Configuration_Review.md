# Configuration Review — RC-1

## Secrets — confirmed clean

No AWS/SFTP credentials, passwords, API keys, or private keys anywhere
in `config/`, `schemas/config-schema/`, or `.env.example` (grepped for
common credential patterns — zero matches). No `.env` file is committed
(only `.env.example`, which documents variable *names* with safe,
non-secret dev defaults and explicit comments that real secrets come
from a secrets manager in every deployed environment). This was already
correctly set up; no changes needed.

## Confirmed defect: `runtime.yaml` mixed live and dead configuration with no indication of which

Traced every one of `runtime.yaml`'s 11 top-level sections against what
the *live* production pipeline (`scripts/archive_migration_batch.py` →
`service_factory` → `Worker`/`ProcessingService`) actually reads:

| Section | Status |
|---|---|
| `retry` | **Live** |
| `output` (`provider`/`local_path`) | **Live** |
| `input` | **Live** |
| `dashboard` | **Live** |
| `output` (`operational_bucket`/`archival_bucket`) | Not yet wired (forward-looking AWS placeholder) |
| `concurrency` | Not yet wired (`ProcessingService` runs strictly sequentially) |
| `validation` | Not yet wired (DTD validation runs unconditionally regardless of this value) |
| `staging` | Not yet wired (only the superseded `container.py`/`input/staging.py` orchestrator reads it) |
| `checkpoint` | Not yet wired (`service_factory` hardcodes `InMemoryCheckpointStore()`) |
| `doi_registry` | Not yet wired (`service_factory` hardcodes `InMemoryDoiRegistry()`) |
| `packaging` | Not yet wired (`service_factory` hardcodes matching literal values) |
| `logging` | Not yet wired (the live pipeline never calls `configure_root_logging`) |

Before this review, none of this was documented — an operator editing
`checkpoint.backend: postgres` before a production deployment could
reasonably believe checkpoints persist across restarts, when in fact
they're in-memory only (lost every restart, by design — see
`checkpoint/store.py`'s own docstring; this is a deliberately deferred
future phase, not a defect). **Fixed**: every section in `runtime.yaml`
is now annotated `[LIVE]` or `[NOT YET WIRED]` with a one-line reason,
so this is never mistaken for active configuration. No behavior changed
— this is a documentation-only fix, verified by re-running
`tests/unit/config/` (55 passed) and the full suite (1163 passed, same
3 pre-existing unrelated failures) after the edit.

## JSON Schema documentation completeness — noted, not fixed

~100+ properties across the 13 `schemas/config-schema/*.json` files have
no `description` field. Not fixed this milestone: the primary,
authoritative human-facing documentation for these values already lives
in each corresponding `config/*.yaml` file's own header/inline comments
(spot-checked — present and substantive), so this is a secondary
documentation layer gap, not a case of undocumented configuration.
Adding accurate descriptions for 100+ fields (many requiring research
per field to avoid filler text) is disproportionate to this milestone's
lightweight-verification scope; recommended as a future, dedicated pass.

## Placeholders remain placeholders — confirmed

`output.operational_bucket: meca-output-operational` /
`archival_bucket: meca-output-archival`, `checkpoint.backend: postgres`,
`doi_registry.backend: postgres` are all clearly-named, non-functional
placeholder values (now explicitly marked `[NOT YET WIRED]`) — none
resemble or could be mistaken for a real credential or connection
string.
