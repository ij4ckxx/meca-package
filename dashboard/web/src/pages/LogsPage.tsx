import { useEffect, useMemo, useRef, useState } from "react";
import { Download, ChevronsDown, ChevronsUp, ScrollText, Search } from "lucide-react";
import { api } from "../api";

type Severity = "all" | "error" | "warn" | "info";

function classify(line: string): Exclude<Severity, "all"> {
  const lower = line.toLowerCase();
  if (lower.includes('"level":"error"') || lower.includes(" error")) return "error";
  if (lower.includes('"level":"warning"') || lower.includes(" warn")) return "warn";
  return "info";
}

export function LogsPage() {
  const [lines, setLines] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState<Severity>("all");
  const [collapsed, setCollapsed] = useState(false);
  const boxRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = () => api.getRunLogs().then((l) => !cancelled && setLines(l)).catch(() => undefined);
    poll();
    const interval = setInterval(poll, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const counts = useMemo(() => {
    const c = { error: 0, warn: 0, info: 0 };
    for (const line of lines) c[classify(line)] += 1;
    return c;
  }, [lines]);

  const filtered = useMemo(() => {
    return lines.filter((line) => {
      if (severity !== "all" && classify(line) !== severity) return false;
      if (query && !line.toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    });
  }, [lines, query, severity]);

  useEffect(() => {
    if (!collapsed) boxRef.current?.scrollTo({ top: boxRef.current.scrollHeight });
  }, [filtered, collapsed]);

  const download = () => {
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `service-log-${new Date().toISOString()}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>
            <ScrollText size={20} /> Service Log
          </h1>
          <p className="subtitle">Live output from the currently or most recently run migration.</p>
        </div>
        <div className="button-row" style={{ marginBottom: 0 }}>
          <button className="button button-secondary" onClick={() => setCollapsed((c) => !c)}>
            {collapsed ? <ChevronsDown size={14} /> : <ChevronsUp size={14} />}
            {collapsed ? "Expand" : "Collapse"}
          </button>
          <button className="button button-secondary" onClick={download}>
            <Download size={14} /> Download
          </button>
        </div>
      </div>

      <div className="filter-row">
        <div className="search-with-icon search-input">
          <Search size={14} />
          <input placeholder="Search logs..." value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <button
          className={`badge ${severity === "all" ? "badge-blue" : "badge-neutral"}`}
          onClick={() => setSeverity("all")}
        >
          All &middot; {lines.length}
        </button>
        <button
          className={`badge ${severity === "info" ? "badge-blue" : "badge-neutral"}`}
          onClick={() => setSeverity("info")}
        >
          Info &middot; {counts.info}
        </button>
        <button
          className={`badge ${severity === "warn" ? "badge-yellow" : "badge-neutral"}`}
          onClick={() => setSeverity("warn")}
        >
          Warning &middot; {counts.warn}
        </button>
        <button
          className={`badge ${severity === "error" ? "badge-red" : "badge-neutral"}`}
          onClick={() => setSeverity("error")}
        >
          Error &middot; {counts.error}
        </button>
      </div>

      {!collapsed && (
        <pre className="log-box" ref={boxRef}>
          {filtered.length === 0 && "No log output matches."}
          {filtered.map((line, i) => {
            const sev = classify(line);
            const cls = sev === "error" ? "log-line-error" : sev === "warn" ? "log-line-warn" : undefined;
            return (
              <div key={i} className={cls}>
                {line}
              </div>
            );
          })}
        </pre>
      )}
      {collapsed && <p className="subtitle">{filtered.length} lines hidden.</p>}
    </div>
  );
}
