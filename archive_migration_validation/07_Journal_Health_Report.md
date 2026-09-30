# Journal Health Report (Summary)

Full version: `Journal_Health_Report.html`. Computed by `reporting/intelligence/journal_statistics.py` directly from the 37-article batch's `ConversionReport`s — no re-validation. Figures below are copied exactly from `dashboard_intelligence.json`.

| Journal | Articles | Avg Confidence | Manual Review | Recovery Rule Counts |
|---|---|---|---|---|
| Clinical Science | 10 | 40.3 | 10 | RR-004: 10, RR-001: 1, RR-002: 2 |
| Biochemical Journal | 6 | 45.7 | 5 | RR-004: 5, RR-002: 1, RR-005: 1 |
| Bioscience Reports | 6 | 71.5 | 5 | RR-004: 5 |
| Biochemical Society Transactions | 5 | 70.4 | 4 | RR-004: 4 |
| Essays in Biochemistry | 5 | 70.8 | 4 | RR-004: 4 |
| Emerging Topics in Life Sciences | 5 | 70.6 | 5 | RR-002: 1, RR-004: 4 |

Every journal shows the same top 3 Business Rule issues — BR-103, BR-110, BR-123 — each at or near 100% trigger rate, which is why all three are the subject of per-journal downgrade recommendations in `Recommendations.md`.

Clinical Science is clearly the outlier: lowest average confidence (40.3, well below the corpus average of 58.5) and the only journal with meaningful `RR-001`/`RR-002` volume — consistent with 2 of the batch's 4 `PARTIAL_CERTIFICATION` outcomes (`cs-2024-5238`, `cs-2025-6682`) belonging to Clinical Science; the other 2 (`bcj-2025-3378`, `etls-2025-3020`) belong to Biochemical Journal and Emerging Topics in Life Sciences respectively.
