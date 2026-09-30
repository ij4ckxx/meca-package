import { ChevronDown } from "lucide-react";
import { useBatch } from "../context/BatchContext";

export function BatchSelector() {
  const { batches, selectedBatchId, latestBatchId, setSelectedBatchId } = useBatch();

  if (batches.length === 0) {
    return <span className="topbar-batch-empty">No migrations run yet</span>;
  }

  return (
    <div className="topbar-batch-selector">
      <span className="topbar-batch-label">Batch</span>
      <select value={selectedBatchId ?? ""} onChange={(e) => setSelectedBatchId(e.target.value || null)}>
        <option value="">Latest{latestBatchId ? ` (${latestBatchId})` : ""}</option>
        {[...batches].reverse().map((b) => (
          <option key={b.batch_id} value={b.batch_id}>
            {b.batch_id}
          </option>
        ))}
      </select>
      <ChevronDown size={12} />
    </div>
  );
}
