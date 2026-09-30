import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, HeartPulse, CheckCircle2, HelpCircle, Gauge, TrendingUp } from "lucide-react";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import { useBatch } from "../context/BatchContext";
import { StatCard } from "../components/StatCard";
import { LoadingState, ErrorState } from "../components/States";

const STATUS_COLORS: Record<string, string> = {
  certified: "#12805c",
  certified_with_warnings: "#1d5fbf",
  certified_with_recovery: "#4f46e5",
  partial_certification: "#b45309",
  engine_failure: "#c0152f",
  fatal_failure: "#7c2d3a",
};

const VALIDATION_COLORS: Record<string, string> = {
  pass: "#12805c",
  warning: "#b45309",
  error: "#c0152f",
  not_checked: "#9296a6",
};

const SPEC_ALIGNMENT_LABELS: Record<string, string> = {
  source_data_issue: "Source Data Issue",
  business_rule_candidate: "Business Rule Candidate",
  recovery_rule_candidate: "Recovery Rule Candidate",
  validation_only: "Validation Only",
};

interface TrendPoint {
  batch: string;
  recoveries: number;
  warnings: number;
  duration: number | null;
}

function useTrend() {
  const { batches } = useBatch();
  const [trend, setTrend] = useState<TrendPoint[]>([]);

  useEffect(() => {
    if (batches.length === 0) return;
    let cancelled = false;
    Promise.all(
      batches.map(async (b) => {
        const [recoveryRules, warnings] = await Promise.all([
          api.getRecoveryRuleStats(b.batch_id),
          api.getWarningStats(b.batch_id),
        ]);
        return {
          batch: b.batch_id.slice(5, 16),
          recoveries: recoveryRules.reduce((s, r) => s + r.occurrences, 0),
          warnings: warnings.reduce((s, w) => s + w.occurrences, 0),
          duration: b.duration_seconds,
        };
      }),
    ).then((points) => !cancelled && setTrend(points));
    return () => {
      cancelled = true;
    };
  }, [batches]);

  return trend;
}

export function AnalyticsPage() {
  const { selectedBatchId } = useBatch();
  const summary = useApi(useCallback(() => api.getSummary(selectedBatchId), [selectedBatchId]), [selectedBatchId]);
  const recovery = useApi(
    useCallback(() => api.getRecoveryRuleStats(selectedBatchId), [selectedBatchId]),
    [selectedBatchId],
  );
  const warnings = useApi(useCallback(() => api.getWarningStats(selectedBatchId), [selectedBatchId]), [selectedBatchId]);
  const businessRules = useApi(
    useCallback(() => api.getBusinessRuleStats(selectedBatchId), [selectedBatchId]),
    [selectedBatchId],
  );
  const missingFiles = useApi(
    useCallback(() => api.getTopMissingFiles(selectedBatchId), [selectedBatchId]),
    [selectedBatchId],
  );
  const confidence = useApi(
    useCallback(() => api.getConfidenceDistribution(selectedBatchId), [selectedBatchId]),
    [selectedBatchId],
  );
  const validation = useApi(
    useCallback(() => api.getValidationStats(selectedBatchId), [selectedBatchId]),
    [selectedBatchId],
  );
  const trend = useTrend();

  if (summary.loading) return <LoadingState label="Loading analytics..." />;
  if (summary.error) return <ErrorState message={summary.error} />;
  if (!summary.data) return null;

  const total = summary.data.total_articles;
  const uploaded = summary.data.category_counts.uploaded;
  const manualReview = summary.data.category_counts.manual_review;
  const successPct = total > 0 ? Math.round((uploaded / total) * 100) : 0;
  const manualReviewPct = total > 0 ? Math.round((manualReview / total) * 100) : 0;

  const statusData = Object.entries(summary.data.status_counts).map(([status, count]) => ({
    name: status,
    value: count,
  }));
  const confidenceData = Object.entries(summary.data.confidence_distribution).map(([bucket, count]) => ({
    name: bucket,
    value: count,
  }));
  const validationData = validation.data
    ? Object.entries(validation.data.overall_counts).map(([name, value]) => ({ name, value }))
    : [];
  const dtdData = validation.data
    ? Object.entries(validation.data.dtd_counts).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div>
      <h1>
        <BarChart3 size={20} /> Analytics
      </h1>
      <p className="subtitle">Reused directly from the engine's own generated reports — nothing recomputed by the engine.</p>

      <div className="stat-grid">
        <StatCard icon={<CheckCircle2 size={15} />} tone="success" label="Success %" value={`${successPct}%`} />
        <StatCard icon={<HelpCircle size={15} />} tone="warning" label="Manual Review %" value={`${manualReviewPct}%`} />
        <StatCard
          icon={<Gauge size={15} />}
          tone="info"
          label="Avg. Confidence"
          value={confidence.data ? confidence.data.average_score.toFixed(1) : "—"}
        />
        <StatCard
          icon={<TrendingUp size={15} />}
          tone="accent"
          label="Median Confidence"
          value={confidence.data ? confidence.data.median_score.toFixed(1) : "—"}
        />
      </div>

      <h2>Status Distribution</h2>
      <div className="panel">
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie data={statusData} dataKey="value" nameKey="name" outerRadius={90} label>
              {statusData.map((entry) => (
                <Cell key={entry.name} fill={STATUS_COLORS[entry.name] ?? "#888"} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <h2>Confidence Distribution</h2>
      <div className="panel">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={confidenceData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="name" stroke="var(--text-muted)" />
            <YAxis stroke="var(--text-muted)" allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="value" fill="var(--accent)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <h2>Recovery Rule Frequency</h2>
      <div className="panel">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={(recovery.data ?? []).slice(0, 10)}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="rule_id" stroke="var(--text-muted)" />
            <YAxis stroke="var(--text-muted)" allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="occurrences" fill="var(--accent)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <h2>Warning Frequency</h2>
      <div className="panel">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={(warnings.data ?? []).slice(0, 8)} layout="vertical" margin={{ left: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis type="number" stroke="var(--text-muted)" allowDecimals={false} />
            <YAxis
              type="category"
              dataKey="code"
              stroke="var(--text-muted)"
              width={220}
              tickFormatter={(v: string) => (v.length > 28 ? v.slice(0, 28) + "…" : v)}
            />
            <Tooltip />
            <Bar dataKey="occurrences" fill="var(--success)" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <h2>Business Rule Frequency</h2>
      <div className="panel">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={(businessRules.data ?? []).slice(0, 10)}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="rule_id" stroke="var(--text-muted)" />
            <YAxis stroke="var(--text-muted)" allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="total_triggered" name="Triggered" fill="var(--warning)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <h2>XML Validation Results (well-formed + DTD, worst of both)</h2>
      <div className="stat-grid">
        <StatCard tone="danger" label="Total Errors" value={validation.data?.total_errors ?? 0} />
        <StatCard tone="warning" label="Total Warnings" value={validation.data?.total_warnings ?? 0} />
        <StatCard tone="neutral" label="Files with DTD Not Vendored" value={validation.data?.dtd_not_vendored_count ?? 0} />
      </div>
      <div className="panel">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={validationData} dataKey="value" nameKey="name" outerRadius={80} label>
              {validationData.map((entry) => (
                <Cell key={entry.name} fill={VALIDATION_COLORS[entry.name] ?? "#888"} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <h2>DTD Compliance Only (separate from well-formedness)</h2>
      <div className="panel">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={dtdData} dataKey="value" nameKey="name" outerRadius={80} label>
              {dtdData.map((entry) => (
                <Cell key={entry.name} fill={VALIDATION_COLORS[entry.name] ?? "#888"} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <h2>Spec Alignment Classification</h2>
      <div className="stat-grid">
        <StatCard tone="success" icon={<CheckCircle2 size={15} />} label="Engine Defects Fixed" value={validation.data?.engine_defects_fixed_count ?? 0} />
        <StatCard tone="neutral" label="Source Data Issues" value={validation.data?.spec_alignment_counts.source_data_issue ?? 0} />
        <StatCard
          tone="neutral"
          label="Business Rule Candidates"
          value={validation.data?.spec_alignment_counts.business_rule_candidate ?? 0}
        />
        <StatCard
          tone="neutral"
          label="Recovery Rule Candidates"
          value={validation.data?.spec_alignment_counts.recovery_rule_candidate ?? 0}
        />
        <StatCard tone="neutral" label="Validation Only" value={validation.data?.spec_alignment_counts.validation_only ?? 0} />
      </div>
      <div className="panel">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart
            data={Object.entries(validation.data?.spec_alignment_counts ?? {}).map(([name, value]) => ({
              name: SPEC_ALIGNMENT_LABELS[name] ?? name,
              value,
            }))}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="name" stroke="var(--text-muted)" tick={{ fontSize: 11 }} />
            <YAxis stroke="var(--text-muted)" allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="value" fill="var(--accent)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <h2>Most Common Validation Issues</h2>
      <div className="panel">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart
            data={validation.data?.common_issues ?? []}
            layout="vertical"
            margin={{ left: 40 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis type="number" stroke="var(--text-muted)" allowDecimals={false} />
            <YAxis
              type="category"
              dataKey="message"
              stroke="var(--text-muted)"
              width={220}
              tickFormatter={(v: string) => (v.length > 28 ? v.slice(0, 28) + "…" : v)}
            />
            <Tooltip />
            <Bar dataKey="occurrences" fill="var(--warning)" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
        {(validation.data?.common_issues.length ?? 0) === 0 && (
          <p style={{ margin: 0 }}>No validation issues recorded in this batch.</p>
        )}
      </div>

      <h2>
        <HeartPulse size={16} /> Journal Health
      </h2>
      <p className="subtitle">
        <Link to="/journal-health">Open the dedicated Journal Health page →</Link>
      </p>

      <h2>Top Missing Files</h2>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Occurrences</th>
            </tr>
          </thead>
          <tbody>
            {(missingFiles.data ?? []).map((m) => (
              <tr key={m.file}>
                <td title={m.file}>{m.file.length > 60 ? m.file.slice(0, 60) + "…" : m.file}</td>
                <td>{m.occurrences}</td>
              </tr>
            ))}
            {(missingFiles.data ?? []).length === 0 && (
              <tr>
                <td colSpan={2}>No missing files in this batch.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <h2>Processing Time Across Batches</h2>
      <div className="panel">
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="batch" stroke="var(--text-muted)" />
            <YAxis stroke="var(--text-muted)" />
            <Tooltip />
            <Line type="monotone" dataKey="duration" name="Duration (s)" stroke="var(--accent)" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <h2>Recovery &amp; Warning Trend Across Batches</h2>
      <div className="panel">
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="batch" stroke="var(--text-muted)" />
            <YAxis stroke="var(--text-muted)" allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="recoveries" stroke="var(--success)" strokeWidth={2} />
            <Line type="monotone" dataKey="warnings" stroke="var(--warning)" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
