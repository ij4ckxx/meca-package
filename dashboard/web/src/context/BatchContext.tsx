import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api";
import type { BatchSummary } from "../types";

interface BatchContextValue {
  batches: BatchSummary[];
  selectedBatchId: string | null;
  latestBatchId: string | null;
  setSelectedBatchId: (id: string | null) => void;
  refreshBatches: () => void;
}

const BatchContext = createContext<BatchContextValue | null>(null);

export function BatchProvider({ children }: { children: ReactNode }) {
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);

  const refreshBatches = useCallback(() => {
    api.getBatches().then(setBatches).catch(() => setBatches([]));
  }, []);

  useEffect(() => {
    refreshBatches();
    const interval = setInterval(refreshBatches, 5000);
    return () => clearInterval(interval);
  }, [refreshBatches]);

  const latestBatchId = batches.length > 0 ? batches[batches.length - 1].batch_id : null;

  return (
    <BatchContext.Provider
      value={{ batches, selectedBatchId, latestBatchId, setSelectedBatchId, refreshBatches }}
    >
      {children}
    </BatchContext.Provider>
  );
}

export function useBatch(): BatchContextValue {
  const ctx = useContext(BatchContext);
  if (!ctx) throw new Error("useBatch must be used within a BatchProvider");
  return ctx;
}

/** The batch id to actually query with: the explicit selection, or null (meaning "latest") if none. */
export function useEffectiveBatchId(): string | null {
  const { selectedBatchId } = useBatch();
  return selectedBatchId;
}
