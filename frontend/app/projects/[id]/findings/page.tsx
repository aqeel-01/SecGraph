"use client";

import Link from "next/link";
import { ArrowLeft, Filter, Search } from "lucide-react";
import { useEffect, useState } from "react";

import { FindingCard } from "@/components/FindingCard";
import { api, type Finding } from "@/lib/api";

export default function ProjectFindingsPage({ params }: { params: { id: string } }) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [severity, setSeverity] = useState("");
  const [rule, setRule] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const query: Record<string, string> = {};
    if (severity) query.severity = severity;
    if (rule) query.rule = rule;
    if (endpoint) query.endpoint = endpoint;
    api.findings(params.id, query)
      .then(setFindings)
      .catch((reason: Error) => setError(reason.message));
  }, [params.id, severity, rule, endpoint]);

  return (
    <div className="space-y-7">
      <div>
        <Link href={`/projects/${params.id}`} className="inline-flex items-center gap-2 text-xs text-cyan hover:underline">
          <ArrowLeft size={14} /> Project overview
        </Link>
        <div className="mt-4 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan">Analysis output</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Security findings</h1>
          </div>
          <span className="text-sm text-muted">{findings.length} results</span>
        </div>
      </div>
      <div className="grid gap-3 rounded-xl border border-line bg-panel p-4 md:grid-cols-[180px_1fr_1fr]">
        <label className="flex items-center gap-2 rounded-lg border border-line bg-ink px-3 py-2 text-xs text-muted">
          <Filter size={14} />
          <select value={severity} onChange={(event) => setSeverity(event.target.value)} className="w-full bg-transparent text-slate-200 outline-none">
            <option value="">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>
        <label className="flex items-center gap-2 rounded-lg border border-line bg-ink px-3 py-2 text-xs text-muted">
          <Search size={14} />
          <input value={endpoint} onChange={(event) => setEndpoint(event.target.value)} placeholder="Exact endpoint..." className="w-full bg-transparent text-sm text-white outline-none placeholder:text-muted" />
        </label>
        <label className="flex items-center gap-2 rounded-lg border border-line bg-ink px-3 py-2 text-xs text-muted">
          <Search size={14} />
          <input value={rule} onChange={(event) => setRule(event.target.value)} placeholder="Rule ID..." className="w-full bg-transparent text-sm text-white outline-none placeholder:text-muted" />
        </label>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <div className="grid gap-4 lg:grid-cols-2">
        {findings.map((finding) => <FindingCard key={finding.id} finding={finding} />)}
      </div>
      {!findings.length && !error && <div className="rounded-xl border border-line bg-panel p-12 text-center text-sm text-muted">No findings match the selected filters.</div>}
    </div>
  );
}
