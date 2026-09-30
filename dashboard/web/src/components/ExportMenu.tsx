import { useState, useRef, useEffect } from "react";
import { Download, ChevronDown } from "lucide-react";
import { exportCsv, exportJson, exportPdf, type ExportColumn } from "../exportUtils";

interface ExportMenuProps<T> {
  rows: T[];
  columns: ExportColumn<T>[];
  baseFilename: string;
  title: string;
}

export function ExportMenu<T>({ rows, columns, baseFilename, title }: ExportMenuProps<T>) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div style={{ position: "relative", display: "inline-block" }} ref={ref}>
      <button className="button button-secondary" onClick={() => setOpen((o) => !o)}>
        <Download size={14} /> Export <ChevronDown size={14} />
      </button>
      {open && (
        <div
          className="panel"
          style={{
            position: "absolute",
            top: "110%",
            right: 0,
            zIndex: 10,
            padding: 6,
            minWidth: 140,
            marginBottom: 0,
          }}
        >
          <button
            className="nav-link"
            style={{ color: "var(--text)", width: "100%" }}
            onClick={() => {
              exportCsv(rows, columns, `${baseFilename}.csv`);
              setOpen(false);
            }}
          >
            CSV / Excel
          </button>
          <button
            className="nav-link"
            style={{ color: "var(--text)", width: "100%" }}
            onClick={() => {
              exportJson(rows, `${baseFilename}.json`);
              setOpen(false);
            }}
          >
            JSON
          </button>
          <button
            className="nav-link"
            style={{ color: "var(--text)", width: "100%" }}
            onClick={() => {
              exportPdf(rows, columns, `${baseFilename}.pdf`, title);
              setOpen(false);
            }}
          >
            PDF
          </button>
        </div>
      )}
    </div>
  );
}
