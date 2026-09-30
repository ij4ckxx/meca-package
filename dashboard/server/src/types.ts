export type PackageStatusValue =
  | "certified"
  | "certified_with_warnings"
  | "certified_with_recovery"
  | "partial_certification"
  | "engine_failure"
  | "fatal_failure";

export type ConfidenceLevel = "low" | "medium" | "high";

export type OutputCategory = "uploaded" | "manual_review" | "failed";

export interface EngineWarningRecord {
  code: string;
  rule?: string | null;
  business_rule_id?: string | null;
  recovery_rule_id?: string | null;
  category?: string;
  severity: string;
  origin?: string;
  recovery_applied?: boolean;
  confidence?: string;
  message: string;
  affected_file?: string | null;
  affected_article?: string;
  suggested_action?: string | null;
  context?: Record<string, unknown>;
}

export interface GeneratorFinding {
  severity: string;
  generator_name: string;
  message: string;
  business_rule_id: string | null;
  recovery_rule_id: string | null;
  context: Record<string, unknown>;
}

export interface BusinessRuleFinding {
  rule_id: string;
  message: string;
  severity: string;
  source: string;
}

export type ValidationResultValue = "pass" | "warning" | "error";

export type SpecAlignmentCategory =
  | "source_data_issue"
  | "business_rule_candidate"
  | "recovery_rule_candidate"
  | "validation_only";

export interface ValidationIssue {
  severity: string;
  message: string;
  line: number | null;
  xpath: string | null;
  check: "well-formed" | "dtd" | null;
  category: SpecAlignmentCategory | null;
}

export interface FileValidationReport {
  filename: string;
  dtd_name: string | null;
  dtd_available: boolean;
  result: ValidationResultValue;
  well_formed_result: ValidationResultValue;
  dtd_result: ValidationResultValue | null;
  error_count: number;
  warning_count: number;
  issues: ValidationIssue[];
}

export interface PackageValidationReport {
  article_id: string;
  overall_result: ValidationResultValue;
  overall_dtd_result: ValidationResultValue | null;
  total_errors: number;
  total_warnings: number;
  category_counts: Partial<Record<SpecAlignmentCategory, number>>;
  files: FileValidationReport[];
}

export interface ConversionReportRecord {
  article_id: string;
  status: PackageStatusValue;
  confidence_score: number;
  overall_confidence: ConfidenceLevel;
  warnings: EngineWarningRecord[];
  recoveries: EngineWarningRecord[];
  generator_findings: GeneratorFinding[];
  unrecoverable_error: Record<string, unknown> | null;
  fatal_errors: Record<string, unknown>[];
  business_rule_findings: BusinessRuleFinding[];
  business_rules_passed: string[];
  business_rules_failed: string[];
  recovery_rules_applied: string[];
  generated_files: string[];
  missing_files: string[];
  skipped_files: string[];
  missing_metadata: string[];
  journal: string;
  validation_report: PackageValidationReport | null;
  reproducibility: Record<string, string> | null;
}

export interface ArticleLocation {
  category: OutputCategory;
  zipFile: string | null;
  certificationHtmlFile: string | null;
  validationHtmlFile: string | null;
  migrationAuditHtmlFile: string | null;
  migrationAuditJsonFile: string | null;
}

export interface ArticleSummary {
  article_id: string;
  journal: string;
  status: PackageStatusValue;
  confidence_score: number;
  overall_confidence: ConfidenceLevel;
  warning_count: number;
  recovery_count: number;
  category: OutputCategory;
}

export interface ArticleDetail extends ConversionReportRecord {
  warning_count: number;
  recovery_count: number;
  category: OutputCategory;
  has_zip: boolean;
  has_certification_report: boolean;
  has_validation_report: boolean;
  has_migration_audit_report: boolean;
  package_size_bytes: number | null;
}

export interface JournalStats {
  journal: string;
  article_count: number;
  status_counts: Record<string, number>;
  average_confidence_score: number;
  recovery_rule_counts: Record<string, number>;
  business_rule_failure_counts: Record<string, number>;
  recovery_rate: number;
  common_recovery_rule: string | null;
  most_common_warning: string | null;
  total_warnings: number;
}

export interface RecoveryRuleStats {
  rule_id: string;
  occurrences: number;
  articles_affected: number;
  is_significant_deficiency: boolean;
  clean_success_rate: number;
  dominant_confidence: string;
}

export interface BusinessRuleStats {
  rule_id: string;
  total_triggered: number;
  total_recovered: number;
  total_failed: number;
  ever_fatal: boolean;
}

export interface WarningStats {
  code: string;
  source: string;
  sample_message: string;
  occurrences: number;
  articles_affected: number;
  always_successful: boolean;
}

export type DtdResultBucket = ValidationResultValue | "not_checked";

export interface ValidationStats {
  overall_counts: Record<ValidationResultValue, number>;
  dtd_counts: Record<DtdResultBucket, number>;
  total_errors: number;
  total_warnings: number;
  dtd_not_vendored_count: number;
  common_issues: { message: string; occurrences: number }[];
  spec_alignment_counts: Partial<Record<SpecAlignmentCategory, number>>;
  engine_defects_fixed_count: number;
}

export interface SummaryStats {
  total_articles: number;
  status_counts: Record<string, number>;
  confidence_distribution: Record<string, number>;
  category_counts: Record<OutputCategory, number>;
  validation_counts: Record<ValidationResultValue, number>;
  dtd_counts: Record<DtdResultBucket, number>;
  spec_alignment_counts: Partial<Record<SpecAlignmentCategory, number>>;
  engine_defects_fixed_count: number;
}

export interface ManualReviewEntry {
  article_id: string;
  journal: string;
  reason: string;
  confidence_score: number;
  note?: string;
  status?: ReviewStatus;
}

export type ReviewStatus = "pending" | "reviewed" | "accepted" | "rejected";

export interface ReviewNote {
  note: string;
  status: ReviewStatus;
  updated_at: string;
}

export interface BatchSummary {
  batch_id: string;
  created_at: string;
  total: number;
  success: number;
  recovery: number;
  manual_review: number;
  failed: number;
  duration_seconds: number | null;
}
