export function confidenceColor(score: number): string {
  if (score >= 80) return "var(--success)";
  if (score >= 50) return "var(--warning)";
  return "var(--danger)";
}
