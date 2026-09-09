import Link from "next/link";
import { ArrowUpRight, FileCode2 } from "lucide-react";

import type { Finding } from "@/lib/api";
import { SeverityBadge } from "@/components/SeverityBadge";

export function FindingCard({ finding }: { finding: Finding }) {
  return (
    <Link
      href={`/findings/${finding.id}`}
      className="group block rounded-xl border border-line bg-panel p-5 transition hover:border-cyan/40 hover:bg-panel2"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <SeverityBadge severity={finding.severity} />
          <span className="font-mono text-xs text-muted">{finding.rule_id}</span>
        </div>
        <ArrowUpRight
          size={16}
          className="text-muted transition group-hover:text-cyan"
        />
      </div>
      <h3 className="mt-4 font-medium text-white">{finding.title}</h3>
      <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-400">
        {finding.description}
      </p>
      <div className="mt-5 flex flex-wrap items-center gap-4 border-t border-line pt-4 text-xs text-muted">
        <span className="font-mono text-cyan">{finding.endpoint ?? "No endpoint"}</span>
        <span className="flex items-center gap-1.5">
          <FileCode2 size={13} />
          {finding.file}:{finding.line ?? "?"}
        </span>
      </div>
    </Link>
  );
}
