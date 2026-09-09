"use client";

import Link from "next/link";
import { ArrowLeft, Search } from "lucide-react";
import { useEffect, useState } from "react";

import { FindingCard } from "@/components/FindingCard";
import { api, type Finding } from "@/lib/api";

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [severity, setSeverity] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.findings(undefined, severity ? { severity } : {})
      .then(setFindings)
      .catch((reason: Error) => setError(reason.message));
  }, [severity]);

  return (
    <div className="space-y-7">
      <div>
        <Link href="/" className="inline-flex items-center gap-2 text-xs text-cyan hover:underline">
          <ArrowLeft size={14} /> Dashboard
        </Link>
        <div className="mt-4 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan">Global view</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">All findings</h1>
          </div>
          <select value={severity} onChange={(event) => setSeverity(event.target.value)} className="rounded-lg border border-line bg-panel px-3 py-2 text-xs text-slate-200 outline-none">
            <option value="">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <div className="grid gap-4 lg:grid-cols-2">
        {findings.map((finding) => <FindingCard key={finding.id} finding={finding} />)}
      </div>
      {!findings.length && !error && <div className="rounded-xl border border-line bg-panel p-12 text-center text-sm text-muted"><Search size={20} className="mx-auto mb-3 text-muted" />No findings detected.</div>}
    </div>
  );
}
