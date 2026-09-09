import type { LucideIcon } from "lucide-react";

export function StatCard({
  label,
  value,
  icon: Icon,
  tone = "default"
}: {
  label: string;
  value: number | string;
  icon: LucideIcon;
  tone?: "default" | "danger" | "warning" | "info";
}) {
  const tones = {
    default: "text-cyan bg-cyan/10",
    danger: "text-danger bg-danger/10",
    warning: "text-warning bg-warning/10",
    info: "text-info bg-info/10"
  };
  return (
    <div className="rounded-xl border border-line bg-panel p-5 shadow-glow">
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium uppercase tracking-wider text-muted">
          {label}
        </p>
        <div className={`rounded-lg p-2 ${tones[tone]}`}>
          <Icon size={16} />
        </div>
      </div>
      <p className="mt-5 text-3xl font-semibold tracking-tight text-white">
        {value}
      </p>
    </div>
  );
}
