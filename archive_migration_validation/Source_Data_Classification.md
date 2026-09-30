# Source Data Classification — Production Stabilization Milestone

## The problem

`providers/input.py`'s `LocalInputProvider.stage_article()` let 3 raw,
unwrapped exceptions propagate: a missing archive (`FileNotFoundError`
from `zipfile.ZipFile(zip_path)`), a corrupt/unreadable archive
(`zipfile.BadZipFile`), and "no source XML found after extraction" (a
second, unrelated `FileNotFoundError` raised by `_find_source_xml`).

None of these are `MecaEngineError` subclasses, so `worker.process()`'s
outer exception handling always caught them in its generic
`except Exception` branch — which unconditionally reports
`PackageStatus.ENGINE_FAILURE`, regardless of cause. An empty/corrupt
publisher zip was therefore indistinguishable, in every report and on
the Dashboard, from a genuine engine bug.

## The fix

No new `PackageStatus` value, no new taxonomy, no dashboard schema
change. The engine's own exception hierarchy already had exactly the
right, purpose-built classes for this — they were simply never wired
into `providers/input.py`:

| Situation | Now raised as | Existing docstring already describes this exact case |
|---|---|---|
| Archive file does not exist | `SourceUnavailableError` | "a local path does not exist... a definitive not-found... condition" |
| Archive is not a readable ZIP (corrupt/empty-of-structure) | `SourceUnavailableError` | same class, same reasoning — the source cannot be accessed at all |
| Archive extracts fine but contains no source XML at all | `InvalidArticlePackageError` | "an article's folder structure does not match the expected shape... zero... root-level XML-named file... present" |
| Declared manuscript file missing (unchanged) | `FileReferenceMissingError` | already correct before this milestone |

Both classes are `ArticleLevelError` → `MecaEngineError` subtypes, so
`worker.process()`'s **first** except clause now catches them (not the
generic catch-all), and `_classify_failure()`'s existing logic — which
already distinguishes a fixed list of engine-defect exception types from
everything else — correctly returns `PackageStatus.FATAL_FAILURE` (the
engine's existing "source data made safe generation impossible"
status) without any change to that function itself.

## Result

| Case | Before | After |
|---|---|---|
| `ebc-2025-3025` (empty zip) | `engine_failure` | `fatal_failure` |
| `ebc-2025-3021_C` (missing manuscript) | `fatal_failure` (already correct) | `fatal_failure` (unchanged) |
| A hypothetical corrupt-zip case | would have been `engine_failure` | `fatal_failure` |

## Dashboard distinction

The Dashboard already renders `PackageStatus.ENGINE_FAILURE` and
`PackageStatus.FATAL_FAILURE` as two separate values everywhere it reads
`ConversionReport.status` (Article list/detail pages, Operator
Checklist's existing "Needs Investigation" vs. "Failed" buckets — see
`Operator_Guide.md`). No Dashboard code change was needed: the defect
was purely in which status got assigned upstream, not in how the two
statuses are displayed once assigned correctly.

## Batch continuation

Unchanged and already correct: `worker.process()` catches every
exception per-article and returns a report rather than propagating, so
one article's staging failure has never stopped the batch from
continuing to the next article — confirmed again in this milestone's
full-corpus run (97/97 articles attempted, 2 fatal failures, 0 engine
failures, batch completed normally).

## Not reclassified (already correct before this milestone)

`FileReferenceMissingError` (missing declared manuscript, BR-011) was
already an `ArticleLevelError` and already correctly resulted in
`FATAL_FAILURE` — no change needed.
