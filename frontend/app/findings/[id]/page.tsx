"use client";

import Link from "next/link";
import { ArrowLeft, FileCode2, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { SeverityBadge } from "@/components/SeverityBadge";
import { api, type Finding } from "@/lib/api";

export default function FindingDetailPage({ params }: { params: { id: string } }) {
  const [finding, setFinding] = useState<Finding | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.finding(params.id)
      .then(setFinding)
      .catch((reason: Error) => setError(reason.message));
  }, [params.id]);

  if (error) return <p className="text-sm text-danger">{error}</p>;
  if (!finding) return <div className="animate-pulse text-sm text-muted">Loading finding...</div>;

  const explanation = finding.ai_analysis?.structured_output;

  return (
    <div className="mx-auto max-w-5xl space-y-7">
      <Link href={finding.project_id ? `/projects/${finding.project_id}/findings` : "/findings"} className="inline-flex items-center gap-2 text-xs text-cyan hover:underline">
        <ArrowLeft size={14} /> Back to findings
      </Link>
      <section className="rounded-2xl border border-line bg-panel p-6 lg:p-8">
        <div className="flex flex-wrap items-center gap-3">
          <SeverityBadge severity={finding.severity} />
          <span className="font-mono text-xs text-muted">{finding.rule_id}</span>
        </div>
        <h1 className="mt-5 text-3xl font-semibold text-white">{finding.title}</h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400">{finding.description}</p>
        <div className="mt-7 flex flex-wrap gap-4 border-t border-line pt-5 text-sm">
          <span className="rounded-lg bg-ink px-3 py-2 font-mono text-cyan">{finding.endpoint ?? "No endpoint"}</span>
          <span className="flex items-center gap-2 rounded-lg bg-ink px-3 py-2 font-mono text-slate-300">
            <FileCode2 size={15} className="text-muted" /> {finding.file}:{finding.line ?? "?"}
          </span>
          <span className="rounded-lg bg-ink px-3 py-2 text-muted">Static confidence {Math.round(finding.confidence * 100)}%</span>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <InfoBlock title="Explanation" value={explanation?.explanation ?? finding.description} />
        <InfoBlock title="Potential attack" value={explanation?.potential_attack ?? "AI explanation is not available for this finding yet."} />
        <InfoBlock title="Impact" value={explanation?.impact ?? "Review the evidence and confirm impact in the application context."} />
        <InfoBlock title="Suggested fix" value={explanation?.suggested_fix ?? finding.remediation} />
      </div>

      <section className="rounded-xl border border-line bg-panel p-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <ShieldAlert size={17} className="text-cyan" /> Evidence
        </div>
        <pre className="mt-4 overflow-x-auto rounded-lg border border-line bg-ink p-4 font-mono text-xs leading-6 text-slate-300">{finding.evidence}</pre>
      </section>
    </div>
  );
}

function InfoBlock({ title, value }: { title: string; value: string }) {
  return (
    <section className="rounded-xl border border-line bg-panel p-6">
      <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">{title}</h2>
      <p className="mt-4 text-sm leading-7 text-slate-300">{value}</p>
    </section>
  );
}
