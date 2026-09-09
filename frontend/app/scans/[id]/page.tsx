"use client";

import Link from "next/link";
import { Check, Circle, Loader2, X } from "lucide-react";
import { useEffect, useState } from "react";

import { api, type Scan, type ScanStatus } from "@/lib/api";

const steps = [
  "Preprocess source files",
  "Build AST and routes",
  "Update code graph",
  "Run static security rules",
  "Generate focused AI analysis",
  "Store findings"
];

export default function ScanProgressPage({ params }: { params: { id: string } }) {
  const [scan, setScan] = useState<Scan | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function poll() {
      try {
        const next = await api.scan(params.id);
        if (active) setScan(next);
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Unable to load scan.");
      }
    }
    poll();
    const timer = window.setInterval(() => {
      if (scan?.status !== "COMPLETED" && scan?.status !== "FAILED") poll();
    }, 2000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [params.id, scan?.status]);

  const status: ScanStatus = scan?.status ?? "PENDING";
  const finished = status === "COMPLETED" || status === "FAILED";

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan">Background analysis</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Scan progress</h1>
        <p className="mt-2 font-mono text-xs text-muted">{params.id}</p>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <section className="rounded-2xl border border-line bg-panel p-6 lg:p-8">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-200">
              {status === "COMPLETED" ? "Analysis complete" : status === "FAILED" ? "Analysis failed" : "Analysis in progress"}
            </p>
            <p className="mt-2 text-xs text-muted">
              {status === "FAILED" ? scan?.error_message ?? "The worker reported an error." : "You can leave this page; the scan will continue in the background."}
            </p>
          </div>
          <StatusIcon status={status} />
        </div>
        <div className="mt-8 space-y-1">
          {steps.map((step, index) => {
            const active = status === "RUNNING" && index === 3;
            const done = status === "COMPLETED" || (status === "RUNNING" && index < 3);
            return (
              <div key={step} className={`flex items-center gap-4 rounded-lg px-3 py-3 ${active ? "bg-cyan/10" : ""}`}>
                {done ? <Check size={16} className="text-cyan" /> : active ? <Loader2 size={16} className="animate-spin text-cyan" /> : <Circle size={16} className="text-slate-600" />}
                <span className={`text-sm ${done || active ? "text-slate-200" : "text-muted"}`}>{step}</span>
              </div>
            );
          })}
        </div>
        {finished && scan?.project_id && (
          <Link href={`/projects/${scan.project_id}`} className="mt-7 inline-flex rounded-lg bg-cyan px-4 py-2.5 text-sm font-semibold text-ink">
            View project results
          </Link>
        )}
      </section>
    </div>
  );
}

function StatusIcon({ status }: { status: ScanStatus }) {
  if (status === "COMPLETED") return <div className="rounded-full bg-cyan/10 p-3 text-cyan"><Check size={22} /></div>;
  if (status === "FAILED") return <div className="rounded-full bg-danger/10 p-3 text-danger"><X size={22} /></div>;
  return <div className="rounded-full bg-cyan/10 p-3 text-cyan"><Loader2 size={22} className="animate-spin" /></div>;
}
