"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, Bug, FolderKanban, Shield } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { FindingCard } from "@/components/FindingCard";
import { StatCard } from "@/components/StatCard";
import { api, type Finding, type Project, type Summary } from "@/lib/api";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api.projects(),
      api.findings(undefined, { severity: "critical" })
    ])
      .then(async ([loadedProjects, criticalFindings]) => {
        setProjects(loadedProjects);
        setFindings(criticalFindings);
        setSummaries(
          await Promise.all(loadedProjects.map((project) => api.summary(project.id)))
        );
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  const totals = useMemo(
    () => ({
      total: summaries.reduce((sum, item) => sum + item.total_findings, 0),
      critical: summaries.reduce((sum, item) => sum + item.critical_count, 0),
      high: summaries.reduce((sum, item) => sum + item.high_count, 0),
      medium: summaries.reduce((sum, item) => sum + item.medium_count, 0),
      low: summaries.reduce((sum, item) => sum + item.low_count, 0),
      score: summaries.length
        ? Math.round(
            summaries.reduce((sum, item) => sum + item.overall_security_score, 0) /
              summaries.length
          )
        : 100
    }),
    [summaries]
  );

  return (
    <div className="space-y-8">
      <section className="grid-background relative overflow-hidden rounded-2xl border border-line bg-panel p-7 lg:p-10">
        <div className="relative max-w-2xl">
          <p className="mb-4 text-xs font-semibold uppercase tracking-[0.24em] text-cyan">
            Security operations center
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-white lg:text-5xl">
            Know what your API is exposing.
          </h1>
          <p className="mt-4 max-w-xl text-sm leading-7 text-slate-400">
            SecGraph combines deterministic code analysis with focused AI
            explanations to surface actionable API security risks.
          </p>
          <Link
            href="/projects/upload"
            className="mt-7 inline-flex items-center gap-2 rounded-lg bg-cyan px-4 py-2.5 text-sm font-semibold text-ink transition hover:bg-cyan/80"
          >
            Analyze a project <ArrowRight size={16} />
          </Link>
        </div>
        <Shield
          size={190}
          strokeWidth={0.6}
          className="absolute -right-8 -top-8 hidden text-cyan/10 lg:block"
        />
      </section>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {error}. Check that the FastAPI server is running.
        </div>
      )}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Security score" value={`${totals.score}/100`} icon={Shield} />
        <StatCard label="Total findings" value={totals.total} icon={Bug} />
        <StatCard label="Critical" value={totals.critical} icon={AlertTriangle} tone="danger" />
        <StatCard label="High" value={totals.high} icon={AlertTriangle} tone="warning" />
        <StatCard label="Medium / low" value={`${totals.medium} / ${totals.low}`} icon={AlertTriangle} tone="info" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
        <div className="rounded-xl border border-line bg-panel">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <div>
              <h2 className="font-semibold text-white">Projects</h2>
              <p className="mt-1 text-xs text-muted">Monitored API codebases</p>
            </div>
            <Link href="/projects" className="text-xs font-medium text-cyan hover:underline">
              View all
            </Link>
          </div>
          <div className="divide-y divide-line">
            {projects.slice(0, 5).map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                className="flex items-center justify-between px-5 py-4 transition hover:bg-white/[0.03]"
              >
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-cyan/10 p-2 text-cyan">
                    <FolderKanban size={16} />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-200">{project.name}</p>
                    <p className="mt-1 text-xs text-muted">{project.backend_framework ?? "Framework pending"}</p>
                  </div>
                </div>
                <ArrowRight size={15} className="text-muted" />
              </Link>
            ))}
            {!projects.length && (
              <div className="px-5 py-10 text-center text-sm text-muted">No projects yet.</div>
            )}
          </div>
        </div>

        <div>
          <div className="mb-4 flex items-end justify-between">
            <div>
              <h2 className="font-semibold text-white">Critical findings</h2>
              <p className="mt-1 text-xs text-muted">Immediate review recommended</p>
            </div>
            <Link href="/findings" className="text-xs font-medium text-cyan hover:underline">
              Browse findings
            </Link>
          </div>
          <div className="space-y-3">
            {findings.slice(0, 2).map((finding) => (
              <FindingCard key={finding.id} finding={finding} />
            ))}
            {!findings.length && (
              <div className="rounded-xl border border-line bg-panel px-5 py-10 text-center text-sm text-muted">
                No critical findings detected.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
