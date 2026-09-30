# Milestone 3 Architecture Compliance Report — XML Parsing Layer

Companion to `MILESTONE_3_IMPLEMENTATION_REPORT.md`. Checks Milestone 3's
implementation against the Business Rule Book, the ADRs, the HLD, and the
LLD, and verifies no architectural boundary was crossed. Every claim below
is either a direct code citation, an empirically-verified parser-behavior
transcript, or a `grep`-based structural check — not an assertion.

---

## 1. Business Rule Book Compliance

| Rule | Requirement | Milestone 3 Implementation | Status |
|---|---|---|---|
| BR-001 | Exactly one root-level XML file must exist; must be well-formed XML | Milestone 2 enforced the existence/count half (directory-listing level). **Milestone 3 enforces the well-formedness half**: `XmlLoader._parse_tree` raises `SourceXmlMalformedError` (tagged `rule_id="BR-001"`) for any non-well-formed content, verified by `test_raises_for_malformed_xml`, `test_raises_for_empty_file`, `test_raises_for_truncated_xml`. Together, Milestones 2+3 now fully implement BR-001. | **Fully implemented** (jointly with Milestone 2) |
| BR-005 | Kriyadocs XML embeds non-JATS platform markers; parser must tolerate/ignore unknown elements rather than fail | `XmlLoader`/`ParsedElement` impose no schema whatsoever — every element/attribute, known or unknown, JATS or not, is represented identically and generically. Nothing in this layer can reject a document for containing an unrecognized tag. | **Fully implemented** (by construction — genericity is the mechanism) |
| BR-007 | Custom-meta is the audit-trail-of-record; must be parseable | Not directly applicable to Milestone 3 — recognizing *which* elements are custom-meta is Milestone 4's `custom_meta_classifier` job. This milestone guarantees the *generic* parse succeeds and every element (custom-meta included) is faithfully represented in the `ParsedElement` tree, which is the precondition BR-007's later classification step depends on. | **Precondition satisfied; classification correctly deferred** |
| BR-010 | `vocab-identifier` snapshot number is the round-ordering key | Not applicable to Milestone 3 — extracting/interpreting this attribute's value is Milestone 4's `round_resolver` job. This milestone's `navigation.get_attribute`/`find_all` make the raw attribute value retrievable generically, but this module never reads or interprets `vocab-identifier` itself. | **Correctly deferred, not violated** |
| BR-011/BR-014 | Custom-meta file-manifest entries are the authoritative file list; directory/structural scanning is not trusted for business purposes | `file_relationships.discover_file_references` finds structural `href`/`src` references — explicitly documented (module docstring) as **not** the BR-011/BR-014 business-rule file list, and never presented or used as such anywhere in this milestone. No test or code path in Milestone 3 conflates the two. | **Correctly scoped, not violated** |

**No Business Rule Book rule was violated.** Every rule with any overlap with Milestone 3's scope is either fully implemented (jointly with Milestone 2, for BR-001) or explicitly, documentedly out of scope pending Milestone 4's business-rule-driven classification layer.

---

## 2. ADR Compliance

| ADR | Decision | Milestone 3 Implementation | Status |
|---|---|---|---|
| ADR-025 | DTD validation is a separate, later concern (vendored DTDs, Validation Engine) — real grammar validation not required yet | `DoctypeDeclaration` captures presence/shape only (`name`, `public_id`, `system_id`, `has_internal_subset`); `XmlLoader` never fetches, parses, or validates against the referenced DTD file. Matches the current task's explicit "DTD awareness (no validation yet)" instruction exactly. | **Fully compliant** |
| (Security posture, no single ADR number — informed by Risk Register RISK-012 Unicode-correctness concern and general dual-use security practice) | Safe handling of untrusted, externally-authored XML | `defusedxml` used for every parse pass (tree-building and namespace-collection alike); empirically verified to reject an internal entity-expansion attempt (`EntitiesForbidden`) while still accepting a realistic external-system-id DOCTYPE with no internal entities (see §5 below) — the correct behavior for both directions. | **Compliant** |
| ADR-031 (defect-replication policy) | Never replicate a hand-built-sample defect as if it were a business rule | Not directly applicable — no XML *generation* occurs in Milestone 3, so there is no output to compare against the 3 real sample packages. | N/A |
| (General architecture principle, 10_LLD_01 §2.1: `extraction.kriyadocs_parser` is "the ONLY module allowed to parse the source XML") | Parsing responsibility is centralized | Milestone 3 establishes the generic parsing primitive (`XmlLoader`) that a future `kriyadocs_parser` will be built on top of, per the Implementation Report §9's explicit note — no other module in the codebase (verified, §5) parses XML content anywhere else. | **Compliant, and sets up Milestone 4 correctly** |

**No ADR was violated.** Every ADR whose scope touches Milestone 3 is fully implemented per its documented decision.

---

## 3. HLD Compliance (System Module Breakdown + Data Flow Document)

- **Metadata Extractor module** (`05_SYSTEM_MODULE_BREAKDOWN.md` §4): "Parses the staged Kriyadocs XML into a single, complete, typed internal article model... This is the **one and only** place the Kriyadocs XML is parsed." Milestone 3 does not yet build that "complete, typed internal article model" (the ICAM) — it builds the layer *underneath* it. The HLD's "one and only place parsed" principle is honored structurally: `XmlLoader` is the sole XML-parsing entry point in the entire codebase today (verified, §5), and it is designed to be the thing the eventual Metadata Extractor calls into, not a competing or duplicate parsing path.
- **Data Flow Document, Stage 2** (`06_DATA_FLOW_DOCUMENT.md`, "Metadata Loading"): "The Metadata Extractor parses the staged root XML into the internal article model." Milestone 3 provides the parsing primitive this stage will use; the stage's full behavior (producing the internal article model) remains Milestone 4's to complete. The Data Flow Document's stage-2 failure paths — "Malformed/unparseable XML → permanent failure, specific parse-error location logged" — are already exactly what `XmlLoader` produces (`SourceXmlMalformedError` with line/column, per BR-001).

**No HLD module's stated responsibility was contradicted, duplicated elsewhere, or silently dropped** — Milestone 3 is additive groundwork underneath the Metadata Extractor module's eventual full implementation, not a conflicting or parallel implementation of it.

---

## 4. LLD Compliance

- **Package structure** (`10_LLD_01_STRUCTURE_AND_PACKAGES.md` §2.1): `extraction/` populated at exactly the path the LLD specifies. The LLD's own sketch of this package (`kriyadocs_parser.py`, `custom_meta_classifier.py`, `file_resolver.py`, `round_resolver.py`) is more granular/business-specific than what Milestone 3 needed to build — consistent with the established, Milestone-1/2 precedent (`container.py`, `input/discovery.py`+`staging.py`) of implementing files *within* an LLD-designated package at a finer or different granularity than the LLD's own illustrative sketch, always justified in-place (every new module's docstring states which future LLD-named module will be built on top of it).
- **ICAM boundary** (`11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md` §3): completely untouched. `parsed_model.py`'s module docstring explicitly states this model carries "no publishing semantics whatsoever" and is not the ICAM — verified by inspection: no class in `extraction/` references `ArticleModel`, `ArticleModelBuilder`, or any ICAM concept.
- **Exception Framework** (`12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md` §7): zero new exception classes introduced. `SourceXmlMalformedError` and `SourceUnavailableError` (both already approved, Milestone 1/2) are reused, with only their docstrings broadened to name `xml_loader` as an additional raiser — verified: `grep -c "^class.*Error" src/meca_engine/exceptions/article_errors.py src/meca_engine/exceptions/batch_errors.py` is unchanged from Milestone 2's count.
- **Logging** (`12_LLD_03...` §6): every class logs exclusively through `meca_engine.logging_.StructuredLogger`, injected via constructor (matching the established pattern from every prior milestone) — verified by direct `grep` (§5): zero occurrences of `logging.getLogger`/`print` in `extraction/`.
- **Coding Standards** (`14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md` §13): full type hints throughout (verified: `mypy --strict` clean on both `src/` and `tests/`), Google-style docstrings on every public class/function, `ruff`/`mypy --strict` clean, one test file per source module mirroring `src/` exactly (`test_parsed_model.py`, `test_navigation.py`, `test_diagnostics.py`, `test_file_relationships.py`, `test_xml_loader.py`).

**No LLD-specified class responsibility, dependency rule, or module boundary was altered.**

---

## 5. Verified Structural & Behavioral Checks

Run directly against the final Milestone 3 codebase:

```
$ grep -rnE "^(from|import) meca_engine\.(model|transform|generators|validation|packaging|output|registry|retry|recovery|reporting|monitoring|orchestrator|input|checkpoint)\b" \
    src/meca_engine/extraction --include="*.py"
NONE FOUND — extraction/ imports nothing from any other package (foundation-adjacent: depends only on
meca_engine.exceptions and meca_engine.logging_, both foundation-layer per 10_LLD_01 §2.3).

$ grep -rnE "^(from|import) meca_engine\.extraction" src/meca_engine --include="*.py" | grep -v "^src/meca_engine/extraction/"
NONE FOUND — no other package imports extraction/ yet (correct: extraction/ is not wired into
container.py this milestone, since there is nothing yet for it to feed into — that wiring is
Milestone 4's job once the Metadata Extractor exists to consume its output).

$ grep -rn "print(\|logging.getLogger" src/meca_engine/extraction
NONE FOUND — every log emission goes through meca_engine.logging_, per Coding Standards §13.5.
```

**Empirical safe-parsing verification** (the specific behavior ADR-025/security-posture compliance rests on):

```
>>> defusedxml.ElementTree.parse(realistic_jats_doctype_with_external_system_id)
PARSED OK: article                          # a legitimate external DOCTYPE reference does not,
                                              # by itself, trigger any safety rejection

>>> defusedxml.ElementTree.parse(doctype_with_internal_entity_declaration_and_reference)
EntitiesForbidden(name='xxe', ...)           # an actual entity-expansion attempt IS rejected,
                                              # correctly re-raised by XmlLoader as SourceXmlMalformedError

>>> defusedxml.ElementTree.parse(malformed_mismatched_tag)
ParseError('mismatched tag: line 1, column 21'), .position == (1, 21)
                                              # genuine syntax errors surface with a real,
                                              # usable source location, correctly formatted by
                                              # XmlLoader._format_error_location into the raised
                                              # SourceXmlMalformedError's message
```

These three transcripts are the exact empirical basis for Design Decision "Safe parsing" in the Implementation Report — not an assumption about `defusedxml`'s behavior, a directly observed one.

---

## 6. Test Evidence Cross-Reference

| Compliance claim | Verifying test(s) |
|---|---|
| BR-001 well-formedness half now enforced | `test_raises_for_malformed_xml`, `test_raises_for_empty_file`, `test_raises_for_truncated_xml`, `test_malformed_error_has_br001_rule_id` |
| BR-005 (tolerate unknown constructs) | Every `test_xml_loader.py` test implicitly — no test fixture uses a JATS-recognized tag name, and all parse identically to any other generic element |
| Safe parsing rejects entity attacks | `test_rejects_internal_entity_declaration` |
| Safe parsing accepts realistic external DOCTYPEs | `test_detects_public_doctype` (uses the real JATS Publishing DTD's public identifier verbatim) |
| No publishing-semantic categorization in file-reference discovery | `test_does_not_assign_any_category_to_a_reference` (explicit negative test — asserts the `FileReference` type has no `category`/`kind` attribute at all) |
| Generic (not JATS-specific) dangling-reference mechanism | `test_custom_reference_attribute_names`, `test_default_reference_attribute_name_is_rid_only` (default is a configurable parameter, not a hard-coded assumption) |
| Encoding detection correctness (the bug found during this milestone) | `test_bom_declared_encoding_conflict_produces_warning` (originally failing, now passing after the `_bom_length` fix) |
| Golden snapshot protects the whole parsed-model shape | `test_valid_sample_matches_golden_snapshot` |

---

## 7. Conclusion

Milestone 3 implements the XML Parsing Layer entirely within the
architectural boundaries established by the Business Rule Book, the ADRs,
the HLD, and the LLD. It introduces zero new exception categories,
touches no ICAM concept, imports from no not-yet-implemented package, and
is not yet imported by anything else (correctly — it has no consumer
until Milestone 4 exists). Every rule/decision/module whose scope
overlaps this milestone is either fully implemented or explicitly,
documentedly deferred with a stated reason, and the one genuine defect
found during development (the BOM/declared-encoding detection bug) was
caught by the milestone's own required test coverage before being
reported here, not after.

**No architectural boundary was violated. Milestone 3 is ready for review.**
