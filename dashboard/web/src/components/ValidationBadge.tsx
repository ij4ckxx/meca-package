import { CheckCircle2, AlertCircle, XCircle, HelpCircle } from "lucide-react";
import type { ValidationResultValue } from "../types";

const LABELS: Record<ValidationResultValue, string> = {
  pass: "Pass",
  warning: "Warning",
  error: "Error",
};

const CLASSES: Record<ValidationResultValue, string> = {
  pass: "badge badge-green",
  warning: "badge badge-yellow",
  error: "badge badge-red",
};

const ICONS: Record<ValidationResultValue, typeof CheckCircle2> = {
  pass: CheckCircle2,
  warning: AlertCircle,
  error: XCircle,
};

export function ValidationBadge({
  result,
  label,
}: {
  result: ValidationResultValue | null;
  label?: string;
}) {
  if (result === null) {
    return (
      <span className="badge badge-yellow">
        <HelpCircle size={12} />
        {label ? `${label}: Not Checked` : "Not Checked"}
      </span>
    );
  }
  const Icon = ICONS[result];
  return (
    <span className={CLASSES[result]}>
      <Icon size={12} />
      {label ? `${label}: ${LABELS[result]}` : LABELS[result]}
    </span>
  );
}
