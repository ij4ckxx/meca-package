# Recovery Rules

A dedicated catalog, separate from the Business Rule Book (`src/meca_engine/model/recovery_rules.py`). Business Rules describe the ideal output; Recovery Rules describe how the engine proceeds when a Business Rule can't be fully satisfied — never fabricating, never modifying source files, never applying silently.

| Rule | Name | Description | Confidence | Occurrences (37-package batch) |
|---|---|---|---|---|
| **RR-001** | Filename recovered from path basename | Declared file name was empty but its declared path was usable; filename derived from the path's basename, generation-only. | HIGH | 12 |
| **RR-002** | Missing supporting file skipped | A declared, non-manuscript file (license, cover letter, figure, etc.) has no matching physical file; the entry is skipped, package generated without it. **Never applied to the manuscript file itself** — that stays fatal. | MEDIUM | 11 |
| **RR-003** | Missing reviewer identity omitted | A reviewer scorecard has real recommendation/comment content but no name or email; content kept, identity omitted. | MEDIUM | 0 (not exercised by this corpus) |
| **RR-004** | File resolved via filename tolerance matching | Declared filename resolved to a physical file via stem/prefix/normalized matching rather than an exact name match. | LOW | 189 |
| **RR-005** | Duplicate round-version snapshot deduplicated | Multiple `<article-version>` elements shared the same sequence number and label (repeated autosave events); collapsed to one round. | HIGH | 1 |
| **RR-006** | Malformed round-version metadata skipped | An `<article-version>` element had an unrecognized/missing vocab-identifier or type; excluded from the round index. | MEDIUM | 0 (not exercised by this corpus) |
| **RR-007** | Optional XML section omitted | An optional article.xml section (e.g. `<license>`) couldn't be populated from a config/source gap; omitted rather than fabricated. | MEDIUM | 0 (not exercised by this corpus) |

**Total recoveries applied across the batch: 213.**

RR-003/006/007 exist in the catalog and are wired into the engine (tested at the unit level) but did not fire against this specific 37-package corpus — real evidence, not a gap in implementation.

**PARTIAL_CERTIFICATION signal:** RR-002 is the one rule flagged as a "significant deficiency" (`SIGNIFICANT_DEFICIENCY_RULE_IDS` in the catalog) — it's the only rule where real, declared content ends up absent from the package. Every other rule represents a lossless alternate resolution (derived, matched, or deduplicated), so packages using only those rules certify as `CERTIFIED_WITH_RECOVERY`, not `PARTIAL_CERTIFICATION`.
