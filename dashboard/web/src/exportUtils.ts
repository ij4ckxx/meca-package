import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";

export interface ExportColumn<T> {
  key: keyof T;
  label: string;
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function csvEscape(value: unknown): string {
  const text = value == null ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function exportCsv<T>(rows: T[], columns: ExportColumn<T>[], filename: string): void {
  const header = columns.map((c) => csvEscape(c.label)).join(",");
  const lines = rows.map((row) => columns.map((c) => csvEscape(row[c.key])).join(","));
  const blob = new Blob([[header, ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
  triggerDownload(blob, filename);
}

export function exportJson<T>(rows: T[], filename: string): void {
  const blob = new Blob([JSON.stringify(rows, null, 2)], { type: "application/json" });
  triggerDownload(blob, filename);
}

export function exportPdf<T>(
  rows: T[],
  columns: ExportColumn<T>[],
  filename: string,
  title: string,
): void {
  const doc = new jsPDF({ orientation: "landscape" });
  doc.setFontSize(14);
  doc.text(title, 14, 16);
  autoTable(doc, {
    startY: 22,
    head: [columns.map((c) => c.label)],
    body: rows.map((row) => columns.map((c) => String(row[c.key] ?? ""))),
    styles: { fontSize: 8 },
    headStyles: { fillColor: [47, 111, 235] },
  });
  doc.save(filename);
}
