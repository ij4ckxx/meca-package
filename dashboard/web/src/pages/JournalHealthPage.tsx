import { useCallback, useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Minus, HeartPulse } from "lucide-react";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import { useBatch } from "../context/BatchContext";
import { LoadingState, ErrorState } from "../components/States";
import type { JournalStats } from "../types";

function Trend({ current, previous }: { current: number; previous: number | undefined }) {
  if (previous == null) return <Minus size={14} color="var(--text-faint)" />;
  if (current > previous) return <TrendingUp size={14} color="var(--success)" />;
  if (current < previous) return <TrendingDown size={14} color="var(--danger)" />;
  return <Minus size={14} color="var(--text-faint)" />;
}

export function JournalHealthPage() {
  const { selectedBatchId, batches } = useBatch();
  const { data, loading, error } = useApi(
    useCallback(() => api.getJournals(selectedBatchId), [selectedBatchId]),
    [selectedBatchId],
  );
  const [previous, setPrevious] = useState<JournalStats[] | null>(null);

  useEffect(() => {
    const currentId = selectedBatchId ?? (batches.length > 0 ? batches[batches.length - 1].batch_id : null);
    const index = batches.findIndex((b) => b.batch_id === currentId);
    if (index > 0) {
      api.getJournals(batches[index - 1].batch_id).then(setPrevious).catch(() => setPrevious(null));
    } else {
      setPrevious(null);
    }
  }, [selectedBatchId, batches]);

  if (loading) return <LoadingState label="Loading journal health..." />;
  if (error) return <ErrorState message={error} />;
  if (!data) return null;

  return (
    <div>
      <h1>
        <HeartPulse size={20} /> Journal Health
      </h1>
      <p className="subtitle">Reused directly from the engine's intelligence output — nothing recomputed here.</p>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Journal</th>
              <th>Total Articles</th>
              <th>Avg. Confidence</th>
              <th>Trend</th>
              <th>Recoveries</th>
              <th>Warnings</th>
              <th>Manual Review</th>
              <th>Common Recovery Rule</th>
              <th>Common Warning</th>
            </tr>
          </thead>
          <tbody>
            {data.map((j) => {
              const prev = previous?.find((p) => p.journal === j.journal);
              return (
                <tr key={j.journal}>
                  <td>{j.journal}</td>
                  <td>{j.article_count}</td>
                  <td>{j.average_confidence_score.toFixed(1)}</td>
                  <td>
                    <Trend current={j.average_confidence_score} previous={prev?.average_confidence_score} />
                  </td>
                  <td>{Object.values(j.recovery_rule_counts).reduce((s, v) => s + v, 0)}</td>
                  <td>{j.total_warnings}</td>
                  <td>{j.status_counts.partial_certification ?? 0}</td>
                  <td>{j.common_recovery_rule ?? "—"}</td>
                  <td title={j.most_common_warning ?? undefined}>
                    {j.most_common_warning ? j.most_common_warning.slice(0, 28) + (j.most_common_warning.length > 28 ? "…" : "") : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
