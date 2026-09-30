# Milestone 5A Architecture Compliance Report — Internal Canonical Article Model (ICAM)

Companion to `MILESTONE_5A_IMPLEMENTATION_REPORT.md`. Checks Milestone 5A's
implementation against the Business Rule Book, the ADRs, the HLD, and the
LLD, and verifies no architectural boundary was crossed. Every claim below
is either a direct code citation, a `grep`-based structural check, or a
result empirically observed by running the code — not an assertion.

---

## 1. Business Rule Book Compliance

| Rule | Requirement | Milestone 5A Implementation | Status |
|---|---|---|---|
| BR-003 | The exact input-folder string is the article's identity | `ArticleIdentity.article_id: str` — a plain, unmodified string field; nothing in this milestone derives, normalizes, or reformats it. | **Modeled; population deferred to 5B** |
| BR-010 | `vocab-identifier` snapshot number is the round-ordering key | `RoundInfo.sequence_number: int` models the resolved value; `model.validation` enforces exactly-one `is_latest` and unique `sequence_number` once populated. Extracting the value from the source remains Milestone 5B's `RoundResolver` job — no code in this milestone reads or interprets `vocab-identifier`. | **Modeled; extraction correctly deferred** |
| BR-045/062 | Copyright statement wording must never be normalized | `ArticleMeta.copyright_statement: str \| None` — a plain, unmodified field; no `.strip()`/`.lower()`/rewording logic exists anywhere in `model/`. | **Fully compliant** |
| BR-060 | `funding-group` content is copied with ids stripped, verbatim | `ArticleMeta.funding: FundingList` (`tuple[str, ...]`) — verbatim funding statement strings, consistent with `keywords`'s same verbatim-string treatment. | **Modeled; population deferred to 5B** |
| BR-075 | ORCID is a value-only field, distinct from any source element id | `Contributor.orcid: str \| None` holds only the ORCID value — there is no `Contributor.element_id`-shaped field anywhere in the ICAM (ids are deliberately never carried into the ICAM at all, consistent with TC-060/070). | **Fully compliant** |
| BR-130 | Primary corresponding email resolution — index 0 is primary | `ArticleMeta.corresponding_emails: tuple[CorrespEmail, ...]` — documented as ordered, index 0 = primary. This milestone only holds an already-ordered tuple; the resolution logic that decides *which* email goes first is explicitly Milestone 5B's job (not implemented here — no ordering/priority logic exists in `model/`). | **Modeled; resolution correctly deferred** |

**No Business Rule Book rule was violated.** Every rule with any overlap with Milestone 5A's scope is either fully satisfied by the model's shape (verbatim-field rules) or a satisfied precondition for Milestone 5B's population/resolution logic.

---

## 2. ADR Compliance

| ADR | Decision | Milestone 5A Implementation | Status |
|---|---|---|---|
| (11_LLD_02... §3.1, the ICAM's central design principle) | The ICAM is the only object any generator is permitted to read | `ArticleModel` is a complete, frozen, self-contained object graph with zero remaining reference to source XML structure, file paths, or an S3 client anywhere in its fields. No generator package exists yet to enforce the import-direction rule against, but the model itself carries nothing a generator would need to bypass it for. | **Compliant; structurally ready for enforcement once generators exist** |
| ADR-014 | Round labels are generic, opaque strings — never a closed enum | `RoundInfo.label: str`, and every other `round_label: str` field across `FileEntry`/`ResolvedFile`/`ReviewerScorecard`/`DecisionDraft`/`DeclineReason`/`CorrespondenceEvent` — no enum, no fixed vocabulary, exactly as ADR-014 requires. | **Fully compliant** |
| ADR-005 (extended-history scope) | `AUTHOR_SUGGESTED_REVIEWER`/`EDITOR_REASSIGNMENT`/`PRODUCTION_QUERY` event kinds are feature-flag-scoped | `CorrespondenceKind` models all 5 values the LLD names (including these 3); the feature-flag gating itself is `CustomMetaClassifier`'s job (11_LLD_02... §4.3, "Configuration Requirements: Reads feature-flags.yaml") — not yet implemented, correctly, since nothing populates a `WorkflowLog` yet in this milestone. | **Modeled; gating correctly deferred** |
| (Diagnostics-not-exceptions principle, established Milestones 3-4) | Non-fatal structural observations are reported, not raised | `model.validation.validate_structural_integrity` returns a tuple of `StructuralIssue`s, never raises — consistent with `extraction.diagnostics`'s established pattern, extended one layer up to the ICAM. | **Fully compliant** |

**No ADR was violated.**

---

## 3. HLD Compliance (System Module Breakdown + Data Flow Document)

- **ICAM module** (`05_SYSTEM_MODULE_BREAKDOWN.md` §4 / `11_LLD_02...` §3): "the one and only... internal article model" every downstream stage reads. This milestone builds exactly that object graph and its builder — the *population* of that graph from real data (the HLD's "Metadata Loading"/"Transformation" stages) remains Milestone 5B's job, per the HLD's own stage boundary (Metadata Extractor parses → Transformation builds the ICAM → Generation reads it).
- **Data Flow Document, Stage 3-4** (Pre-Validation → Transformation): this milestone's `model.validation` module implements exactly the kind of structural check the Data Flow Document's "Pre-Validation" stage name suggests (as distinct from the full business-rule Validation Engine, a later stage) — scoped here strictly to graph integrity (duplicate keys, dangling references, round consistency), never a publishing-semantic check.

**No HLD module's stated responsibility was contradicted, duplicated elsewhere, or silently dropped.**

---

## 4. LLD Compliance

- **Package structure** (`10_LLD_01_STRUCTURE_AND_PACKAGES.md` §2.1): `model/article.py`, `model/enums.py`, `model/collections.py` populated at exactly the 3 file names and responsibilities the LLD's own package sketch names. `model/serialization.py`, `model/validation.py`, and `model/builders.py` are additions beyond that 3-file sketch — each justified in its own module docstring (serialization/validation are this milestone's explicit task requirements, absent from the LLD's own text; `builders.py` is an explicitly-flagged, non-binding supplement — see §2 above and its own module docstring's opening paragraph).
- **ICAM object graph** (`11_LLD_02...` §3.2-3.6): every field the LLD names is present under its exact name, with two documented, hashability-driven representation adaptations (`dict[str, str]` → `tuple[tuple[str, str], ...]`; `FormAnswerBag` in place of a raw `dict`) — see the Implementation Report's Directory Tree Changes / this milestone's `article.py` module docstring for the full rationale. No LLD-named field was dropped, renamed beyond this, or given different semantics.
- **ArticleModelBuilder** (`11_LLD_02...` §4.1): implements exactly the LLD's public interface — `set_identity`, `set_journal_meta`, `set_article_meta`, `set_body_fragment`, `set_custom_meta`, `set_rounds`, `set_resolved_files`, `freeze() -> ArticleModel` — verified by direct inspection: no additional public setter exists, and `freeze()`'s signature and `ModelBuildError`-raising behavior match §4.1's "Error Handling" cell exactly (raises on premature `freeze()` and on any field set twice).
- **Foundation-layer dependency rule** (`10_LLD_01...` §2.1/§2.3): `model/` imports only `meca_engine.exceptions` (for `ModelBuildError`) and, where a caller supplies one, `meca_engine.logging_.StructuredLogger` — both foundation-layer, consistent with every prior milestone's own foundation-layer dependencies (Milestone 1's `config`/`logging_` already established that cross-foundation-package imports, unlike imports into a business-logic layer, are normal). Verified: `grep` finds zero imports of `extraction`, `input`, `transform`, `generators`, `validation`, `packaging`, `output`, `registry`, `retry`, `recovery`, `reporting`, `monitoring`, `orchestrator`, `checkpoint`, `config`, or `cli` anywhere in `model/`.
- **No consumer yet** (correct per the LLD's own stage ordering): `grep` finds zero imports of `meca_engine.model` from any other package — expected, since Milestone 5B's `TransformationCoordinator` (the first real consumer) does not exist yet.
- **Exception Framework** (`12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md` §7): zero new exception classes introduced. `ModelBuildError` (already present since Milestone 1's upfront exception framework) is reused unmodified — verified: `grep -c "^class.*Error"` on both exception modules is unchanged from Milestone 4 (22 article-level + 7 batch-level = 29).
- **Logging** (`12_LLD_03...` §6): `ArticleModelBuilder` and `validate_structural_integrity` both accept an optional injected `StructuredLogger`, logging creation/freeze/validation-start/validation-complete events — matching every prior milestone's constructor-injection pattern. Verified: `grep -rn "print(\|logging.getLogger" src/meca_engine/model` returns no matches.
- **Coding Standards** (`14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md` §13): full type hints throughout (verified: `mypy --strict` clean on 168 source files), Google-style docstrings on every public class/function, `ruff check`/`ruff format --check` clean, one test file per source module mirroring `src/` exactly.

**No LLD-specified class responsibility, dependency rule, or module boundary was altered.**

---

## 5. Verified Structural & Behavioral Checks

Run directly against the final Milestone 5A codebase:

```
$ grep -rnE "^(from|import) meca_engine\.(extraction|input|transform|generators|validation|packaging|output|registry|retry|recovery|reporting|monitoring|orchestrator|checkpoint|config|cli)\b" \
    src/meca_engine/model --include="*.py"
NONE FOUND — model/ imports nothing from any business-logic-layer package.

$ grep -rlE "^(from|import) meca_engine\.model\b" src/meca_engine --include="*.py" | grep -v "^src/meca_engine/model/"
NONE FOUND — no other package imports model/ yet (correct: no Milestone 5B consumer exists).

$ grep -rn "print(\|logging.getLogger" src/meca_engine/model
NONE FOUND — every log emission goes through meca_engine.logging_.

$ grep -c "^class.*Error" src/meca_engine/exceptions/article_errors.py src/meca_engine/exceptions/batch_errors.py
article_errors.py: 22   batch_errors.py: 7   (both unchanged from Milestone 4 — zero new exceptions)
```

**Empirical immutability/equality/hashing verification** (run directly, not just asserted in prose):

```
>>> hash(article_model)
-1524511343099794276                          # succeeds — every field, including every nested
                                                # sub-object, is hashable (the documented dict->tuple
                                                # adaptations exist specifically to make this true)

>>> article_model.identity = article_model.identity
dataclasses.FrozenInstanceError: cannot assign to field 'identity'
                                                # root-level mutation rejected

>>> article_model.article_meta.contributors[0].surname = "x"
dataclasses.FrozenInstanceError: cannot assign to field 'surname'
                                                # NESTED sub-object mutation also rejected —
                                                # immutability is not merely root-level
```

These three transcripts are the exact empirical basis for this milestone's "Immutability" and "equality support"/"deterministic hashing" claims — not an assumption about `@dataclass(frozen=True)`'s behavior, a directly observed one, including the nested-object case the task's own wording ("frozen after build") implies but does not spell out.

---

## 6. Test Evidence Cross-Reference

| Compliance claim | Verifying test(s) |
|---|---|
| Frozen instances reject root-level mutation | `test_article_model_is_frozen` |
| Frozen instances reject *nested* sub-object mutation | `test_nested_sub_object_is_frozen` |
| Every collection is a tuple, never a list | `test_collections_are_tuples_not_lists` |
| Field-equal instances compare equal and hash equal | `test_equal_article_models_compare_equal`, `test_equal_article_models_hash_equal` |
| `ArticleModel` is usable as a `dict` key (deterministic hashing, practically demonstrated) | `test_article_model_is_usable_as_a_dict_key` |
| Write-once semantics enforced for all 7 builder fields | `test_every_setter_enforces_write_once` (parametrized ×7) |
| `freeze()` reports exactly the missing field(s), never a false positive | `test_freeze_with_one_missing_field_reports_only_that_field` |
| `Affiliation.model_key` is model-internal, not a source id | `test_affiliation_keys_are_model_internal_not_source_ids` |
| Structural (not business-rule) validation: dangling references, duplicates, graph consistency | `test_dangling_affiliation_reference_is_reported`, `test_duplicate_affiliation_key_is_reported`, `test_zero_is_latest_rounds_is_reported`, `test_multiple_is_latest_rounds_is_reported`, `test_duplicate_round_sequence_number_is_reported` |
| JSON round-trip fidelity, including through actual JSON text | `test_round_trip_preserves_equality`, `test_round_trip_through_actual_json_text` |
| Backward-compatibility seam rejects an unsupported schema version | `test_from_dict_rejects_unsupported_major_version`, `test_from_dict_rejects_missing_schema_version` |
| Builder Protocols are structurally satisfied without an inheritance edge | `test_article_model_builder_satisfies_article_builder_protocol`, `test_article_model_builder_is_not_declared_to_inherit_from_article_builder` |
| Full ICAM JSON structure protected end-to-end | `test_sample_article_model_matches_golden_snapshot` |

---

## 7. Conclusion

Milestone 5A implements the Internal Canonical Article Model entirely
within the architectural boundaries established by the Business Rule
Book, the ADRs, the HLD, and the LLD. It introduces zero new exception
categories, imports from no business-logic-layer package, and is not yet
imported by anything else (correctly — it has no consumer until Milestone
5B exists). Every LLD-specified field, type, and the builder's exact
public interface are implemented verbatim, with two narrow, documented,
hashability-driven representation adaptations that preserve every field
the LLD names. Two domain areas from the task's plain-English list
("Assets", "Cross References") were deliberately not promoted into new
ICAM types, with the reasoning traced directly to the LLD's own opaque
`BodyFragment` design and BR-072 — a documented mapping decision, not a
silent gap. Immutability, equality, and hashing were verified empirically
against both the root object and a nested sub-object, not merely
asserted.

**No architectural boundary was violated. Milestone 5A is ready for review.**
