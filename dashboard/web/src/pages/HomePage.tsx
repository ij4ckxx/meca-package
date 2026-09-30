import { useCallback } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  Package,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  HelpCircle,
  XCircle,
  Clock,
  Gauge,
  History,
  BookOpen,
  ShieldAlert,
} from "lucide-react";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import { StatCard, type StatTone } from "../components/StatCard";
import { LoadingState, ErrorState } from "../components/States";
import { useBatch } from "../context/BatchContext";

const STATUS_META: { key: string; label: string; icon: typeof CheckCircle2; tone: StatTone; color: string }[] = [
  { key: "certified", label: "Certified", icon: CheckCircle2, tone: "success", color: "#12805c" },
  { key: "certified_with_warnings", label: "Certified With Warnings", icon: AlertCircle, tone: "info", color: "#1d5fbf" },
  { key: "certified_with_recovery", label: "Certified With Recovery", icon: RefreshCw, tone: "accent", color: "#4f46e5" },
  { key: "partial_certification", label: "Partial Certification", icon: HelpCircle, tone: "warning", color: "#b45309" },
  { key: "engine_failure", label: "Engine Failure", icon: XCircle, tone: "danger", color: "#c0152f" },
  { key: "fatal_failure", label: "Fatal Failure", icon: XCircle, tone: "danger", color: "#7c2d3a" },
];

function pct(count: number, total: number): string {
  return total === 0 ? "0%" : `${Math.round((count / total) * 100)}%`;
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return minutes > 0 ? `${minutes}m ${rest}s` : `${rest}s`;
}

export function HomePage() {
  const { selectedBatchId, batches } = useBatch();
  const summary = useApi(useCallback(() => api.getSummary(selectedBatchId), [selectedBatchId]), [selectedBatchId]);
  const journals = useApi(useCallback(() => api.getJournals(selectedBatchId), [selectedBatchId]), [selectedBatchId]);
  const recoveryRules = useApi(
    useCallback(() => api.getRecoveryRuleStats(selectedBatchId), [selectedBatchId]),
    [selectedBatchId],
  );
  const warnings = useApi(useCallback(() => api.getWarningStats(selectedBatchId), [selectedBatchId]), [selectedBatchId]);

  if (summary.loading) return <LoadingState label="Loading overview..." />;
  if (summary.error) return <ErrorState message={summary.error} />;
  if (!summary.data) return null;

  const data = summary.data;
  const activeBatch =
    batches.find((b) => b.batch_id === (selectedBatchId ?? batches[batches.length - 1]?.batch_id)) ?? null;
  const totalRecoveries = recoveryRules.data?.reduce((sum, r) => sum + r.occurrences, 0) ?? 0;
  const totalWarnings = warnings.data?.reduce((sum, w) => sum + w.occurrences, 0) ?? 0;
  const businessRuleFailures =
    journals.data?.reduce((sum, j) => sum + Object.values(j.business_rule_failure_counts).reduce((s, v) => s + v, 0), 0) ??
    0;
  const avgProcessingTime =
    activeBatch?.duration_seconds && data.total_articles > 0
      ? activeBatch.duration_seconds / data.total_articles
      : null;

  const statusChartData = STATUS_META.map((meta) => ({
    name: meta.label,
    value: data.status_counts[meta.key] ?? 0,
    color: meta.color,
  })).filter((d) => d.value > 0);

  const journalChartData = (journals.data ?? [])
    .slice()
    .sort((a, b) => b.article_count - a.article_count)
    .slice(0, 10)
    .map((j) => ({ journal: j.journal, count: j.article_count }));

  const recoveryChartData = (recoveryRules.data ?? []).slice(0, 5);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>
            <Package size={22} /> Migration Overview
          </h1>
          <p className="subtitle">
            {activeBatch ? (
              <>
                Latest batch <strong>{activeBatch.batch_id}</strong> ·{" "}
                <Link to="/batches">view all batches →</Link>
              </>
            ) : (
              "No batch selected"
            )}
          </p>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard icon={<Package size={15} />} tone="info" label="Total Packages" value={data.total_articles} />
        {STATUS_META.map(({ key, label, icon: Icon, tone }) => (
          <StatCard
            key={key}
            icon={<Icon size={15} />}
            tone={tone}
            label={label}
            value={data.status_counts[key] ?? 0}
            sub={pct(data.status_counts[key] ?? 0, data.total_articles)}
          />
        ))}
      </div>

      {statusChartData.length > 0 && (
        <div className="panel">
          <h3 style={{ margin: "0 0 12px" }}>Package Status Distribution</h3>
          <div style={{ display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap" }}>
            <ResponsiveContainer width={200} height={200}>
              <PieChart>
                <Pie data={statusChartData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90}>
                  {statusChartData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1, minWidth: 200 }}>
              {statusChartData.map((entry) => (
                <div key={entry.name} style={{ display: "flex", alignItems: "center", gap: 9 }}>
                  <span style={{ width: 9, height: 9, borderRadius: 3, background: entry.color, flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: "var(--text-muted)", flexGrow: 1 }}>{entry.name}</span>
                  <span style={{ fontSize: 12.5, fontWeight: 700 }}>{entry.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <h2>
        <Clock size={16} /> Processing
      </h2>
      <div className="stat-grid">
        <StatCard
          icon={<Clock size={15} />}
          label="Processing Duration"
          value={formatDuration(activeBatch?.duration_seconds ?? null)}
        />
        <StatCard
          icon={<Gauge size={15} />}
          label="Avg. Time / Article"
          value={avgProcessingTime ? `${avgProcessingTime.toFixed(1)}s` : "—"}
        />
        <StatCard icon={<History size={15} />} label="Batches Run" value={batches.length} />
      </div>

      <h2>
        <Gauge size={16} /> Confidence Distribution
      </h2>
      <div className="stat-grid">
        <StatCard tone="danger" label="Low" value={data.confidence_distribution.low ?? 0} />
        <StatCard tone="warning" label="Medium" value={data.confidence_distribution.medium ?? 0} />
        <StatCard tone="success" label="High" value={data.confidence_distribution.high ?? 0} />
      </div>

      <h2>
        <CheckCircle2 size={16} /> XML Validation (well-formed + DTD, worst of both)
      </h2>
      <div className="stat-grid">
        <StatCard
          icon={<CheckCircle2 size={15} />}
          tone="success"
          label="Pass"
          value={data.validation_counts.pass}
          sub={pct(data.validation_counts.pass, data.total_articles)}
        />
        <StatCard
          icon={<AlertCircle size={15} />}
          tone="warning"
          label="Warning"
          value={data.validation_counts.warning}
          sub={pct(data.validation_counts.warning, data.total_articles)}
        />
        <StatCard
          icon={<XCircle size={15} />}
          tone="danger"
          label="Error"
          value={data.validation_counts.error}
          sub={pct(data.validation_counts.error, data.total_articles)}
        />
      </div>

      <h2>DTD Compliance (separate from well-formedness)</h2>
      <div className="stat-grid">
        <StatCard
          icon={<CheckCircle2 size={15} />}
          tone="success"
          label="DTD Valid"
          value={data.dtd_counts.pass}
          sub={pct(data.dtd_counts.pass, data.total_articles)}
        />
        <StatCard
          icon={<AlertCircle size={15} />}
          tone="warning"
          label="DTD Warning"
          value={data.dtd_counts.warning}
          sub={pct(data.dtd_counts.warning, data.total_articles)}
        />
        <StatCard
          icon={<XCircle size={15} />}
          tone="danger"
          label="DTD Invalid"
          value={data.dtd_counts.error}
          sub={pct(data.dtd_counts.error, data.total_articles)}
        />
        <StatCard
          tone="neutral"
          label="DTD Not Checked"
          value={data.dtd_counts.not_checked}
          sub={pct(data.dtd_counts.not_checked, data.total_articles)}
        />
      </div>

      <h2>Spec Alignment</h2>
      <div className="stat-grid">
        <StatCard icon={<CheckCircle2 size={15} />} tone="success" label="Engine Defects Fixed" value={data.engine_defects_fixed_count} />
        <StatCard tone="neutral" label="Source Data Issues" value={data.spec_alignment_counts.source_data_issue ?? 0} />
        <StatCard tone="neutral" label="Business Rule Candidates" value={data.spec_alignment_counts.business_rule_candidate ?? 0} />
        <StatCard tone="neutral" label="Recovery Rule Candidates" value={data.spec_alignment_counts.recovery_rule_candidate ?? 0} />
        <StatCard
          icon={<XCircle size={15} />}
          tone="danger"
          label="Remaining DTD Violations"
          value={
            (data.spec_alignment_counts.source_data_issue ?? 0) +
            (data.spec_alignment_counts.business_rule_candidate ?? 0) +
            (data.spec_alignment_counts.recovery_rule_candidate ?? 0) +
            (data.spec_alignment_counts.validation_only ?? 0)
          }
        />
      </div>

      <h2>
        <BookOpen size={16} /> Journal Distribution
      </h2>
      <div className="panel">
        {journalChartData.length === 0 ? (
          <p style={{ margin: 0 }}>No journal data in this batch.</p>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(160, journalChartData.length * 32)}>
            <BarChart data={journalChartData} layout="vertical" margin={{ left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" stroke="var(--text-muted)" allowDecimals={false} />
              <YAxis
                type="category"
                dataKey="journal"
                stroke="var(--text-muted)"
                width={150}
                tickFormatter={(v: string) => (v.length > 20 ? v.slice(0, 20) + "…" : v)}
              />
              <Tooltip />
              <Bar dataKey="count" fill="var(--accent)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <h2>
        <ShieldAlert size={16} /> Recovery &amp; Warnings
      </h2>
      <div className="stat-grid">
        <StatCard tone="accent" label="Recovery Count" value={totalRecoveries} />
        <StatCard tone="warning" label="Warning Count" value={totalWarnings} />
        <StatCard tone="danger" label="Business Rule Failures" value={businessRuleFailures} />
      </div>

      <h2>Top Recovery Rule Usage</h2>
      <div className="panel">
        {recoveryChartData.length === 0 ? (
          <p style={{ margin: 0 }}>No recovery rules triggered in this batch.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={recoveryChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="rule_id" stroke="var(--text-muted)" />
              <YAxis stroke="var(--text-muted)" allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="occurrences" fill="var(--accent)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
