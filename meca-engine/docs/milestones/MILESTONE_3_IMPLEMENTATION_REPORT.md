# Milestone 3 Implementation Report — XML Parsing Layer

Baseline: Milestones 1 (Foundation) and 2 (Input & Staging Layer), both
approved. Scope: safe, generic XML loading — encoding/BOM detection,
DOCTYPE-presence detection (no validation), a namespace-aware Parsed
Object Model mirroring source XML structure exactly, navigation helpers,
generic file/reference discovery, and diagnostics (encoding, DOCTYPE,
unsupported constructs, dangling cross-references). **No metadata
extraction, business rules, ICAM construction, transformation, MECA
generation, validation, or packaging was implemented** — see §9 for what
remains deferred and why.

---

## 1. Directory Tree Changes

```
src/meca_engine/extraction/                [was an empty stub — fully implemented]
├── __init__.py                             re-exports every public name
├── parsed_model.py                         ParsedAttribute, ParsedElement, NamespaceDeclaration,
│                                           DoctypeDeclaration, EncodingInfo, SourceLocation,
│                                           DiagnosticSeverity, DiagnosticCategory,
│                                           ParseDiagnostic, ParsedDocument
├── navigation.py                           iter_descendants, find_first, find_all, find_by_path,
│                                           get_attribute, get_text, as_int/as_float/as_bool,
│                                           build_id_index
├── diagnostics.py                          find_dangling_references
├── file_relationships.py                   FileReference, discover_file_references,
│                                           DEFAULT_REFERENCE_ATTRIBUTES, XLINK_NAMESPACE_URI
└── xml_loader.py                           XmlLoader (the orchestrating class)

src/meca_engine/exceptions/article_errors.py  [MODIFIED, docstrings only]
    SourceXmlMalformedError — docstring broadened: now also raised by
    xml_loader (was previously attributed only to the not-yet-built
    kriyadocs_parser)
    SourceUnavailableError — docstring broadened: now also raised by
    xml_loader for a missing/unreadable staged XML file

pyproject.toml                              [MODIFIED]
    + defusedxml>=0.7.1 (core dependency)
    + types-defusedxml>=0.7.0 (dev dependency)
    + [[tool.mypy.overrides]] for defusedxml/botocore import resolution nuances

tests/
├── unit/extraction/                        [NEW] 8 test files + conftest.py + _snapshot_utils.py
│   ├── conftest.py                         write_xml fixture
│   ├── _snapshot_utils.py                  test-only ParsedDocument -> JSON-safe dict serializer
│   ├── test_parsed_model.py
│   ├── test_navigation.py
│   ├── test_file_relationships.py
│   ├── test_diagnostics.py
│   ├── test_xml_loader.py                  the largest file — see §6
│   └── test_golden_snapshots.py
└── fixtures/extraction/                    [NEW]
    ├── valid_sample.xml                    small, representative, purpose-built (not a real sample)
    └── snapshots/valid_sample.snapshot.json   checked-in golden snapshot

config/, schemas/, docs/ (baseline): unchanged.
```

**Stub packages left untouched** (still empty, per scope): `model/`, `transform/`, `generators/*`, `validation/*`, `packaging/`, `output/`, `registry/*`, `retry/`, `recovery/`, `reporting/`, `monitoring/`. `input/`, `checkpoint/`, `orchestrator/` (Milestone 2) also untouched — this milestone added a new, independent package rather than modifying any Milestone 2 code.

---

## 2. New Public Classes

| Class/Type | Module | Kind |
|---|---|---|
| `ParsedAttribute` | `parsed_model` | Frozen dataclass |
| `ParsedElement` | `parsed_model` | Frozen dataclass |
| `NamespaceDeclaration` | `parsed_model` | Frozen dataclass |
| `DoctypeDeclaration` | `parsed_model` | Frozen dataclass |
| `EncodingInfo` | `parsed_model` | Frozen dataclass |
| `SourceLocation` | `parsed_model` | Frozen dataclass |
| `DiagnosticSeverity` | `parsed_model` | Enum |
| `DiagnosticCategory` | `parsed_model` | Enum |
| `ParseDiagnostic` | `parsed_model` | Frozen dataclass |
| `ParsedDocument` | `parsed_model` | Frozen dataclass (the parse result) |
| `FileReference` | `file_relationships` | Frozen dataclass |
| `XmlLoader` | `xml_loader` | Service class (the one public entry point) |

**12 new public types.** `navigation.py` and `diagnostics.py` contribute only functions (no new classes), by design — see Design Decision D-2.

---

## 3. Parsed Object Model

The complete, generic tree/document model (mirrors source XML exactly; carries zero publishing semantics — see `parsed_model.py`'s module docstring for the explicit boundary):

```
ParsedDocument
├── source_path: Path
├── encoding: EncodingInfo(declared_encoding, bom_encoding, effective_encoding)
├── doctype: DoctypeDeclaration(name, public_id, system_id, has_internal_subset) | None
├── root: ParsedElement
│     ├── tag: str                              (local name only)
│     ├── namespace_uri: str | None
│     ├── attributes: tuple[ParsedAttribute, ...]
│     │     each: (name, namespace_uri, value)
│     ├── children: tuple[ParsedElement, ...]    (recursive)
│     ├── text: str | None                       (immediate text, before first child)
│     └── tail: str | None                       (text after this element's closing tag)
├── namespace_declarations: tuple[NamespaceDeclaration(prefix, uri), ...]
└── diagnostics: tuple[ParseDiagnostic(severity, category, message, location), ...]
```

Every type is a frozen dataclass — immutable once constructed, consistent with the ICAM's own philosophy (11_LLD_02... §3.7) and Milestone 2's input-layer models, applied one layer earlier. Tag/attribute/namespace names and text content are preserved **verbatim** — no renaming, no normalization, per the task's explicit instruction. No Python-identifier-collision issue ever arises because names are stored as string *values* inside fixed dataclass fields, never as dynamic Python attribute names (Design Decision D-1).

**Deliberately not modeled** (documented scope cuts, not oversights):
- XML comments and processing instructions are dropped during parsing (matching `xml.etree.ElementTree`'s own default behavior) — nothing downstream needs to reproduce them.
- Per-element source line/column is not tracked (only parse-*error* locations are, via the underlying parser's native `.position`/`.lineno`/`.offset`) — see Design Decision D-3.
- DTD internal-subset contents (entity/attlist declarations) are never parsed or resolved — flagged as a diagnostic only (`has_internal_subset` + an `UNSUPPORTED_CONSTRUCT` diagnostic).

---

## 4. Parser Architecture

```
XmlLoader.load(path: Path) -> ParsedDocument
  │
  ├─ [1] _read_file(path) -> bytes                       # OSError -> SourceUnavailableError
  │
  ├─ [2] _detect_bom(raw_bytes) -> str | None             # 5 BOM signatures, longest-prefix-safe order
  │      _bom_length(raw_bytes) -> int
  │      _detect_declared_encoding(bytes_after_bom)        # regex on the BOM-stripped prolog
  │      effective_encoding = bom or declared or "utf-8"
  │      _encoding_diagnostics(...)                        # INFO (no signal at all) / WARNING (conflict)
  │
  ├─ [3] _detect_doctype(prolog_text) -> (DoctypeDeclaration | None, diagnostics)
  │      regex: name, PUBLIC "pub" "sys" | SYSTEM "sys" | bare, internal-subset `[` flag
  │
  ├─ [4] _collect_namespaces(raw_bytes) -> tuple[NamespaceDeclaration, ...]
  │      via defusedxml.ElementTree.iterparse(events=("start-ns",)) — a dedicated, lightweight
  │      second pass over the same in-memory bytes (no second file read)
  │
  ├─ [5] _parse_tree(raw_bytes) -> Element
  │      via defusedxml.ElementTree.parse()                # SAFE: forbid_entities=True,
  │      forbid_external=True (defusedxml defaults); forbid_dtd stays False (bare DOCTYPE, as
  │      every real sample document uses, must still parse)
  │      ParseError/ExpatError -> SourceXmlMalformedError (BR-001, with line/column when available)
  │      DefusedXmlException  -> SourceXmlMalformedError (entity/external-reference rejected)
  │
  ├─ [6] _convert_element(Element) -> ParsedElement        # recursive; Clark-notation split
  │      via _split_clark("{uri}local" -> (uri, local))
  │
  ├─ [7] find_dangling_references(parsed_root, ...)        # id-index cross-check, "rid" default
  │
  └─ [8] assemble ParsedDocument; log one INFO event; return
```

**Safety model**: `defusedxml.ElementTree` (not bare `xml.etree.ElementTree`) throughout, both for the tree-building pass and the namespace-collecting pass — the stdlib parser does not protect against entity-expansion or external-entity/DTD-fetch attacks by default, and every code path that touches untrusted bytes goes through the safe parser (verified empirically: an internal `<!ENTITY xxe "...">` declaration is rejected as `EntitiesForbidden`, wrapped into the approved `SourceXmlMalformedError`; a realistic external-system-id JATS/MECA DOCTYPE, with no internal entities, parses normally — see Architecture Compliance Report §5 for the exact empirical verification transcript).

---

## 5. Golden Snapshot Strategy

- **Fixture**: `tests/fixtures/extraction/valid_sample.xml` — a small, **purpose-built synthetic** document (not a copy of any real sample package), deliberately exercising: a realistic JATS-style `PUBLIC` DOCTYPE, an `xmlns:xlink` namespace declaration, Unicode text (via numeric character references — café/em-dash/中文), an `id`/`rid` cross-reference pair that correctly resolves, mixed content (`text`/`tail` fidelity), and both an `xlink:href` (`graphic`) and a plain-namespace `xlink:href` (`supplementary-material`) file reference.
- **Serialization**: `tests/unit/extraction/_snapshot_utils.py`'s `document_to_snapshot_dict()` converts a `ParsedDocument` into a JSON-safe, order-stable `dict` — deliberately excluding `source_path` (environment-specific, would make the snapshot non-portable) and diagnostic `location` fields (always `None` per Design Decision D-3).
- **Comparison**: `test_golden_snapshots.py` parses the fixture fresh on every test run and asserts structural equality against the checked-in `valid_sample.snapshot.json` — any unintended change to encoding detection, DOCTYPE parsing, namespace resolution, text/tail handling, or diagnostic generation shows up as a diff here, mirroring `14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md` §11.3's golden-file regression philosophy one layer earlier (before there is a full generation pipeline to regress-test against the 3 real samples).
- **Governance**: the snapshot JSON is checked in and only ever regenerated deliberately (documented in the test module's own docstring) — never auto-regenerated by a test run, so an accidental behavior change is always caught as a failing assertion, not silently re-baselined.

---

## 6. Test Summary

| Test file | Test functions | Executions (incl. parametrized) | Covers |
|---|---|---|---|
| `test_parsed_model.py` | 14 | 14 | Immutability, defaults, enum values |
| `test_navigation.py` | 22 | 39 (parametrized as_int/as_float/as_bool cases) | Every navigation helper, including path-skipping edge cases |
| `test_file_relationships.py` | 6 | 6 | xlink:href, plain href/src, mixed shapes together, no-category guarantee, custom attribute config |
| `test_diagnostics.py` | 7 | 7 | Dangling references, multi-token IDREFS, custom/default attribute names, namespaced-attribute exclusion |
| `test_xml_loader.py` | 35 | 35 | Valid/invalid/broken/empty/truncated XML, missing file, XXE rejection, namespace capture + resolution, BOM (UTF-8/UTF-16) + declared-encoding + conflict + UTF-16-family-rejected-by-parser, DOCTYPE (PUBLIC/SYSTEM/bare/none/internal-subset), 10,000-element large-document parse, Unicode text/attributes, empty elements (both forms), optional attributes, mixed-content text/tail, dangling-reference integration, configurable reference-attribute names, logging integration, error-location formatting (both attribute conventions) |
| `test_golden_snapshots.py` | 2 | 2 | Full-document structural snapshot match; snapshot-file sanity guard |
| **Total** | **88 unique test functions** | **103 actual test executions** | |

All 103 extraction-package test executions pass; the full suite (all 3 milestones combined) is **298 passing tests**, verified in a fresh, from-scratch virtual environment with `ruff check`, `ruff format --check`, and `mypy --strict` all clean on both `src/` and `tests/`.

**A real bug was caught by this test suite before it ever reached this report**: the BOM/declared-encoding conflict diagnostic initially never fired, because `_detect_declared_encoding` was being run against the raw bytes *including* the BOM prefix, and the regex (correctly, per the XML spec's own bootstrapping rule) requires `<?xml` to be the very first thing it sees — the BOM bytes silently made every match attempt fail whenever a BOM was present. Fixed by stripping the detected BOM's exact byte length before running the declared-encoding regex (`_bom_length()`, new helper). This is exactly the kind of defect the task's "Encoding variations" test requirement exists to catch.

---

## 7. Coverage Report

```
Name                                                  Stmts   Miss  Cover
------------------------------------------------------------------------
src/meca_engine/extraction/__init__.py                    7      0   100%
src/meca_engine/extraction/diagnostics.py                15      0   100%
src/meca_engine/extraction/file_relationships.py         21      0   100%
src/meca_engine/extraction/navigation.py                 75      0   100%
src/meca_engine/extraction/parsed_model.py               62      0   100%
src/meca_engine/extraction/xml_loader.py                132      0   100%*
------------------------------------------------------------------------
Milestone 3 module subtotal                             312      0   100%
------------------------------------------------------------------------
TOTAL (whole src/, incl. Milestones 1-2 + untouched stubs)  1410   19    99%
```

\* One line in `xml_loader.py` (`_parse_tree`'s `if root is None:` defensive branch) is marked `# pragma: no cover`, matching Milestone 2's established precedent (`Boto3S3Client`'s internals): a successfully-parsed `ElementTree` document always has a root element — there is no well-formed-XML input that could reach this branch through the public `load()` API, so it exists purely to keep the method's declared return type (`Element`, not `Element | None`) accurate for `mypy --strict`, not as a code path any realistic test could trigger.

**Target ("at least 95% coverage for all new modules") is met: every Milestone 3 module is at 100% coverage.**

---

## 8. Architecture Compliance Report

See the companion document: **`MILESTONE_3_ARCHITECTURE_COMPLIANCE_REPORT.md`** in this same directory.

---

## 9. Deferred Work for Milestone 4

Per the current task's explicit exclusion list, all deferred:

- **Metadata Extraction / Custom-Meta Classification** (`extraction.kriyadocs_parser`, `extraction.custom_meta_classifier`) — the business-rule-driven interpretation of a `ParsedDocument` into typed, Kriyadocs-shaped intermediate structures (Business Rule Book §A-J), built *using* this milestone's `navigation`/`file_relationships`/`diagnostics` helpers rather than re-implementing tree-walking.
- **Round resolution via `vocab-identifier`** (BR-010) — this milestone's `ParsedElement` tree makes the raw `article-version/@vocab-identifier` values retrievable (via `find_all` + `get_attribute`), but extracting/parsing/ordering by the snapshot sequence number is Milestone 4's job.
- **Internal Canonical Article Model** (`model.article.ArticleModelBuilder`, `ArticleModel`) — still untouched; this milestone produces exactly the kind of generic, structure-preserving input the ICAM builder is designed to consume next, but builds none of it itself.
- **File-manifest resolution** (BR-011/BR-014) — this milestone's `discover_file_references` finds structural `xlink:href`/`href`/`src` attributes generically; the actual, business-rule-authoritative file list (driven by custom-meta `named-content` entries, not by scanning for href-bearing elements) is Milestone 4's File Resolver, which will very likely *not* even use `file_relationships.py` for the Kriyadocs input shape specifically (recall from the Reverse Engineering Report: Kriyadocs' file manifest lives entirely in custom-meta, not in JATS `graphic`/`supplementary-material` elements) — `file_relationships.py` remains available as a generic capability for any future XML source that *does* use structural href-based references.
- **All 5 XML generators, Validation Engine, Package Builder, Output Writer, DOI Registry** — untouched stub packages, per scope, unaffected by this milestone.
- **DTD validation** (ADR-025) — `DoctypeDeclaration` captures shape only; fetching/validating against the actual DTD grammar remains a later-milestone Validation Engine concern.

**Explicit dependency check before Milestone 4 begins**: `ParsedDocument`/`ParsedElement` (this milestone's output) are exactly the inputs Milestone 4's Metadata Extractor is designed to consume via this milestone's `navigation` helpers — nothing left open in this milestone blocks that work. The one open question worth flagging explicitly for Milestone 4 planning: whether `extraction.kriyadocs_parser` should be a genuinely separate module layered on top of `xml_loader`/`navigation` (this milestone's recommendation, consistent with the LLD's original `extraction.kriyadocs_parser` naming) or whether some of its logic naturally belongs inside `custom_meta_classifier` instead — a design detail for Milestone 4 to settle, not a blocker.
