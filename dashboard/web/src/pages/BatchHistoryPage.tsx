import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, FileDown, History } from "lucide-react";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import { useBatch } from "../context/BatchContext";
import { LoadingState, ErrorState, EmptyState } from "../components/States";

const REPORT_FILES = [
  { file: "Migration_Summary.html", label: "Migration Summary" },
  { file: "Recovery_Analytics.md", label: "Recovery Analytics" },
  { file: "Business_Rule_Statistics.md", label: "Business Rule Statistics" },
  { file: "Journal_Health_Report.html", label: "Journal Health Report" },
  { file: "Archive_Audit.csv", label: "Archive Audit (CSV)" },
  { file: "Manual_Review.csv", label: "Manual Review (CSV)" },
  { file: "migration_dashboard.json", label: "Dashboard JSON" },
];

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return minutes > 0 ? `${minutes}m ${rest}s` : `${rest}s`;
}

export function BatchHistoryPage() {
  const { setSelectedBatchId } = useBatch();
  const navigate = useNavigate();
  const { data, loading, error } = useApi(useCallback(() => api.getBatches(), []));

  if (loading) return <LoadingState label="Loading batch history..." />;
  if (error) return <ErrorState message={error} />;
  if (!data || data.length === 0) {
    return (
      <div>
        <h1>
          <History size={20} /> Batch History
        </h1>
        <EmptyState title="No migrations run yet" description="Start a migration from the Control Center." />
      </div>
    );
  }

  const latestBatchId = data[data.length - 1]?.batch_id;

  const view = (batchId: string) => {
    setSelectedBatchId(batchId);
    navigate("/home");
  };

  return (
    <div>
      <h1>
        <History size={20} /> Batch History
      </h1>
      <p className="subtitle">Every migration run, newest first. Select one to view it across the whole dashboard.</p>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Batch ID</th>
              <th>Date</th>
              <th>Time</th>
              <th>Packages</th>
              <th>Success</th>
              <th>Recovery</th>
              <th>Manual Review</th>
              <th>Failed</th>
              <th>Duration</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {[...data].reverse().map((b) => {
              const date = new Date(b.created_at);
              return (
                <tr key={b.batch_id}>
                  <td className="mono">
                    {b.batch_id}
                    {b.batch_id === latestBatchId && (
                      <span className="badge badge-blue" style={{ marginLeft: 8 }}>
                        Latest
                      </span>
                    )}
                  </td>
                  <td>{date.toLocaleDateString()}</td>
                  <td>{date.toLocaleTimeString()}</td>
                  <td>{b.total}</td>
                  <td style={{ color: "var(--success)", fontWeight: 600 }}>{b.success}</td>
                  <td style={{ color: "var(--accent)", fontWeight: 600 }}>{b.recovery}</td>
                  <td style={{ color: "var(--warning)", fontWeight: 600 }}>{b.manual_review}</td>
                  <td style={{ color: b.failed > 0 ? "var(--danger)" : "var(--text-faint)", fontWeight: 600 }}>
                    {b.failed}
                  </td>
                  <td>{formatDuration(b.duration_seconds)}</td>
                  <td>
                    <button className="icon-button" onClick={() => view(b.batch_id)} title="View this batch">
                      <Eye size={14} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <h2>
        <FileDown size={16} /> Downloads (latest batch)
      </h2>
      <div className="button-row">
        {REPORT_FILES.map((r) => (
          <a key={r.file} className="button button-secondary" href={api.reportFileDownloadUrl(null, r.file)}>
            {r.label}
          </a>
        ))}
      </div>
    </div>
  );
}
