import type { ReactNode } from "react";
import { Inbox, AlertTriangle } from "lucide-react";

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="loading-state">
      <span className="spinner" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ icon, title, description }: { icon?: ReactNode; title: string; description?: string }) {
  return (
    <div className="empty-state">
      {icon ?? <Inbox size={32} />}
      <p style={{ fontWeight: 600, margin: "4px 0" }}>{title}</p>
      {description && <p style={{ margin: 0, fontSize: 12.5 }}>{description}</p>}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="empty-state">
      <AlertTriangle size={32} color="var(--danger)" />
      <p style={{ fontWeight: 600, margin: "4px 0", color: "var(--danger)" }}>Something went wrong</p>
      <p style={{ margin: 0, fontSize: 12.5 }}>{message}</p>
    </div>
  );
}
