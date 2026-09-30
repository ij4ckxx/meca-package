import type { ReactNode } from "react";

export type StatTone = "accent" | "success" | "warning" | "danger" | "info" | "neutral";

export function StatCard({
  label,
  value,
  sub,
  icon,
  tone = "accent",
}: {
  label: string;
  value: string | number | ReactNode;
  sub?: string;
  icon?: ReactNode;
  tone?: StatTone;
}) {
  return (
    <div className="stat-card">
      {icon && <div className={`stat-icon-badge stat-icon-badge-${tone}`}>{icon}</div>}
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}
