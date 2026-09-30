# Dashboard JSON Specification — `dashboard_intelligence.json`

Produced by `reporting/intelligence/corpus_analyzer.py::build_dashboard_intelligence`. Pure data — no dashboard UI is built by this milestone.

## Top-level shape

```json
{
  "total_articles": 37,
  "journals": { "<journal name>": { ... JournalStats ... } },
  "business_rules": { "<BR-XXX>": { ... BusinessRuleStats ... } },
  "recovery_rules": { "<RR-XXX>": { ... RecoveryRuleStats ... } },
  "warnings": [ { ... WarningStats ... } ],
  "confidence": { ... ConfidenceStats ... },
  "package_status": { "<article_id>": { "status": "...", "journal": "..." } },
  "manual_review": ["<article_id>", ...],
  "recommendations": [ { ... Recommendation ... } ]
}
```

`business_rules`/`recovery_rules` include only entries actually observed in the batch (unused/never-applied rules are omitted, matching the Markdown reports — a dashboard can compute "unused" as catalog-minus-present-keys).

## `JournalStats`

| Field | Type | Meaning |
|---|---|---|
| `journal` | string | Journal display name |
| `article_count` | int | Articles from this journal |
| `status_counts` | object | Status → count |
| `confidence_distribution` | object | HIGH/MEDIUM/LOW → count |
| `average_confidence_score` | float | 0–100 |
| `recovery_rule_counts` | object | RR-XXX → occurrence count |
| `business_rule_failure_counts` | object | BR-XXX → count of articles where it triggered |
| `manual_review_count` | int | Articles from this journal needing review |

## `BusinessRuleStats`

`rule_id`, `total_triggered`, `total_recovered`, `total_failed`, `ever_fatal` (bool), `journal_trigger_rates` (object: journal → 0–1 fraction).

## `RecoveryRuleStats`

`rule_id`, `occurrences`, `articles_affected`, `is_significant_deficiency` (bool), `failure_correlated_articles`, `partial_certification_articles`, `clean_success_rate` (0–1), `observed_confidence_levels` (object), `dominant_confidence` (string or null).

## `WarningStats` (array entries)

`code`, `source` (`"engine_warning"` | `"generator_diagnostic"`), `sample_message`, `occurrences`, `articles_affected`, `always_successful` (bool).

## `ConfidenceStats`

`distribution` (object), `average_score`, `median_score`, `average_by_journal` (object), `average_by_recovery_rule` (object).

## `Recommendation` (array entries)

`id`, `category` (`business_rule` | `recovery_rule` | `warning` | `journal_config`), `title`, `rationale`, `evidence` (object — always includes raw counts/rates, never prose alone).

## Companion file: `Migration_Trends.json`

Separate from `dashboard_intelligence.json` (produced by `trend_analyzer.py`). Shape: `{"status": "insufficient_history" | "computed" | "no_data", "points": [TrendPoint...], "deltas": [Delta...]}`. With only one batch run available, `status` is currently `"insufficient_history"` and `deltas` is empty — this is expected, not an error; re-running the batch and passing both snapshots to `trend_analyzer.analyze_trends` will populate real deltas.
