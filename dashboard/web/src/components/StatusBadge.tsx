import { CheckCircle2, AlertCircle, RefreshCw, HelpCircle, XCircle, ShieldAlert } from "lucide-react";
import type { PackageStatusValue } from "../types";

const LABELS: Record<PackageStatusValue, string> = {
  certified: "Certified",
  certified_with_warnings: "Certified with Warnings",
  certified_with_recovery: "Certified with Recovery",
  partial_certification: "Partial Certification",
  engine_failure: "Engine Failure",
  fatal_failure: "Fatal Failure",
};

const CLASSES: Record<PackageStatusValue, string> = {
  certified: "badge badge-green",
  certified_with_warnings: "badge badge-yellow",
  certified_with_recovery: "badge badge-blue",
  partial_certification: "badge badge-orange",
  engine_failure: "badge badge-red",
  fatal_failure: "badge badge-red",
};

const ICONS: Record<PackageStatusValue, typeof CheckCircle2> = {
  certified: CheckCircle2,
  certified_with_warnings: AlertCircle,
  certified_with_recovery: RefreshCw,
  partial_certification: HelpCircle,
  engine_failure: ShieldAlert,
  fatal_failure: XCircle,
};

export function StatusBadge({ status }: { status: PackageStatusValue }) {
  const Icon = ICONS[status];
  return (
    <span className={CLASSES[status]}>
      <Icon size={12} />
      {LABELS[status]}
    </span>
  );
}
