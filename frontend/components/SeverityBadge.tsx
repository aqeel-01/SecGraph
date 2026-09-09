export function SeverityBadge({ severity }: { severity: string }) {
  const normalized = severity.toLowerCase();
  const styles: Record<string, string> = {
    critical: "border-danger/30 bg-danger/10 text-danger",
    high: "border-orange-400/30 bg-orange-400/10 text-orange-300",
    medium: "border-warning/30 bg-warning/10 text-warning",
    low: "border-info/30 bg-info/10 text-info",
    informational: "border-slate-500/30 bg-slate-500/10 text-slate-300"
  };
  return (
    <span
      className={`rounded-md border px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${
        styles[normalized] ?? styles.informational
      }`}
    >
      {severity}
    </span>
  );
}
