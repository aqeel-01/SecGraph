"use client";

import Link from "next/link";
import { ArrowRight, BarChart3, Play, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { FindingCard } from "@/components/FindingCard";
import { SeverityBadge } from "@/components/SeverityBadge";
import { StatCard } from "@/components/StatCard";
import { api, formatDate, type Finding, type ProjectDetail, type Scan, type Summary } from "@/lib/api";

export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [scans, setScans] = useState<Scan[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [loadedProject, loadedSummary, loadedScans, loadedFindings] = await Promise.all([
        api.project(params.id),
        api.summary(params.id),
        api.scans(params.id),
        api.findings(params.id)
      ]);
      setProject(loadedProject);
      setSummary(loadedSummary);
      setScans(loadedScans);
      setFindings(loadedFindings);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load project.");
    }
  }, [params.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function startScan() {
    setBusy(true);
    try {
      const scan = await api.startScan(params.id);
      window.location.href = `/scans/${scan.id}`;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to start scan.");
      setBusy(false);
    }
  }

  if (error && !project) return <p className="text-sm text-danger">{error}</p>;
  if (!project || !summary) return <div className="animate-pulse text-sm text-muted">Loading project...</div>;

  return (
    <div className="space-y-8">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <Link href="/projects" className="text-xs text-cyan hover:underline">← All projects</Link>
          <h1 className="mt-3 text-3xl font-semibold text-white">{project.name}</h1>
          <p className="mt-2 text-sm text-muted">{project.backend_framework ?? "Framework pending"} · {project.source_type}</p>
        </div>
        <div className="flex gap-3">
          <button onClick={load} className="rounded-lg border border-line p-2.5 text-muted hover:text-white" aria-label="Refresh">
            <RefreshCw size={17} />
          </button>
          <button onClick={startScan} disabled={busy} className="flex items-center gap-2 rounded-lg bg-cyan px-4 py-2.5 text-sm font-semibold text-ink disabled:opacity-50">
            <Play size={15} /> {busy ? "Starting..." : "Start scan"}
          </button>
        </div>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard label="Security score" value={`${summary.overall_security_score}/100`} icon={BarChart3} />
        <StatCard label="Critical" value={summary.critical_count} icon={BarChart3} tone="danger" />
        <StatCard label="High" value={summary.high_count} icon={BarChart3} tone="warning" />
        <StatCard label="Medium" value={summary.medium_count} icon={BarChart3} tone="info" />
        <StatCard label="Low" value={summary.low_count} icon={BarChart3} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.4fr_0.6fr]">
        <div>
          <div className="mb-4 flex items-end justify-between">
            <div>
              <h2 className="font-semibold text-white">Security findings</h2>
              <p className="mt-1 text-xs text-muted">{summary.total_findings} findings in this project</p>
            </div>
            <Link href={`/projects/${params.id}/findings`} className="text-xs text-cyan hover:underline">View all</Link>
          </div>
          <div className="space-y-3">
            {findings.slice(0, 4).map((finding) => <FindingCard key={finding.id} finding={finding} />)}
            {!findings.length && <div className="rounded-xl border border-line bg-panel p-10 text-center text-sm text-muted">No findings yet.</div>}
          </div>
        </div>
        <div className="rounded-xl border border-line bg-panel">
          <div className="border-b border-line px-5 py-4">
            <h2 className="font-semibold text-white">Scan history</h2>
            <p className="mt-1 text-xs text-muted">Background analysis runs</p>
          </div>
          <div className="divide-y divide-line">
            {scans.slice(0, 5).map((scan) => (
              <Link key={scan.id} href={`/scans/${scan.id}`} className="flex items-center justify-between px-5 py-4 hover:bg-white/[0.03]">
                <div>
                  <p className="font-mono text-xs text-slate-300">{scan.id.slice(0, 8)}</p>
                  <p className="mt-1 text-[11px] text-muted">{formatDate(scan.completed_at ?? scan.started_at)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={scan.status} />
                  <ArrowRight size={14} className="text-muted" />
                </div>
              </Link>
            ))}
            {!scans.length && <p className="p-5 text-sm text-muted">No scans run yet.</p>}
          </div>
        </div>
      </section>
    </div>
  );
}
