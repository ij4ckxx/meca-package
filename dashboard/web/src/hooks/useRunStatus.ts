import { useEffect, useState } from "react";
import { api } from "../api";
import type { RunStatus } from "../types";

/** Polls /api/run/status every `intervalMs`. "Polling every few seconds is fine." */
export function useRunStatus(intervalMs = 3000): RunStatus | null {
  const [status, setStatus] = useState<RunStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = () => {
      api
        .getRunStatus()
        .then((s) => {
          if (!cancelled) setStatus(s);
        })
        .catch(() => {
          /* transient — keep showing the last known status */
        });
    };
    poll();
    const interval = setInterval(poll, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [intervalMs]);

  return status;
}
