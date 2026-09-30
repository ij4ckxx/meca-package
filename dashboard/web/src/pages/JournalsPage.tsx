import { useCallback } from "react";
import { BookOpen } from "lucide-react";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import { useBatch } from "../context/BatchContext";
import { LoadingState, ErrorState } from "../components/States";

export function JournalsPage() {
  const { selectedBatchId } = useBatch();
  const { data, loading, error } = useApi(
    useCallback(() => api.getJournals(selectedBatchId), [selectedBatchId]),
    [selectedBatchId],
  );

  if (loading) return <LoadingState label="Loading journals..." />;
  if (error) return <ErrorState message={error} />;
  if (!data) return null;

  return (
    <div>
      <h1>
        <BookOpen size={20} /> Per Journal
      </h1>
      <p className="subtitle">{data.length} journal(s) in this batch.</p>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Journal</th>
              <th>Articles</th>
              <th>Recovery Rate</th>
              <th>Common Recovery Rule</th>
              <th>Warnings</th>
              <th>Avg. Confidence</th>
            </tr>
          </thead>
          <tbody>
            {data.map((j) => (
              <tr key={j.journal}>
                <td>{j.journal}</td>
                <td>{j.article_count}</td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <div className="mini-bar-track">
                      <div
                        className="mini-bar-fill"
                        style={{ width: `${Math.round(j.recovery_rate * 100)}%`, background: "var(--accent)" }}
                      />
                    </div>
                    <span style={{ fontSize: 11.5, color: "var(--text-muted)" }}>
                      {Math.round(j.recovery_rate * 100)}%
                    </span>
                  </div>
                </td>
                <td className="mono">{j.common_recovery_rule ?? "—"}</td>
                <td>{j.total_warnings}</td>
                <td>{j.average_confidence_score.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
