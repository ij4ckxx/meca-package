import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { batchDataRoot } from "./batchStore.js";
import type { ReviewNote, ReviewStatus } from "./types.js";

/**
 * Operator notes for manual-review articles — local JSON only, one file
 * per batch, co-located with that batch's other reports. No database.
 */
function notesPath(batchId: string): string {
  return join(batchDataRoot(batchId), "manual_review_notes.json");
}

export function getNotes(batchId: string): Record<string, ReviewNote> {
  const path = notesPath(batchId);
  if (!existsSync(path)) return {};
  return JSON.parse(readFileSync(path, "utf-8")) as Record<string, ReviewNote>;
}

export function setNote(
  batchId: string,
  articleId: string,
  update: { note?: string; status?: ReviewStatus },
): Record<string, ReviewNote> {
  const notes = getNotes(batchId);
  const existing = notes[articleId] ?? { note: "", status: "pending" as ReviewStatus, updated_at: "" };
  notes[articleId] = {
    note: update.note ?? existing.note,
    status: update.status ?? existing.status,
    updated_at: new Date().toISOString(),
  };
  writeFileSync(notesPath(batchId), JSON.stringify(notes, null, 2));
  return notes;
}
