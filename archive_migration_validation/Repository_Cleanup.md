# Repository Cleanup — RC-1

## Archived (moved, not deleted — reversible)

6 pre-existing, large (~700MB total) milestone/verification-output
directories moved from repo root into a new `_archive/` directory.
Confirmed via repo-wide grep that none are read by any live code at
runtime — only cited in a handful of code comments as historical
evidence (those comments were updated to point at the new location, see
below):

- `Output/` (102M) — **initially archived, then restored to its original
  root location** after the full test suite caught a real dependency:
  5 golden tests (`tests/golden/test_{raw,manifest,transfer,reviews}_xml_golden.py`)
  read real reference packages directly from `./Output/*.zip`. This is
  the one correction made mid-cleanup this milestone — confirmed by
  re-running the full suite (1163 passed, same 3 pre-existing unrelated
  failures) after restoring it.
- `certification_output/` (7.3M), `full_input_certification/` (83M),
  `golden_baseline/` (38M), `independent_certification/` (83M),
  `production_validation/` (375M) — confirmed archived safely; full test
  suite and full batch run both clean with these moved.

## Deleted (true orphans, zero references, confirmed safe)

- `build_meca_v1.1.py` (repo root) — an abandoned prototype (tkinter
  file-picker UI, hand-rolled XML building, no relation to the
  `meca_engine` package). Zero references anywhere in the repo.
- `rawtocleanup.xslt` (repo root) — a byte-for-byte duplicate of the
  live, packaged copy at
  `meca-engine/src/meca_engine/generators/raw_xml/rawtocleanup.xslt`
  (confirmed via `diff`, exit 0). Only the packaged copy is ever loaded
  by any code.
- `meca-engine/config/runtime.yaml.bak` — a stray, byte-identical backup
  of `runtime.yaml`, zero references anywhere.
- `meca-engine/src/meca_engine.egg-info/` — a stale, gitignored
  (`*.egg-info/` already in `.gitignore`) setuptools build artifact;
  regenerates automatically on the next editable install.
- 5 of my own accumulated verification-run batch directories under
  `archive_migration_validation/batches/` from the last 3 milestones
  this session (`new-input-batch-1`, `production-stabilization-verify`,
  `production-readiness-final`, `quality-improvement-investigation`,
  `quality-improvement-final`) plus this milestone's own
  `rc1-final-verification` — kept only the 2 real, timestamp-named
  batches that represent actual user dashboard runs.

## Documentation updated as a direct consequence

8 code/config comments across `meca-engine/config/*.yaml` and
`meca-engine/src/meca_engine/{config/schema.py, generators/article_xml/generator.py,
generators/raw_xml/xslt_transform.py}` cited `Output/*.zip` as evidence
for a design decision — all confirmed still accurate (since `Output/`
was restored to its original location) and one (`runtime.yaml`'s own
comment) updated to note it's also a live golden-test dependency, not
just a "never overwrite" reference set.

## Dead-code / lint sweep

`ruff check --select F401,F811,F841,ERA001` (unused imports, redefined
names, unused variables, commented-out code) across the entire `src/`
tree: **zero findings** — the codebase has been kept clean incrementally
all session, not accumulated debt. A full, unrestricted `ruff check`
across `src/` + `tests/` (broader than any single milestone's own
scope, run as part of this cleanup pass) found one genuine, pre-existing
issue: unsorted imports in `tests/golden/test_article_xml_golden.py`
(predating this session's changes) — fixed via `ruff check --fix`
(mechanical reordering, zero behavior change), re-verified clean
(`ruff check`/`ruff format --check`: 0 errors, 330 files correctly
formatted; full suite: 1163 passed, same 3 pre-existing unrelated
failures). Zero `TODO`/`FIXME`/`XXX` markers found anywhere in engine
source. Dashboard TypeScript: zero `TODO` markers, one legitimate
`console.log` (a startup banner, not leftover debug code).

## Reviewed, left unchanged (not obsolete — genuine repository content)

- 57 numbered planning/design/milestone documents at repo root
  (`01_BUSINESS_RULE_BOOK.md` through `56_...md`, plus
  `FUNCTIONAL_SPECIFICATION.md`/`REVERSE_ENGINEERING_REPORT.md`) — these
  are architecture/design documentation, not disposable outputs; in
  scope for the separate Documentation Freeze review, not deletion.
- `meca-engine/cli/main.py`'s `seed-doi-registry`/`rebuild-golden-baseline`
  commands (and their 1:1 wrapper scripts in `meca-engine/scripts/`) —
  both are registered, packaged CLI commands (`meca-engine = "meca_engine.cli.main:cli"`
  in `pyproject.toml`) whose own docstrings say "placeholder... deferred
  until X exists," where X (the DOI registry, the full generation
  pipeline) has existed and been in active use for many milestones now.
  This is genuine, confirmed stale documentation inside otherwise-live,
  publicly-registered commands — flagged here rather than changed,
  since removing/rewriting a public CLI command's behavior is a larger
  judgment call than this cleanup pass should make unilaterally. Low
  risk either way: both commands are no-ops today regardless of the
  staleness of their message.
