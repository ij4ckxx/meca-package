import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Activity, Play, Pause, StepForward, XCircle, RefreshCw, ShieldAlert, ClipboardList } from "lucide-react";
import { api } from "../api";
import { useRunStatus } from "../hooks/useRunStatus";
import { useBatch } from "../context/BatchContext";
import type { SummaryStats } from "../types";

function formatSeconds(seconds: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes}m ${rest}s`;
}

function formatTimestamp(iso: string | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

export function ControlCenterPage() {
  const runStatus = useRunStatus();
  const { refreshBatches } = useBatch();
  const [liveSummary, setLiveSummary] = useState<SummaryStats | null>(null);
  const [busy, setBusy] = useState(false);
  const [logLines, setLogLines] = useState<string[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  const activeBatchId = runStatus?.batchId ?? null;
  const isActive = runStatus?.phase === "running" || runStatus?.phase === "starting";
  const live = runStatus?.liveStatus ?? null;

  useEffect(() => {
    if (!activeBatchId) {
      setLiveSummary(null);
      return;
    }
    let cancelled = false;
    const poll = () => api.getSummary(activeBatchId).then((s) => !cancelled && setLiveSummary(s)).catch(() => undefined);
    poll();
    const interval = setInterval(poll, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [activeBatchId]);

  useEffect(() => {
    let cancelled = false;
    const poll = () => api.getRunLogs().then((l) => !cancelled && setLogLines(l.slice(-8))).catch(() => undefined);
    poll();
    const interval = setInterval(poll, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [logLines]);

  const run = useCallback(
    async (label: string, action: () => Promise<unknown>) => {
      setBusy(true);
      try {
        await action();
        toast.success(label);
        refreshBatches();
      } catch (err) {
        toast.error(err instanceof Error ? err.message : String(err));
      } finally {
        setBusy(false);
      }
    },
    [refreshBatches],
  );

  const waiting = !runStatus || runStatus.phase === "idle";
  const jobState = waiting
    ? "Waiting"
    : runStatus.phase === "starting"
      ? "Starting"
      : runStatus.liveStatus?.state === "processing"
        ? "Processing"
        : runStatus.liveStatus?.state === "completed"
          ? "Completed"
          : runStatus.liveStatus?.state === "stopped"
            ? "Stopped"
            : runStatus.liveStatus?.state === "cancelled"
              ? "Cancelled"
              : "Idle";

  const progressPct = live && live.total > 0 ? Math.round((live.completed / live.total) * 100) : 0;
  const succeeded = liveSummary?.category_counts.uploaded ?? 0;
  const manualReview = liveSummary?.category_counts.manual_review ?? 0;
  const failed = liveSummary?.category_counts.failed ?? 0;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>
            <Activity size={22} /> Control Center
          </h1>
          <p className="subtitle">Live batch execution &amp; operator controls</p>
        </div>
        {isActive && (
          <span className="live-pill">
            <span className="live-pill-dot live-pill-dot-pulse" />
            LIVE &middot; {jobState.toUpperCase()}
          </span>
        )}
      </div>

      <div className="run-card">
        <div className="run-card-header">
          <div>
            <div className="run-card-label">{waiting ? "Status" : "Currently Processing"}</div>
            <div className="run-card-article mono">{live?.current_article_id ?? jobState}</div>
          </div>
          <div className="button-row" style={{ marginBottom: 0 }}>
            <button
              className="button"
              disabled={busy || isActive}
              onClick={() => run("Migration started", () => api.startRun())}
            >
              <Play size={14} /> Start Migration
            </button>
            <button
              className="button button-secondary"
              disabled={busy || !isActive || runStatus?.paused}
              onClick={() => run("Paused", () => api.pauseRun())}
            >
              <Pause size={14} /> Pause
            </button>
            <button
              className="button button-secondary"
              disabled={busy || !isActive || !runStatus?.paused}
              onClick={() => run("Resumed", () => api.resumeRun())}
            >
              <Play size={14} /> Resume
            </button>
            <button
              className="button button-secondary"
              disabled={busy || !isActive}
              onClick={() => run("Will stop after the current article", () => api.stopAfterCurrent())}
            >
              <StepForward size={14} /> Stop After Current
            </button>
            <button
              className="button button-danger"
              disabled={busy || !isActive}
              onClick={() => run("Batch cancelled", () => api.cancelRun())}
            >
              <XCircle size={14} /> Cancel
            </button>
          </div>
        </div>

        {live && (
          <div>
            <div className="progress-row">
              <span>
                {live.completed} of {live.total} articles &middot;{" "}
                {formatSeconds(live.estimated_remaining_seconds)} remaining
              </span>
              <span style={{ fontWeight: 700, color: "var(--text)" }}>{progressPct}%</span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${progressPct}%` }} />
            </div>
          </div>
        )}

        <div className="run-stat-row">
          <div className="run-stat">
            <span className="run-stat-value">{live?.completed ?? 0}</span>
            <span className="run-stat-label">Processed</span>
          </div>
          <div className="run-stat">
            <span className="run-stat-value" style={{ color: "var(--success)" }}>
              {succeeded}
            </span>
            <span className="run-stat-label">Succeeded</span>
          </div>
          <div className="run-stat">
            <span className="run-stat-value" style={{ color: "var(--warning)" }}>
              {manualReview}
            </span>
            <span className="run-stat-label">Manual Review</span>
          </div>
          <div className="run-stat">
            <span className="run-stat-value" style={{ color: "var(--danger)" }}>
              {failed}
            </span>
            <span className="run-stat-label">Failed</span>
          </div>
          <div className="run-stat">
            <span className="run-stat-value">
              {live?.articles_per_second ? `${live.articles_per_second.toFixed(2)}/s` : "—"}
            </span>
            <span className="run-stat-label">Throughput</span>
          </div>
        </div>
      </div>

      <div className="console-grid">
        <div className="live-log-panel">
          <div className="live-log-header">
            <span className="live-log-title">LIVE LOG</span>
            <span className="live-pill-dot" style={{ background: isActive ? "#34d399" : "#4b5163" }} />
          </div>
          <div className="live-log-lines" ref={logRef}>
            {logLines.length === 0 && <span style={{ color: "#5b6178" }}>No log output yet.</span>}
            {logLines.map((line, i) => (
              <div className="live-log-line" key={i}>
                {line}
              </div>
            ))}
          </div>
        </div>

        <div className="batch-info-panel">
          <h3 style={{ margin: 0, fontSize: 13 }}>Batch Info</h3>
          <div className="batch-info-row">
            <span className="batch-info-row-label">Batch ID</span>
            <span className="batch-info-row-value mono">{activeBatchId ?? "—"}</span>
          </div>
          <div className="batch-info-row">
            <span className="batch-info-row-label">Phase</span>
            <span className="batch-info-row-value">{jobState}</span>
          </div>
          <div className="batch-info-row">
            <span className="batch-info-row-label">Started At</span>
            <span className="batch-info-row-value">{formatTimestamp(live?.started_at)}</span>
          </div>
          <div className="batch-info-row">
            <span className="batch-info-row-label">Elapsed</span>
            <span className="batch-info-row-value">{formatSeconds(live?.elapsed_seconds ?? null)}</span>
          </div>
          {runStatus?.exitCode != null && (
            <div className="batch-info-row">
              <span className="batch-info-row-label">Exit Code</span>
              <span
                className="batch-info-row-value"
                style={{ color: runStatus.exitCode === 0 ? "var(--success)" : "var(--danger)" }}
              >
                {runStatus.exitCode}
              </span>
            </div>
          )}
        </div>
      </div>

      <h2>Restart</h2>
      <div className="button-row">
        <button
          className="button button-secondary"
          disabled={busy || isActive}
          onClick={() => run("Restarting failed articles", () => api.restartFailed(null))}
        >
          <ShieldAlert size={14} /> Restart Failed Articles
        </button>
        <button
          className="button button-secondary"
          disabled={busy || isActive}
          onClick={() => run("Restarting manual-review articles", () => api.restartManualReview(null))}
        >
          <ClipboardList size={14} /> Restart Manual Review Articles
        </button>
      </div>
      {runStatus?.exitCode != null && runStatus.exitCode !== 0 && (
        <p className="error">
          <RefreshCw size={14} /> Last run exited with code {runStatus.exitCode} — check the Logs page.
        </p>
      )}
    </div>
  );
}
