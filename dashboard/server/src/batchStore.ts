import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { BATCHES_ROOT } from "./paths.js";

export interface BatchInfo {
  batch_id: string;
  created_at: string;
}

export function listBatches(): BatchInfo[] {
  if (!existsSync(BATCHES_ROOT)) return [];
  return readdirSync(BATCHES_ROOT)
    .filter((name) => statSync(join(BATCHES_ROOT, name)).isDirectory())
    .sort()
    .map((batch_id) => ({
      batch_id,
      created_at: statSync(join(BATCHES_ROOT, batch_id)).birthtime.toISOString(),
    }));
}

/** The most recently created batch id, or null if no batch has ever run. */
export function latestBatchId(): string | null {
  const batches = listBatches();
  return batches.length > 0 ? batches[batches.length - 1].batch_id : null;
}

export function resolveBatchId(requested: string | undefined): string | null {
  if (!requested || requested === "latest") return latestBatchId();
  // RC-1 security review: `requested` comes straight from a URL query
  // param (?batch=...) and every downstream path (batchDataRoot,
  // batchPackagesRoot, ...) joins it directly onto BATCHES_ROOT with no
  // further sanitization — an unvalidated value here (e.g.
  // "../../../../etc") is a directory-escape/path-traversal
  // vulnerability. Only ever return a value that is a real, existing
  // batch directory name.
  const isRealBatch = listBatches().some((b) => b.batch_id === requested);
  return isRealBatch ? requested : null;
}

export function batchDataRoot(batchId: string): string {
  return join(BATCHES_ROOT, batchId, "reports");
}

export function batchPackagesRoot(batchId: string): string {
  return join(BATCHES_ROOT, batchId, "generated_packages");
}

/** Final elapsed seconds from the batch's live-status file, if it ever ran. */
export function getBatchDuration(batchId: string): number | null {
  const path = join(BATCHES_ROOT, batchId, "live_status.json");
  if (!existsSync(path)) return null;
  const status = JSON.parse(readFileSync(path, "utf-8")) as { elapsed_seconds?: number };
  return status.elapsed_seconds ?? null;
}

const REPORT_FILE_ALLOWLIST = new Set([
  "Migration_Summary.html",
  "Recovery_Analytics.md",
  "Business_Rule_Statistics.md",
  "Journal_Health_Report.html",
  "Archive_Audit.csv",
  "Manual_Review.csv",
  "migration_dashboard.json",
  "dashboard_intelligence.json",
  "conversion_reports.json",
  "Business_Rule_Effectiveness.md",
  "Recovery_Rule_Effectiveness.md",
  "Warning_Frequency.md",
  "Confidence_Analysis.md",
  "Recommendations.md",
  "Migration_Trends.json",
  "Migration_Intelligence_Report.html",
]);

/** Resolves a named generated report to its path, rejecting anything not on the allowlist. */
export function resolveReportFile(batchId: string, filename: string): string | null {
  if (!REPORT_FILE_ALLOWLIST.has(filename)) return null;
  const path = join(batchDataRoot(batchId), filename);
  return existsSync(path) ? path : null;
}

export function listAvailableReportFiles(batchId: string): string[] {
  const dir = batchDataRoot(batchId);
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter((name) => REPORT_FILE_ALLOWLIST.has(name));
}
