import { useCallback, useEffect, useState } from "react";
import { GitCompare, ArrowRight } from "lucide-react";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import { LoadingState, ErrorState } from "../components/States";
import type { JournalStats, RecoveryRuleStats, SummaryStats, WarningStats } from "../types";

interface BatchDataset {
  summary: SummaryStats;
  journals: JournalStats[];
  recoveryRules: RecoveryRuleStats[];
  warnings: WarningStats[];
}

const STATUS_KEYS = [
  "certified",
  "certified_with_warnings",
  "certified_with_recovery",
  "partial_certification",
  "engine_failure",
  "fatal_failure",
];

const STATUS_LABELS: Record<string, string> = {
  certified: "Certified",
  certified_with_warnings: "Certified w/ Warnings",
  certified_with_recovery: "Certified w/ Recovery",
  partial_certification: "Partial Certification",
  engine_failure: "Engine Failures",
  fatal_failure: "Fatal Failures",
};

const NEGATIVE_STATUS_KEYS = new Set(["engine_failure", "fatal_failure"]);

function useBatchDataset(batchId: string | null): { data: BatchDataset | null; loading: boolean } {
  const [data, setData] = useState<BatchDataset | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!batchId) {
      setData(null);
      return;
    }
    setLoading(true);
    Promise.all([
      api.getSummary(batchId),
      api.getJournals(batchId),
      api.getRecoveryRuleStats(batchId),
      api.getWarningStats(batchId),
    ])
      .then(([summary, journals, recoveryRules, warnings]) =>
        setData({ summary, journals, recoveryRules, warnings }),
      )
      .finally(() => setLoading(false));
  }, [batchId]);

  return { data, loading };
}

function DiffPill({
  a,
  b,
  invert = false,
  neutral = false,
}: {
  a: number;
  b: number;
  invert?: boolean;
  neutral?: boolean;
}) {
  const delta = b - a;
  const improved = invert ? delta < 0 : delta > 0;
  const cls = neutral || delta === 0 ? "diff-pill-neutral" : improved ? "diff-pill-positive" : "diff-pill-negative";
  const text = delta > 0 ? `+${delta}` : delta === 0 ? "±0" : `${delta}`;
  return <span className={`diff-pill ${cls}`}>{text}</span>;
}

function deltaValue(a: number, b: number, invert: boolean): { text: string; color: string } {
  const delta = b - a;
  const improved = invert ? delta < 0 : delta > 0;
  const color = delta === 0 ? "var(--text-faint)" : improved ? "var(--success)" : "var(--danger)";
  const text = delta > 0 ? `+${delta}` : delta === 0 ? "±0" : `${delta}`;
  return { text, color };
}

export function BatchComparisonPage() {
  const { data: batches, loading: batchesLoading, error } = useApi(useCallback(() => api.getBatches(), []));
  const [batchA, setBatchA] = useState<string>("");
  const [batchB, setBatchB] = useState<string>("");

  useEffect(() => {
    if (batches && batches.length >= 2 && !batchA && !batchB) {
      setBatchA(batches[batches.length - 2].batch_id);
      setBatchB(batches[batches.length - 1].batch_id);
    } else if (batches && batches.length === 1 && !batchA) {
      setBatchA(batches[0].batch_id);
      setBatchB(batches[0].batch_id);
    }
  }, [batches, batchA, batchB]);

  const a = useBatchDataset(batchA || null);
  const b = useBatchDataset(batchB || null);

  if (batchesLoading) return <LoadingState label="Loading batches..." />;
  if (error) return <ErrorState message={error} />;
  if (!batches || batches.length < 2) {
    return (
      <div>
        <h1>
          <GitCompare size={20} /> Batch Comparison
        </h1>
        <p className="subtitle">Run at least 2 migrations to compare them.</p>
      </div>
    );
  }

  const durationA = batches.find((batch) => batch.batch_id === batchA)?.duration_seconds ?? null;
  const durationB = batches.find((batch) => batch.batch_id === batchB)?.duration_seconds ?? null;
  const totalA = a.data ? Object.values(a.data.summary.status_counts).reduce((s, v) => s + v, 0) : 0;
  const totalB = b.data ? Object.values(b.data.summary.status_counts).reduce((s, v) => s + v, 0) : 0;

  return (
    <div>
      <h1>
        <GitCompare size={20} /> Batch Comparison
      </h1>
      <p className="subtitle">See exactly what changed between two runs.</p>

      <div className="batch-vs-row">
        <select value={batchA} onChange={(e) => setBatchA(e.target.value)}>
          {batches.map((batch) => (
            <option key={batch.batch_id} value={batch.batch_id}>
              {batch.batch_id}
            </option>
          ))}
        </select>
        <ArrowRight size={16} color="var(--text-faint)" />
        <select value={batchB} onChange={(e) => setBatchB(e.target.value)}>
          {batches.map((batch) => (
            <option key={batch.batch_id} value={batch.batch_id}>
              {batch.batch_id}
            </option>
          ))}
        </select>
      </div>

      {(a.loading || b.loading) && <LoadingState label="Comparing..." />}

      {a.data && b.data && (
        <>
          <div className="compare-grid">
            <div className="compare-card">
              <div className="compare-card-header">
                <span className="mono" style={{ fontWeight: 700, fontSize: 13 }}>
                  Batch A
                </span>
                <span style={{ fontSize: 10.5, color: "var(--text-faint)" }}>{totalA} articles</span>
              </div>
              {STATUS_KEYS.map((key) => (
                <div className="compare-row" key={key}>
                  <span>{STATUS_LABELS[key]}</span>
                  <span>{a.data!.summary.status_counts[key] ?? 0}</span>
                </div>
              ))}
              <div className="compare-row">
                <span>Duration</span>
                <span>{durationA != null ? `${durationA.toFixed(1)}s` : "—"}</span>
              </div>
            </div>

            <div className="compare-delta-col">
              <span className="compare-delta-label">DELTA</span>
              {STATUS_KEYS.map((key) => {
                const { text, color } = deltaValue(
                  a.data!.summary.status_counts[key] ?? 0,
                  b.data!.summary.status_counts[key] ?? 0,
                  NEGATIVE_STATUS_KEYS.has(key),
                );
                return (
                  <div className="compare-delta-value" style={{ color }} key={key}>
                    {text}
                  </div>
                );
              })}
              <div className="compare-delta-value" style={{ color: "var(--text-muted)" }}>
                {durationA != null && durationB != null ? `${(durationB / durationA).toFixed(1)}x` : "—"}
              </div>
            </div>

            <div className="compare-card compare-card-highlight">
              <div className="compare-card-header">
                <span className="mono" style={{ fontWeight: 700, fontSize: 13, color: "var(--accent-hover)" }}>
                  Batch B
                </span>
                <span style={{ fontSize: 10.5, color: "var(--text-faint)" }}>{totalB} articles</span>
              </div>
              {STATUS_KEYS.map((key) => (
                <div className="compare-row compare-row-highlight" key={key}>
                  <span>{STATUS_LABELS[key]}</span>
                  <span>{b.data!.summary.status_counts[key] ?? 0}</span>
                </div>
              ))}
              <div className="compare-row compare-row-highlight">
                <span>Duration</span>
                <span>{durationB != null ? `${durationB.toFixed(1)}s` : "—"}</span>
              </div>
            </div>
          </div>

          <h2>Confidence Differences</h2>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Confidence</th>
                  <th>Batch A</th>
                  <th>Batch B</th>
                  <th>Delta</th>
                </tr>
              </thead>
              <tbody>
                {["low", "medium", "high"].map((key) => (
                  <tr key={key}>
                    <td style={{ textTransform: "capitalize" }}>{key}</td>
                    <td>{a.data!.summary.confidence_distribution[key] ?? 0}</td>
                    <td>{b.data!.summary.confidence_distribution[key] ?? 0}</td>
                    <td>
                      <DiffPill
                        a={a.data!.summary.confidence_distribution[key] ?? 0}
                        b={b.data!.summary.confidence_distribution[key] ?? 0}
                        invert={key === "low"}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2>Journal Differences</h2>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Journal</th>
                  <th>Articles A</th>
                  <th>Articles B</th>
                  <th>Delta</th>
                  <th>Avg. Confidence A</th>
                  <th>Avg. Confidence B</th>
                </tr>
              </thead>
              <tbody>
                {[...new Set([...a.data!.journals.map((j) => j.journal), ...b.data!.journals.map((j) => j.journal)])].map(
                  (journalName) => {
                    const ja = a.data!.journals.find((j) => j.journal === journalName);
                    const jb = b.data!.journals.find((j) => j.journal === journalName);
                    return (
                      <tr key={journalName}>
                        <td>{journalName}</td>
                        <td>{ja?.article_count ?? 0}</td>
                        <td>{jb?.article_count ?? 0}</td>
                        <td>
                          <DiffPill a={ja?.article_count ?? 0} b={jb?.article_count ?? 0} neutral />
                        </td>
                        <td>{ja?.average_confidence_score.toFixed(1) ?? "—"}</td>
                        <td>{jb?.average_confidence_score.toFixed(1) ?? "—"}</td>
                      </tr>
                    );
                  },
                )}
              </tbody>
            </table>
          </div>

          <h2>Recovery Rule Differences</h2>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rule</th>
                  <th>Occurrences A</th>
                  <th>Occurrences B</th>
                  <th>Delta</th>
                </tr>
              </thead>
              <tbody>
                {[...new Set([...a.data!.recoveryRules.map((r) => r.rule_id), ...b.data!.recoveryRules.map((r) => r.rule_id)])].map(
                  (ruleId) => {
                    const ra = a.data!.recoveryRules.find((r) => r.rule_id === ruleId)?.occurrences ?? 0;
                    const rb = b.data!.recoveryRules.find((r) => r.rule_id === ruleId)?.occurrences ?? 0;
                    return (
                      <tr key={ruleId}>
                        <td className="mono">{ruleId}</td>
                        <td>{ra}</td>
                        <td>{rb}</td>
                        <td>
                          <DiffPill a={ra} b={rb} neutral />
                        </td>
                      </tr>
                    );
                  },
                )}
              </tbody>
            </table>
          </div>

          <h2>Warning Differences</h2>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Warning Code</th>
                  <th>Occurrences A</th>
                  <th>Occurrences B</th>
                  <th>Delta</th>
                </tr>
              </thead>
              <tbody>
                {[...new Set([...a.data!.warnings.map((w) => w.code), ...b.data!.warnings.map((w) => w.code)])].map(
                  (code) => {
                    const wa = a.data!.warnings.find((w) => w.code === code)?.occurrences ?? 0;
                    const wb = b.data!.warnings.find((w) => w.code === code)?.occurrences ?? 0;
                    return (
                      <tr key={code}>
                        <td className="mono">{code}</td>
                        <td>{wa}</td>
                        <td>{wb}</td>
                        <td>
                          <DiffPill a={wa} b={wb} invert />
                        </td>
                      </tr>
                    );
                  },
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
