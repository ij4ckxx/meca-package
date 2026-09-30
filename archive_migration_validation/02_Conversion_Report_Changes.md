# Conversion Report — New Fields

`ConversionReport` (`src/meca_engine/packaging/conversion_report.py`) extended, not rewritten. All prior fields are unchanged.

## Package status

`status` now uses the 6-value model: `CERTIFIED`, `CERTIFIED_WITH_WARNINGS`, `CERTIFIED_WITH_RECOVERY`, `PARTIAL_CERTIFICATION`, `ENGINE_FAILURE`, `FATAL_FAILURE`. Decision order in `PackageBuilder._compute_status`: a recovery tagged with a "significant deficiency" Recovery Rule (currently only RR-002) → `PARTIAL_CERTIFICATION`; any other recovery → `CERTIFIED_WITH_RECOVERY`; any advisory warning/generator finding with no recovery → `CERTIFIED_WITH_WARNINGS`; otherwise → `CERTIFIED`.

## New per-warning fields (`EngineWarning`)

Every warning/recovery entry in the report now serializes with:

| Field | Meaning |
|---|---|
| `rule` | The most specific identifier — the Recovery Rule ID if this was a recovery, else the Business Rule ID |
| `business_rule_id` | The Business Rule this relates to (never a Recovery Rule ID — kept separate per instruction) |
| `recovery_rule_id` | The Recovery Rule applied, if any |
| `severity` / `origin` | Unchanged from Milestone 11 |
| `recovery_applied` | `true`/`false` (was `is_recovery`) |
| `confidence` | `HIGH` / `MEDIUM` / `LOW` — reporting-only, per Recovery Rule |
| `affected_file` | The specific file this finding concerns, when applicable |
| `affected_article` | The article ID |
| `message`, `context` | Unchanged |

Generator-layer findings (`generator_findings`, the pre-existing `GeneratorDiagnostic` system) are left structurally unchanged — extending that type would have touched every one of the 5 generators. Instead, `business_rule_id`/`recovery_rule_id` are extracted from its message text (both mechanisms already embed `BR-XXX`/`RR-XXX` literally).

## New report-level fields

| Field | Meaning |
|---|---|
| `overall_confidence` | `confidence_score` bucketed into HIGH (≥70) / MEDIUM (≥40) / LOW |
| `business_rules_passed` / `business_rules_failed` | Split of a tracked subset of Business Rules (BR-010, 011, 013, 016, 063, 112 — the ones this recovery framework has explicit per-article signal for) into passed/failed for this article. Not a re-validation of all 160 rules. |
| `recovery_rules_applied` | Distinct Recovery Rule IDs that fired, from both `EngineWarning` and generator-diagnostic sources |
| `generated_files` | Hrefs of every file actually packaged |
| `missing_files` / `skipped_files` | Declared files that couldn't be resolved (RR-002) — the same underlying event, exposed under both names |
| `fatal_errors` | `unrecoverable_error` in list form (0 or 1 entries), kept alongside the original singular field |

No dashboard was built — this is the JSON/report model only.
