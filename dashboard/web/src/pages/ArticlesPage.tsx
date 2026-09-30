import { useCallback, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Search, FileText, ChevronRight } from "lucide-react";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import { StatusBadge } from "../components/StatusBadge";
import { useBatch } from "../context/BatchContext";
import { LoadingState, ErrorState, EmptyState } from "../components/States";
import { Pagination } from "../components/Pagination";
import { ExportMenu } from "../components/ExportMenu";
import { confidenceColor } from "../utils/confidence";

const STATUS_OPTIONS = [
  "certified",
  "certified_with_warnings",
  "certified_with_recovery",
  "partial_certification",
  "engine_failure",
  "fatal_failure",
];
const CONFIDENCE_OPTIONS = ["low", "medium", "high"];
const PAGE_SIZE = 15;

export function ArticlesPage() {
  const { selectedBatchId } = useBatch();
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const journal = searchParams.get("journal") ?? "";
  const status = searchParams.get("status") ?? "";
  const confidence = searchParams.get("confidence") ?? "";
  const [page, setPage] = useState(1);

  const [qInput, setQInput] = useState(q);

  const { data, loading, error } = useApi(
    useCallback(
      () => api.getArticles(selectedBatchId, { q, journal, status, confidence }),
      [selectedBatchId, q, journal, status, confidence],
    ),
    [selectedBatchId, q, journal, status, confidence],
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
            <FileText size={20} /> Articles
          </h1>
          {data && <p className="subtitle">{data.length} article(s) matched</p>}
        </div>
        {data && data.length > 0 && (
          <ExportMenu
            rows={data}
            columns={[
              { key: "article_id", label: "Article ID" },
              { key: "journal", label: "Journal" },
              { key: "status", label: "Status" },
              { key: "confidence_score", label: "Confidence" },
              { key: "warning_count", label: "Warnings" },
              { key: "recovery_count", label: "Recoveries" },
              { key: "category", label: "Category" },
            ]}
            baseFilename="articles"
            title="Articles"
          />
        )}
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
            placeholder="Search article id, DOI, journal, status, business/recovery rule, warning..."
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
      </div>

      {loading && <LoadingState label="Loading articles..." />}
      {error && <ErrorState message={error} />}
      {data && data.length === 0 && <EmptyState title="No articles match" description="Try clearing your filters." />}
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
                      <Link
                        to={`/articles/${encodeURIComponent(a.article_id)}`}
                        className="icon-button"
                        aria-label={`Open ${a.article_id}`}
                      >
                        <ChevronRight size={15} />
                      </Link>
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
