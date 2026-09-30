import { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { FileArchive, FileText, FileJson, ChevronLeft } from "lucide-react";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import { StatusBadge } from "../components/StatusBadge";
import { ValidationBadge } from "../components/ValidationBadge";
import { LoadingState, ErrorState } from "../components/States";
import { useBatch } from "../context/BatchContext";

type Tab =
  | "summary"
  | "business"
  | "recovery"
  | "warnings"
  | "missing"
  | "generated"
  | "certification"
  | "validation"
  | "audit";

const XML_BUTTONS = [
  { kind: "raw", label: "raw.xml" },
  { kind: "article", label: "article.xml" },
  { kind: "transfer", label: "transfer.xml" },
  { kind: "manifest", label: "manifest.xml" },
  { kind: "reviews", label: "reviews.xml" },
];

const SPEC_ALIGNMENT_LABELS: Record<string, string> = {
  source_data_issue: "Source Data Issue",
  business_rule_candidate: "Business Rule Candidate",
  recovery_rule_candidate: "Recovery Rule Candidate",
  validation_only: "Validation Only",
};

function formatBytes(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function overallWellFormedResult(files: { well_formed_result: string }[]): "pass" | "error" {
  return files.some((f) => f.well_formed_result === "error") ? "error" : "pass";
}

function confidenceTone(score: number): string {
  if (score >= 80) return "var(--success)";
  if (score >= 50) return "var(--warning)";
  return "var(--danger)";
}

export function ArticleDetailPage() {
  const { id = "" } = useParams();
  const { selectedBatchId } = useBatch();
  const { data, loading, error } = useApi(
    useCallback(() => api.getArticle(selectedBatchId, id), [selectedBatchId, id]),
    [selectedBatchId, id],
  );
  const [tab, setTab] = useState<Tab>("summary");

  if (loading) return <LoadingState label="Loading article..." />;
  if (error) return <ErrorState message={error} />;
  if (!data) return null;

  const isManualReview = data.category === "manual_review";
  const isFailure = data.category === "failed";

  // Business Rule Timeline: passed rules + every finding, grouped by rule number.
  const ruleGroups = new Map<string, { passed: boolean; findings: typeof data.business_rule_findings }>();
  for (const ruleId of data.business_rules_passed) {
    ruleGroups.set(ruleId, { passed: true, findings: [] });
  }
  for (const finding of data.business_rule_findings) {
    const existing = ruleGroups.get(finding.rule_id) ?? { passed: false, findings: [] };
    existing.findings.push(finding);
    ruleGroups.set(finding.rule_id, existing);
  }

  const warningsCount = data.warnings.length + data.generator_findings.length;
  const reproEntries = data.reproducibility ? Object.entries(data.reproducibility) : [];

  const TABS: { key: Tab; label: string; count?: number }[] = [
    { key: "summary", label: "Summary" },
    { key: "business", label: "Business Rule Timeline", count: ruleGroups.size },
    { key: "recovery", label: "Recovery Timeline", count: data.recoveries.length },
    { key: "warnings", label: "Warnings", count: warningsCount },
    { key: "missing", label: "Missing Files", count: data.missing_files.length },
    { key: "generated", label: "Generated Files", count: data.generated_files.length },
    { key: "certification", label: "Certification Report" },
    { key: "validation", label: "XML Validation" },
    { key: "audit", label: "Migration Audit" },
  ];

  return (
    <div>
      <div className="page-header">
        <Link to="/articles" className="button button-secondary" style={{ marginBottom: 12 }}>
          <ChevronLeft size={14} /> Back to Articles
        </Link>
      </div>

      <div className="detail-header-card">
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div className="detail-icon-badge">
            <FileText size={24} />
          </div>
          <div>
            <div className="detail-title-row">
              <h1 className="mono" style={{ margin: 0, fontSize: 19 }}>
                {data.article_id}
              </h1>
              <StatusBadge status={data.status} />
            </div>
            <p className="subtitle" style={{ margin: "4px 0 0" }}>
              {data.journal} &middot; category: {data.category}
            </p>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
          <div
            className="confidence-donut"
            style={{
              background: `conic-gradient(${confidenceTone(data.confidence_score)} 0% ${data.confidence_score}%, var(--border) ${data.confidence_score}% 100%)`,
            }}
          >
            <div className="confidence-donut-inner">{data.confidence_score}</div>
          </div>
          <span style={{ fontSize: 9.5, color: "var(--text-faint)", fontWeight: 600, textTransform: "uppercase" }}>
            Confidence
          </span>
        </div>
      </div>

      <div className="button-row">
        <a
          className={`button ${data.has_zip ? "" : "button-disabled"}`}
          href={data.has_zip ? api.zipDownloadUrl(selectedBatchId, data.article_id) : undefined}
        >
          <FileArchive size={14} /> MECA ZIP
        </a>
        {XML_BUTTONS.map((x) => (
          <a
            key={x.kind}
            className={`button button-secondary ${data.has_zip ? "" : "button-disabled"}`}
            href={data.has_zip ? api.xmlDownloadUrl(selectedBatchId, data.article_id, x.kind) : undefined}
          >
            <FileText size={14} /> {x.label}
          </a>
        ))}
        <a
          className={`button button-secondary ${data.has_certification_report ? "" : "button-disabled"}`}
          href={
            data.has_certification_report
              ? api.certificationDownloadUrl(selectedBatchId, data.article_id)
              : undefined
          }
        >
          <FileText size={14} /> Certification Report
        </a>
        <a
          className={`button button-secondary ${data.has_validation_report ? "" : "button-disabled"}`}
          href={
            data.has_validation_report
              ? api.validationReportDownloadUrl(selectedBatchId, data.article_id)
              : undefined
          }
        >
          <FileText size={14} /> Validation Report
        </a>
        <a
          className={`button button-secondary ${data.has_migration_audit_report ? "" : "button-disabled"}`}
          href={
            data.has_migration_audit_report
              ? api.migrationAuditReportDownloadUrl(selectedBatchId, data.article_id)
              : undefined
          }
        >
          <FileText size={14} /> Migration Audit Report
        </a>
        <a className="button button-secondary" href={api.reportJsonDownloadUrl(selectedBatchId, data.article_id)}>
          <FileJson size={14} /> conversion-report.json
        </a>
        <a
          className={`button button-secondary ${data.has_migration_audit_report ? "" : "button-disabled"}`}
          href={
            data.has_migration_audit_report
              ? api.migrationAuditJsonDownloadUrl(selectedBatchId, data.article_id)
              : undefined
          }
        >
          <FileJson size={14} /> migration-audit.json
        </a>
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t.key} className={`tab ${tab === t.key ? "tab-active" : ""}`} onClick={() => setTab(t.key)}>
            {t.label}
            {!!t.count && <span className="tab-count">{t.count}</span>}
          </button>
        ))}
      </div>

      <div className="detail-grid">
        <div className="tab-panel">
          {tab === "summary" && (
            <div>
              <p>
                <strong>DOI:</strong> not exposed by the engine's reporting model yet
              </p>
              <p>
                <strong>Category:</strong> {data.category}
              </p>
              {isManualReview && (
                <p>
                  <strong>Manual Review Reason:</strong>{" "}
                  {data.missing_files.length > 0
                    ? `Missing ${data.missing_files.length} file(s)`
                    : data.business_rules_failed.length > 0
                      ? `Business rule finding: ${data.business_rules_failed.join(", ")}`
                      : "Partial certification"}
                </p>
              )}
              {isFailure && data.unrecoverable_error && (
                <p>
                  <strong>Failure:</strong> {data.unrecoverable_error.message}{" "}
                  <span style={{ color: "var(--text-faint)", fontSize: 12 }}>
                    (stage: {data.unrecoverable_error.stage})
                  </span>
                </p>
              )}
              <p>
                <strong>Recovery Rules Applied:</strong> {data.recovery_rules_applied.join(", ") || "none"}
              </p>
            </div>
          )}
          {tab === "business" && (
            <div>
              <h3 style={{ margin: "0 0 4px" }}>Business Rule Timeline</h3>
              {[...ruleGroups.entries()]
                .sort((a, b) => a[0].localeCompare(b[0]))
                .map(([ruleId, group]) => (
                  <div key={ruleId}>
                    {group.passed && group.findings.length === 0 && (
                      <div className="rule-timeline-row">
                        <span className="rule-timeline-pill" style={{ background: "var(--success-soft)", color: "var(--success)" }}>
                          Passed
                        </span>
                        <div>
                          <span className="mono" style={{ fontWeight: 700 }}>
                            {ruleId}
                          </span>
                        </div>
                      </div>
                    )}
                    {group.findings.map((f, i) => (
                      <div className="rule-timeline-row" key={i}>
                        <span
                          className="rule-timeline-pill"
                          style={
                            f.severity === "warning"
                              ? { background: "var(--warning-soft)", color: "var(--warning)" }
                              : { background: "var(--info-soft)", color: "var(--info)" }
                          }
                        >
                          {f.severity === "warning" ? "Warning" : "Applied"}
                        </span>
                        <div>
                          <span className="mono" style={{ fontWeight: 700 }}>
                            {ruleId}
                          </span>
                          <span style={{ color: "var(--text-muted)", marginLeft: 8 }}>{f.message}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              {ruleGroups.size === 0 && <p>No business rule activity recorded.</p>}
            </div>
          )}
          {tab === "recovery" && (
            <div>
              {data.recoveries.map((r, i) => (
                <div key={i} className="panel" style={{ marginBottom: 10 }}>
                  <p style={{ margin: 0 }}>
                    <strong>{r.recovery_rule_id ?? "—"}</strong> (Business Rule {r.business_rule_id ?? "—"})
                  </p>
                  <p style={{ margin: "4px 0", fontSize: 12.5 }}>{r.message}</p>
                  <p style={{ margin: 0, fontSize: 12, color: "var(--text-faint)" }}>
                    Confidence: {r.confidence ?? "—"} · Affected file: {r.affected_file ?? "—"}
                  </p>
                </div>
              ))}
              {data.recoveries.length === 0 && <p>No recoveries were needed for this article.</p>}
            </div>
          )}
          {tab === "warnings" && (
            <ul>
              {data.warnings.map((w, i) => (
                <li key={`w-${i}`}>
                  [{w.code}] {w.message}
                </li>
              ))}
              {data.generator_findings.map((f, i) => (
                <li key={`g-${i}`}>
                  [{f.generator_name}] {f.message}
                </li>
              ))}
              {data.warnings.length === 0 && data.generator_findings.length === 0 && <p>No warnings.</p>}
            </ul>
          )}
          {tab === "missing" && (
            <ul>
              {data.missing_files.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
              {data.missing_files.length === 0 && <p>No missing files.</p>}
            </ul>
          )}
          {tab === "generated" && (
            <ul>
              {data.generated_files.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
              {data.generated_files.length === 0 && <p>No package was generated for this article.</p>}
            </ul>
          )}
          {tab === "certification" &&
            (data.has_certification_report ? (
              <iframe
                title="Certification Report"
                src={api.certificationViewUrl(selectedBatchId, data.article_id)}
                className="certification-frame"
              />
            ) : (
              <p>No certification report available.</p>
            ))}
          {tab === "validation" &&
            (data.validation_report ? (
              <div>
                {Object.keys(data.validation_report.category_counts).length > 0 && (
                  <p style={{ fontSize: 12.5, color: "var(--text-faint)" }}>
                    Remaining findings:{" "}
                    {Object.entries(data.validation_report.category_counts)
                      .map(([cat, count]) => `${SPEC_ALIGNMENT_LABELS[cat] ?? cat}: ${count}`)
                      .join(" · ")}
                  </p>
                )}
                {data.validation_report.files.map((f) => (
                  <div key={f.filename} className="panel" style={{ marginBottom: 10 }}>
                    <p style={{ margin: 0 }}>
                      <strong>{f.filename}</strong> <ValidationBadge result={f.well_formed_result} label="Well-formed" />{" "}
                      <ValidationBadge result={f.dtd_result} label="DTD" />
                    </p>
                    <p style={{ margin: "4px 0", fontSize: 12, color: "var(--text-faint)" }}>
                      DTD: {f.dtd_name ?? "n/a"}
                      {f.dtd_name && !f.dtd_available ? " (not vendored — DTD not checked)" : ""}
                      {" · "}
                      Errors: {f.error_count} · Warnings: {f.warning_count}
                    </p>
                    {f.issues.length > 0 && (
                      <ul style={{ fontSize: 12.5, margin: "4px 0" }}>
                        {f.issues.map((issue, i) => (
                          <li key={i}>
                            [{issue.check ?? "?"}/{issue.severity}] {issue.message}
                            {issue.line != null ? ` (line ${issue.line})` : ""}
                            {issue.xpath ? ` — ${issue.xpath}` : ""}
                            {issue.category ? (
                              <span className="badge badge-blue" style={{ marginLeft: 6 }}>
                                {SPEC_ALIGNMENT_LABELS[issue.category] ?? issue.category}
                              </span>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
                {data.has_validation_report && (
                  <a
                    className="button button-secondary"
                    href={api.validationReportViewUrl(selectedBatchId, data.article_id)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <FileText size={14} /> Open full Validation Report
                  </a>
                )}
              </div>
            ) : (
              <p>No validation data available for this article.</p>
            ))}
          {tab === "audit" && (
            <div>
              {data.reproducibility ? (
                <table className="data-table" style={{ marginBottom: 12 }}>
                  <tbody>
                    {Object.entries(data.reproducibility).map(([key, value]) => (
                      <tr key={key}>
                        <th style={{ textAlign: "left", width: 220 }}>{key}</th>
                        <td>{String(value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p>No reproducibility metadata recorded for this package.</p>
              )}
              {data.has_migration_audit_report && (
                <a
                  className="button button-secondary"
                  href={api.migrationAuditReportViewUrl(selectedBatchId, data.article_id)}
                  target="_blank"
                  rel="noreferrer"
                >
                  <FileText size={14} /> Open full Migration Audit Report
                </a>
              )}
            </div>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="panel" style={{ marginBottom: 0 }}>
            <h3 style={{ margin: "0 0 10px", fontSize: 12.5 }}>Reproducibility</h3>
            {reproEntries.length === 0 ? (
              <p style={{ margin: 0, fontSize: 11.5, color: "var(--text-faint)" }}>Not recorded.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {reproEntries.slice(0, 6).map(([key, value]) => (
                  <div className="side-panel-row" key={key}>
                    <span>{key}</span>
                    <span className="mono" style={{ fontWeight: 600 }}>
                      {String(value)}
                    </span>
                  </div>
                ))}
                {reproEntries.length > 6 && (
                  <button className="link-button" onClick={() => setTab("audit")}>
                    View full audit trail →
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="panel" style={{ marginBottom: 0 }}>
            <h3 style={{ margin: "0 0 10px", fontSize: 12.5 }}>Validation Snapshot</h3>
            {data.validation_report ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <ValidationBadge result={overallWellFormedResult(data.validation_report.files)} label="Well-formed" />
                <ValidationBadge result={data.validation_report.overall_dtd_result} label="DTD" />
                <span style={{ fontSize: 11.5, color: "var(--text-faint)" }}>
                  {data.validation_report.total_errors} errors &middot; {data.validation_report.total_warnings} warnings
                </span>
                <button className="link-button" onClick={() => setTab("validation")}>
                  View full validation report →
                </button>
              </div>
            ) : (
              <p style={{ margin: 0, fontSize: 11.5, color: "var(--text-faint)" }}>Not available.</p>
            )}
          </div>

          <div className="panel" style={{ marginBottom: 0 }}>
            <h3 style={{ margin: "0 0 10px", fontSize: 12.5 }}>Package</h3>
            <div className="side-panel-row">
              <span>Size</span>
              <span style={{ fontWeight: 600 }}>{formatBytes(data.package_size_bytes)}</span>
            </div>
            <div className="side-panel-row" style={{ marginTop: 8 }}>
              <span>Warnings / Recoveries</span>
              <span style={{ fontWeight: 600 }}>
                {data.warning_count} / {data.recovery_count}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
