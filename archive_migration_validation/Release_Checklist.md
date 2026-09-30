# Release Readiness Checklist — v1.0.0-rc1

| Item | Status | Notes |
|---|---|---|
| Repository ready | ✅ | Cleaned: 6 large obsolete-output folders archived, 4 orphaned/stray files removed, verification-run clutter cleared. See `Repository_Cleanup.md`. |
| Configuration ready | ✅ | No secrets committed. Every `runtime.yaml` section now marked `[LIVE]`/`[NOT YET WIRED]`. See `Configuration_Review.md`. |
| Dashboard ready | ✅ | Navigation, routing, dark mode, batch switching, manual review, config page all verified working; 1 security fix applied uniformly across every route. See `Dashboard_Review.md`. |
| Processing Service ready | ✅ | Unchanged this milestone; batch-crash safety net and incremental reporting from the prior Production Readiness milestone remain in place and re-verified. |
| Business Rules frozen | ✅ | 163 rules (BR-001–BR-163), unchanged this milestone. |
| Recovery Rules frozen | ✅ | 7 rules (RR-001–RR-007), unchanged this milestone. |
| DTD validation enabled | ✅ | NISO MECA 1.0 + JATS Archiving 1.2, vendored verbatim; validates all 4 generated XML files per package. |
| Migration Audit enabled | ✅ | Unchanged this milestone; per-package and per-batch reports confirmed generating in the full batch run. |
| Certification enabled | ✅ | Unchanged this milestone; Certification Report now also surfaces the specific failure reason for failed articles (fixed 2 milestones ago, re-verified). |
| Reports enabled | ✅ | All report types (Certification, Validation, Migration Audit, Transformation Summary, Batch Audit, Operator Checklist) confirmed generating correctly in the full batch run. |
| Manual Review enabled | ✅ | 10/97 articles correctly routed to manual review in the final verification batch; workflow (note-taking, restart-manual-review) verified via API review. |
| S3 placeholders ready | ✅ | `output.operational_bucket`/`archival_bucket` present, clearly named, explicitly marked `[NOT YET WIRED]` — ready to be replaced with real bucket names and wired up in the AWS integration phase. |
| SFTP placeholders ready | ✅ | `SftpOutputProvider` exists as a documented placeholder (`providers/output.py`), `"SFTP"` is already a valid `output.provider` enum value in `runtime.schema.json` — same pattern as the S3 placeholders, ready to be implemented in the AWS integration phase. |
| AWS deployment | ⏳ Pending | Explicitly out of scope for this milestone, as instructed. `S3InputProvider` exists as a documented placeholder (`ProviderNotConfiguredError` stub); no S3/SFTP/Docker/Kubernetes/Terraform/CloudFormation/CI-CD present anywhere, confirmed. |

## Explicitly not implemented this milestone (by instruction)

No AWS, S3, SFTP, Docker, Kubernetes, Terraform, CloudFormation, CI/CD,
Authentication, User Management, Database, Notifications, Email, Queue
Services, Redis, RabbitMQ, EventBridge, Step Functions, Lambda, new
Business Rules, new Recovery Rules, or feature requests — confirmed none
of this milestone's changes introduce any of the above.
