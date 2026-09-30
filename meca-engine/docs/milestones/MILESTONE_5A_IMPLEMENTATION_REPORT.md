# Milestone 5A Implementation Report — Internal Canonical Article Model (ICAM)

Baseline: Milestones 1 (Foundation), 2 (Input & Staging Layer), 3 (XML
Parsing Layer), and 4 (Metadata Extraction Layer), all approved. Scope:
the ICAM domain model, its "mutable during construction, frozen after
build" lifecycle, structural validation, and JSON serialization — per
11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §3-4. **No metadata mapping, no
business rules, no XML generation, no transformation, no validation
engine, no package generation was implemented** — see §9 for what
remains deferred and why.

---

## 1. Directory Tree Changes

```
src/meca_engine/model/                    [was an empty stub — fully implemented]
├── __init__.py                           [MODIFIED] re-exports every public name
├── enums.py                              [NEW] ContribType, ReviewOutcomeStatus, ActorRole,
│                                          CorrespondenceChannel, CorrespondenceKind
├── article.py                            [NEW] ArticleModel + every sub-object + ArticleModelBuilder
├── collections.py                        [NEW] typed collection aliases (type-checking only)
├── serialization.py                      [NEW] to_dict/from_dict, SCHEMA_VERSION
├── validation.py                         [NEW] StructuralIssue, validate_structural_integrity
└── builders.py                           [NEW] ArticleBuilder/ContributorBuilder/JournalBuilder/
                                           WorkflowBuilder/AssetBuilder — Milestone 5B preview Protocols

tests/
├── unit/model/                           [NEW]
│   ├── __init__.py
│   ├── conftest.py                       build_sample_article_model() + fixtures
│   ├── test_article.py                   creation, immutability, equality, hashing, builder
│   ├── test_enums.py
│   ├── test_collections.py
│   ├── test_serialization.py             round-trip, schema-version rejection
│   ├── test_validation.py                structural-integrity checks + logging
│   ├── test_builders.py                  Protocol structural-conformance checks
│   └── test_golden_snapshots.py
└── fixtures/model/                       [NEW]
    └── snapshots/sample_article_model.snapshot.json  checked-in golden snapshot
```

**Stub packages left untouched**: `transform/`, every `generators.*` subpackage, `validation/` (business-rule Validation Engine — distinct from this milestone's `model.validation` structural checker), `packaging/`, `output/`, `registry/*`, `retry/`, `recovery/`, `reporting/`, `monitoring/`. `input/`, `checkpoint/`, `orchestrator/`, `extraction/` (Milestones 2-4) also untouched — `model` depends on none of them and none of them yet import `model`.

---

## 2. ICAM Class Hierarchy

```
ArticleModel (root, frozen)
├── identity: ArticleIdentity
├── journal_meta: JournalMeta
├── article_meta: ArticleMeta
│     ├── contributors: tuple[Contributor, ...]
│     ├── affiliations: tuple[Affiliation, ...]
│     ├── corresponding_emails: tuple[CorrespEmail, ...]
│     ├── counts: ArticleCounts
│     └── history_dates: HistoryDates
├── body_fragment: BodyFragment
├── custom_meta: CustomMetaStore
│     ├── form_answers: FormAnswerBag (entries: tuple[FormAnswerEntry, ...])
│     ├── file_entries: tuple[FileEntry, ...]
│     ├── reviewer_scorecards: tuple[ReviewerScorecard, ...]
│     ├── decision_drafts: tuple[DecisionDraft, ...]
│     ├── decline_reasons: tuple[DeclineReason, ...]
│     └── workflow_log: WorkflowLog (events: tuple[CorrespondenceEvent, ...])
├── rounds: tuple[RoundInfo, ...]
└── resolved_files: tuple[ResolvedFile, ...]
```

21 frozen dataclasses + 5 enums + 1 builder + 5 Protocol interfaces = every deliverable from the task's "ICAM Domain Model" list, mapped as follows (LLD-exact names on the left where they differ from the task's plain-English list):

| Task's domain area | ICAM type(s) |
|---|---|
| Article | `ArticleModel`, `ArticleMeta`, `ArticleCounts`, `HistoryDates` |
| Journal / Issue | `JournalMeta` (volume/issue-level fields live on `ArticleMeta` per the LLD — there is no separate `Issue` type; see §4 "Object Relationships" note) |
| Contributors / Affiliations | `Contributor`, `Affiliation`, `CorrespEmail` |
| Workflow | `WorkflowLog`, `CorrespondenceEvent` (inside `CustomMetaStore`, per LLD §3.4) |
| Review History | `ReviewerScorecard`, `DecisionDraft`, `DeclineReason` (inside `CustomMetaStore`) |
| Custom Metadata | `CustomMetaStore`, `FormAnswerBag`, `FormAnswerEntry` |
| Identifiers | `ArticleIdentity` |
| Publication Information | `ArticleMeta` (copyright/funding/keywords/counts/history_dates) |
| File Inventory | `ResolvedFile` / `ResolvedFileList` |
| Assets | Mapped to `ResolvedFileList` — see §3's "Object Relationships" note on why there is no separate `Asset` ICAM type |
| Cross References | Deliberately **not** a separate ICAM type — see §3's note |

---

## 3. Object Relationships

- **Ownership** (composition — child has no independent identity/lifecycle outside its parent): `ArticleModel` owns every field listed in §2 directly; none is shared between `ArticleModel` instances.
- **Aggregation with model-internal keys, not source ids** (11_LLD_02... §3.3): `Contributor.affiliation_keys: tuple[int, ...]` references `Affiliation.model_key` — a stable integer assigned at build time, never a source XML `id`. This is a deliberate design carried over from the LLD verbatim (TC-060/070: article.xml strips all ids, so author↔affiliation linkage cannot depend on them). `model.validation.validate_structural_integrity` enforces this reference's integrity (a dangling `affiliation_keys` entry is a structural error).
- **Collections, ordered**: `contributors`, `affiliations`, `rounds`, `resolved_files`, `corresponding_emails` (index 0 = primary, BR-130), and every `CustomMetaStore` sub-collection are all plain `tuple`s — ordered, immutable, never a `set`/`dict` (dict-shaped LLD fields were adapted to ordered-pair tuples; see `article.py`'s module docstring).
- **Optional relationships**: every field that the LLD does not mark as always-present is `Optional` (`str | None`, `date | None`) — e.g. `JournalMeta.issn_ppub`/`issn_epub` (a journal may lack a print or electronic ISSN), `Contributor.email`/`orcid`, `ReviewerScorecard.overall_recommendation`. Every *collection* field defaults to an empty tuple rather than `None` — "no data" is represented as an empty collection, never a null collection, so calling code never needs a `is not None` guard before iterating.
- **References, not ownership**: `RoundInfo.label`/`FileEntry.round_label`/`ResolvedFile.round_label`/`ReviewerScorecard.round_label`/etc. all reference the same opaque round-label string space (ADR-014) — there is no shared `Round` object each of these points to; the label is compared by string equality only, exactly matching the LLD's "generic string" design (no `Round` object graph is built).
- **Two deliberate non-additions, flagged rather than guessed at** (a documented design note, not a redesign — see the Architecture Compliance Report §2 for the full reasoning):
  - **No separate `Issue` type.** The LLD's `ArticleMeta`/`JournalMeta` carry every volume/issue/page-level field the 3 reference samples exhibit; introducing a distinct `Issue` object would group fields the LLD's own object graph does not group, without a cited requirement forcing that grouping.
  - **No separate `Asset`/`CrossReference` ICAM type.** `BodyFragment.raw_xml_fragment` is deliberately opaque (LLD §3.2: "deliberately NOT decomposed further... no generator needs structured access to its internals") and `article.xml` never includes the body at all (BR-072) — so no generator needs a structured figure/table/cross-reference list out of the ICAM. Milestone 4's `AssetMetadata`/`CrossReferenceMap` remain valid, useful outputs of the *extraction* layer; they are not promoted into the ICAM because the LLD's actual generator designs (§4.7) never read them from there. `ResolvedFileList` is the one file-shaped list every generator that touches files (`manifest_xml`, `packaging`) actually consumes, per LLD §3.6.

---

## 4. Serialization Strategy

- **Format**: JSON only (no XML serialization, per explicit scope). Implemented as a pair of pure functions, `model.serialization.to_dict(article) -> dict` / `from_dict(data) -> ArticleModel`, not a method on `ArticleModel` itself — keeps the domain model free of any serialization-format concern.
- **Version field**: every `to_dict()` output carries a top-level `schema_version` field (`SCHEMA_VERSION = "1.0.0"`, semantic-versioned, independent of the package's own `0.1.0` version).
- **Backward compatibility strategy**: `from_dict()` rejects any `schema_version` whose major version doesn't match the one this module supports (today, major version `"1"`) — a deliberate hard rejection for a breaking schema change, not a silent best-effort parse. Every field is read *by name* (`data["article"]["identity"]["article_id"]`, never by position), so a hypothetical old `1.x` document with a since-added optional field simply gets that field's Python-level default back with zero migration code required; a genuine breaking change (field removed/retyped) is exactly the seam `_SUPPORTED_MAJOR_VERSION` exists to guard, and would be handled by a version-specific migration function added at that point — no such function exists yet because no second schema version exists yet.
- **Round-trip fidelity, verified**: `to_dict(article) == to_dict(from_dict(to_dict(article)))`-equivalent behavior is asserted directly (`from_dict(to_dict(article)) == article`) across every populated and empty-collection case (`test_serialization.py`), including passing the dict through actual `json.dumps`/`json.loads` text (not just the in-memory dict), confirming every value really is a JSON primitive.

---

## 5. Freeze Lifecycle

```
ArticleModelBuilder(article_id, logger=...)      # logs "ArticleModelBuilder created"
  │
  ├─ set_identity(identity)          ─┐
  ├─ set_journal_meta(journal_meta)   │  each: _assert_not_already_set(field)
  ├─ set_article_meta(article_meta)   │         → raise ModelBuildError if already set
  ├─ set_body_fragment(body_fragment) │         (write-once, in any order the caller chooses —
  ├─ set_custom_meta(store)           │          the LLD does not mandate a call order)
  ├─ set_rounds(index)                │
  ├─ set_resolved_files(files)       ─┘
  │
  └─ freeze() -> ArticleModel
        ├─ missing = [any of the 7 fields still None]
        ├─ if missing: raise ModelBuildError (lists exactly the missing field names)
        └─ else: construct the frozen ArticleModel, log "ArticleModel frozen"
                 (contributor_count / round_count / resolved_file_count in the log context)
```

Matches 11_LLD_02... §3.7's table exactly: "write-once during build, frozen thereafter... a frozen object shared across concurrent readers has no possible race condition." `None` is used as the internal "not yet set" sentinel (not a separate `_UNSET` object) — legitimate specifically because all 7 fields are non-optional on the frozen `ArticleModel`, so there is no ambiguity between "unset" and "deliberately set to null." Verified empirically (not just asserted): attempting `article.identity = ...` on a frozen instance, and `article.article_meta.contributors[0].surname = ...` on a *nested* frozen instance, both raise `dataclasses.FrozenInstanceError`; `hash(article)` succeeds and is stable across two independently-built, field-equal instances; an `ArticleModel` instance is usable as a `dict` key.

---

## 6. Test Summary

| Test file | Test functions (incl. parametrized) | Covers |
|---|---|---|
| `test_article.py` | 20 | object creation, defaults, immutability (root + nested), collections-are-tuples, equality, hashing, dict-key usability, builder happy path, write-once enforcement (all 7 setters, parametrized), incomplete-freeze error reporting, builder logging, model-internal affiliation keys, `FormAnswerBag.get()` |
| `test_enums.py` | 5 | every enum's exact value set |
| `test_collections.py` | 1 | module imports cleanly (type-checking-only module) |
| `test_serialization.py` | 8 | schema-version field, JSON-safety, round-trip equality (in-memory and through actual JSON text), empty-collection round-trip, missing/unsupported/non-string schema-version rejection |
| `test_validation.py` | 9 | sound-model no-issues case, duplicate affiliation key, dangling affiliation reference, zero/multiple `is_latest`, duplicate round sequence, empty-round-index no-issues, validation logging |
| `test_builders.py` | 5 | Protocol structural conformance (both positive and negative), no accidental inheritance edge, Protocols not directly instantiable |
| `test_golden_snapshots.py` | 2 | full ICAM JSON structural snapshot match; snapshot-file sanity guard |
| **Total** | **54** | |

Full suite (all 5 milestones combined): **401 passing tests**, verified in the same virtual environment used for Milestones 1-4, with `ruff check`, `ruff format --check`, and `mypy --strict` all clean on both `src/` (168 source files) and `tests/`.

---

## 7. Coverage Report

```
Name                                                  Stmts   Miss Branch BrPart  Cover
------------------------------------------------------------------------------------------
src/meca_engine/model/__init__.py                         7      0      0      0   100%
src/meca_engine/model/article.py                        198      0     12      0   100%
src/meca_engine/model/builders.py                        24      0      0      0   100%
src/meca_engine/model/collections.py                      2      0      0      0   100%
src/meca_engine/model/enums.py                           32      0      0      0   100%
src/meca_engine/model/serialization.py                   82      0      2      0   100%
src/meca_engine/model/validation.py                      51      0     22      0   100%
------------------------------------------------------------------------------------------
Milestone 5A module subtotal                            396      0     36      0   100%
------------------------------------------------------------------------------------------
TOTAL (whole src/, incl. Milestones 1-4 + untouched stubs)  2157     18    258      1    99%
```

**Target ("at least 95% coverage") is met: every Milestone 5A module is at 100% coverage.** `collections.py` required one dedicated import-only test (`test_collections.py`) since nothing else in the codebase imports it at runtime (a type-checking-only module, by design — see its own docstring); the remaining 18 uncovered lines project-wide are entirely in still-unimplemented future-milestone stub packages, unchanged from Milestone 4.

---

## 8. Architecture Compliance Report

See the companion document: **`MILESTONE_5A_ARCHITECTURE_COMPLIANCE_REPORT.md`** in this same directory.

**Versioned golden baseline (strategic recommendation, actioned this milestone)**: this milestone's golden snapshot (`tests/fixtures/model/snapshots/sample_article_model.snapshot.json`) follows the same checked-in, deliberately-regenerated-only pattern as Milestones 3 and 4. Tagging the repository at each approved milestone (e.g. `v0.4.0-metadata-complete` retroactively for Milestone 4, `v0.5.0-icam-complete` for this one) and archiving golden snapshots per tag is a repository/release-process action outside this codebase's own files — recommended for adoption at the next actual git-repository/tagging setup point (this workspace is not yet a git repository — see Known Limitations in `README.md`), not something this report can action directly.

---

## 9. Deferred Work for Milestone 5B

Per the current task's explicit exclusion list, all deferred:

- **Metadata → ICAM builder logic** — `KriyadocsParser`, `CustomMetaClassifier`, `RoundResolver`, `FileResolver`, `TransformationCoordinator` (11_LLD_02... §4.2-4.6) do not exist yet. This milestone's `ArticleModelBuilder` is real and load-bearing; nothing yet calls its 7 setters with real extracted data. `model.builders`'s 5 Protocols are non-binding previews only — Milestone 5B is free to implement them, ignore them, or use a different shape entirely.
- **Business rules** — no article-type mapping, license-template mapping, DOI generation/formula, custom-meta deny-list pruning, or any other Business-Rule-Book-driven transformation. Every ICAM value in this milestone's tests is hand-constructed, never derived from a real extracted document.
- **XML generation, Validation Engine, Package Builder** — untouched stub packages, per scope, unaffected by this milestone.
- **Round resolution from real `vocab-identifier` values** (BR-010) — `RoundInfo`/`RoundIndex` are fully modeled and structurally validated (exactly-one-`is_latest`, unique `sequence_number`), but nothing yet populates them from a real parsed document.
- **File resolution against the staged physical folder** (11_LLD_02... §4.5) — `ResolvedFile`/`ResolvedFileList` are fully modeled, but nothing yet computes a real checksum/size/media-type from a staged file.

**Explicit dependency check before Milestone 5B begins**: `ArticleModelBuilder` (this milestone's output) is exactly the object `TransformationCoordinator.build_model()` is designed to construct and freeze. Nothing left open in this milestone blocks that work. One open question worth flagging for Milestone 5B planning (documented, not blocking): whether the model-internal `Affiliation.model_key` assignment happens inside a Milestone 5B `ContributorBuilder`-shaped component or inline within `KriyadocsParser`/`CustomMetaClassifier` — the LLD does not specify which class performs this assignment, only that it happens "at build time."
