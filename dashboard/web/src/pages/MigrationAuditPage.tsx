import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, ShieldCheck, ExternalLink } from "lucide-react";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import { StatusBadge } from "../components/StatusBadge";
import { useBatch } from "../context/BatchContext";
import { LoadingState, ErrorState, EmptyState } from "../components/States";
import { Pagination } from "../components/Pagination";
import { confidenceColor } from "../utils/confidence";
import type { ValidationResultValue } from "../types";

const STATUS_OPTIONS = [
  "certified",
  "certified_with_warnings",
  "certified_with_recovery",
  "partial_certification",
  "engine_failure",
  "fatal_failure",
];
const CONFIDENCE_OPTIONS = ["low", "medium", "high"];
const RESULT_OPTIONS: ValidationResultValue[] = ["pass", "warning", "error"];
const DTD_RESULT_OPTIONS = [...RESULT_OPTIONS, "not_checked"];
const PAGE_SIZE = 15;

export function MigrationAuditPage() {
  const { selectedBatchId } = useBatch();
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const journal = searchParams.get("journal") ?? "";
  const status = searchParams.get("status") ?? "";
  const confidence = searchParams.get("confidence") ?? "";
  const business_rule = searchParams.get("business_rule") ?? "";
  const recovery_rule = searchParams.get("recovery_rule") ?? "";
  const warning = searchParams.get("warning") ?? "";
  const validation = searchParams.get("validation") ?? "";
  const dtd_result = searchParams.get("dtd_result") ?? "";
  const [page, setPage] = useState(1);
  const [qInput, setQInput] = useState(q);

  const filters = {
    q,
    journal,
    status,
    confidence,
    business_rule,
    recovery_rule,
    warning,
    validation,
    dtd_result,
  };

  const { data, loading, error } = useApi(
    useCallback(() => api.getArticles(selectedBatchId, filters), [selectedBatchId, JSON.stringify(filters)]),
    [selectedBatchId, JSON.stringify(filters)],
  );

  const businessRules = useApi(
    useCallback(() => api.getBusinessRuleStats(selectedBatchId), [selectedBatchId]),
    [selectedBatchId],
  );
  const recoveryRules = useApi(
    useCallback(() => api.getRecoveryRuleStats(selectedBatchId), [selectedBatchId]),
    [selectedBatchId],
  );
  const warnings = useApi(
    useCallback(() => api.getWarningStats(selectedBatchId), [selectedBatchId]),
    [selectedBatchId],
  );

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
    setPage(1);
  };

  const journals = useMemo(() => [...new Set((data ?? []).map((a) => a.journal))].sort(), [data]);
  const paged = useMemo(() => {
    if (!data) return [];
    return data.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  }, [data, page]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>
            <ShieldCheck size={20} /> Migration Audit
          </h1>
          <p className="subtitle">
            Filter the corpus, then open any article's complete Migration Audit Report.
          </p>
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setFilter("q", qInput);
        }}
        className="search-row"
      >
        <div className="search-with-icon search-input">
          <Search size={14} />
          <input
            placeholder="Search article id, journal, status, business/recovery rule, warning..."
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
          />
        </div>
        <button className="button" type="submit">
          Search
        </button>
      </form>

      <div className="filter-row">
        <select value={journal} onChange={(e) => setFilter("journal", e.target.value)}>
          <option value="">All journals</option>
          {journals.map((j) => (
            <option key={j} value={j}>
              {j}
            </option>
          ))}
        </select>
        <select value={status} onChange={(e) => setFilter("status", e.target.value)}>
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select value={confidence} onChange={(e) => setFilter("confidence", e.target.value)}>
          <option value="">All confidence levels</option>
          {CONFIDENCE_OPTIONS.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select value={business_rule} onChange={(e) => setFilter("business_rule", e.target.value)}>
          <option value="">All Business Rules</option>
          {(businessRules.data ?? []).map((r) => (
            <option key={r.rule_id} value={r.rule_id}>
              {r.rule_id}
            </option>
          ))}
        </select>
        <select value={recovery_rule} onChange={(e) => setFilter("recovery_rule", e.target.value)}>
          <option value="">All Recovery Rules</option>
          {(recoveryRules.data ?? []).map((r) => (
            <option key={r.rule_id} value={r.rule_id}>
              {r.rule_id}
            </option>
          ))}
        </select>
        <select value={warning} onChange={(e) => setFilter("warning", e.target.value)}>
          <option value="">All Warnings</option>
          {(warnings.data ?? []).map((w) => (
            <option key={w.code} value={w.code}>
              {w.code}
            </option>
          ))}
        </select>
        <select value={validation} onChange={(e) => setFilter("validation", e.target.value)}>
          <option value="">All Validation Results</option>
          {RESULT_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <select value={dtd_result} onChange={(e) => setFilter("dtd_result", e.target.value)}>
          <option value="">All DTD Results</option>
          {DTD_RESULT_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>

      {loading && <LoadingState label="Loading articles..." />}
      {error && <ErrorState message={error} />}
      {data && data.length === 0 && (
        <EmptyState title="No articles match" description="Try clearing your filters." />
      )}
      {data && data.length > 0 && (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Article</th>
                  <th>Journal</th>
                  <th>Status</th>
                  <th>Confidence</th>
                  <th>Warnings</th>
                  <th>Recoveries</th>
                  <th>Category</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {paged.map((a) => (
                  <tr key={a.article_id}>
                    <td className="mono">{a.article_id}</td>
                    <td>{a.journal}</td>
                    <td>
                      <StatusBadge status={a.status} />
                    </td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <div className="mini-bar-track">
                          <div
                            className="mini-bar-fill"
                            style={{ width: `${a.confidence_score}%`, background: confidenceColor(a.confidence_score) }}
                          />
                        </div>
                        <span style={{ fontSize: 11.5, color: "var(--text-muted)" }}>{a.confidence_score}%</span>
                      </div>
                    </td>
                    <td>{a.warning_count}</td>
                    <td>{a.recovery_count}</td>
                    <td>{a.category}</td>
                    <td style={{ textAlign: "right" }}>
                      <a
                        href={api.migrationAuditReportViewUrl(selectedBatchId, a.article_id)}
                        target="_blank"
                        rel="noreferrer"
                        className="icon-button"
                        title="Open Migration Audit Report"
                      >
                        <ExternalLink size={14} />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={PAGE_SIZE} total={data.length} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
