import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ClipboardCheck, ClipboardX, RotateCcw, RefreshCw, ClipboardList } from "lucide-react";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import { useBatch } from "../context/BatchContext";
import { LoadingState, ErrorState, EmptyState } from "../components/States";
import { ExportMenu } from "../components/ExportMenu";
import { confidenceColor } from "../utils/confidence";
import type { ManualReviewEntry, ReviewStatus } from "../types";

const STATUS_BADGE: Record<ReviewStatus, string> = {
  pending: "badge badge-neutral",
  reviewed: "badge badge-blue",
  accepted: "badge badge-green",
  rejected: "badge badge-red",
};

export function ManualReviewPage() {
  const { selectedBatchId, refreshBatches } = useBatch();
  const { data, loading, error, refetch } = useApi(
    useCallback(() => api.getManualReview(selectedBatchId), [selectedBatchId]),
    [selectedBatchId],
  );
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);

  const restartAll = () => {
    api
      .restartManualReview(selectedBatchId)
      .then(() => {
        toast.success("Restart queued for all manual-review articles");
        refreshBatches();
      })
      .catch((err: unknown) => toast.error(err instanceof Error ? err.message : String(err)));
  };

  const saveNote = async (articleId: string, update: { note?: string; status?: ReviewStatus }) => {
    setBusyId(articleId);
    try {
      await api.setManualReviewNote(selectedBatchId, articleId, update);
      toast.success(update.status ? `Marked ${update.status}` : "Note saved");
      refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <LoadingState label="Loading manual review queue..." />;
  if (error) return <ErrorState message={error} />;
  if (!data) return null;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>
            <ClipboardList size={20} /> Manual Review Workspace
          </h1>
          <p className="subtitle">Articles the engine routed for manual decision, with operator notes stored locally.</p>
        </div>
        {data.length > 0 && (
          <div className="button-row" style={{ marginBottom: 0 }}>
            <ExportMenu
              rows={data}
              columns={[
                { key: "article_id", label: "Article ID" },
                { key: "journal", label: "Journal" },
                { key: "reason", label: "Reason" },
                { key: "confidence_score", label: "Confidence" },
                { key: "status", label: "Status" },
                { key: "note", label: "Note" },
              ]}
              baseFilename="manual-review"
              title="Manual Review Queue"
            />
            <button className="button button-secondary" onClick={restartAll}>
              <RefreshCw size={14} /> Restart All
            </button>
          </div>
        )}
      </div>

      {data.length === 0 && (
        <EmptyState title="Nothing needs manual review" description="Every article in this batch was auto-routed." />
      )}

      {data.map((entry: ManualReviewEntry) => (
        <div className="panel" key={entry.article_id}>
          <div className="page-header" style={{ marginBottom: 8, alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span className="mono" style={{ fontWeight: 700, fontSize: 13.5 }}>
                {entry.article_id}
              </span>
              <span className={STATUS_BADGE[entry.status]}>{entry.status}</span>
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{entry.journal}</span>
            </div>
            <Link to={`/articles/${encodeURIComponent(entry.article_id)}`} className="button button-secondary">
              Open Article →
            </Link>
          </div>
          <p style={{ fontSize: 12.5, margin: "4px 0", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span>
              <strong>Reason:</strong> {entry.reason}
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <strong>Confidence:</strong>
              <span className="mini-bar-track">
                <span
                  className="mini-bar-fill"
                  style={{ display: "block", width: `${entry.confidence_score}%`, background: confidenceColor(entry.confidence_score) }}
                />
              </span>
              {entry.confidence_score}%
            </span>
          </p>
          <textarea
            className="note-textarea"
            placeholder="Operator notes..."
            value={drafts[entry.article_id] ?? entry.note}
            onChange={(e) => setDrafts({ ...drafts, [entry.article_id]: e.target.value })}
          />
          <div className="status-pill-row">
            <button
              className="button button-secondary"
              disabled={busyId === entry.article_id}
              onClick={() => saveNote(entry.article_id, { note: drafts[entry.article_id] ?? entry.note })}
            >
              Save Note
            </button>
            <button
              className="button button-secondary"
              disabled={busyId === entry.article_id}
              onClick={() => saveNote(entry.article_id, { status: "reviewed" })}
            >
              <RotateCcw size={14} /> Mark Reviewed
            </button>
            <button
              className="button button-success"
              disabled={busyId === entry.article_id}
              onClick={() => saveNote(entry.article_id, { status: "accepted" })}
            >
              <ClipboardCheck size={14} /> Mark Accepted
            </button>
            <button
              className="button button-danger"
              disabled={busyId === entry.article_id}
              onClick={() => saveNote(entry.article_id, { status: "rejected" })}
            >
              <ClipboardX size={14} /> Mark Rejected
            </button>
            <a className="button button-secondary" href={api.zipDownloadUrl(selectedBatchId, entry.article_id)}>
              Download ZIP
            </a>
          </div>
        </div>
      ))}
    </div>
  );
}
