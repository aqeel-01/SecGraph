"use client";

import { useRouter } from "next/navigation";
import { FileArchive, Loader2, UploadCloud } from "lucide-react";
import { useState } from "react";

import { api } from "@/lib/api";

export default function UploadProjectPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<"zip" | "github">("zip");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [repositoryRef, setRepositoryRef] = useState("main");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (mode === "zip" && !file) {
      setError("Choose a ZIP archive to continue.");
      return;
    }
    if (mode === "github" && !repositoryUrl) {
      setError("Enter a GitHub repository URL to continue.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (mode === "github") {
        const result = await api.github(repositoryUrl, repositoryRef);
        router.push(`/scans/${result.scan.id}`);
      } else {
        const project = await api.upload(file as File);
        router.push(`/projects/${project.id}`);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Upload failed.");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan">New analysis target</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Upload a project</h1>
        <p className="mt-2 text-sm leading-6 text-muted">Upload a backend ZIP. SecGraph will preprocess the code and build an index for analysis.</p>
      </div>
      <form onSubmit={submit} className="rounded-2xl border border-line bg-panel p-6">
        <div className="mb-6 grid grid-cols-2 rounded-lg border border-line bg-ink p-1">
          <button type="button" onClick={() => setMode("zip")} className={`rounded-md px-3 py-2 text-sm ${mode === "zip" ? "bg-panel2 text-cyan" : "text-muted"}`}>Upload ZIP</button>
          <button type="button" onClick={() => setMode("github")} className={`rounded-md px-3 py-2 text-sm ${mode === "github" ? "bg-panel2 text-cyan" : "text-muted"}`}>GitHub repository</button>
        </div>
        {mode === "github" ? (
          <div className="space-y-4">
            <label className="block">
              <span className="mb-2 block text-xs font-medium uppercase tracking-wider text-muted">Repository URL</span>
              <input value={repositoryUrl} onChange={(event) => setRepositoryUrl(event.target.value)} placeholder="https://github.com/owner/repository" className="w-full rounded-lg border border-line bg-ink px-3 py-3 text-sm text-white outline-none focus:border-cyan/60" />
            </label>
            <label className="block">
              <span className="mb-2 block text-xs font-medium uppercase tracking-wider text-muted">Branch or ref</span>
              <input value={repositoryRef} onChange={(event) => setRepositoryRef(event.target.value)} placeholder="main" className="w-full rounded-lg border border-line bg-ink px-3 py-3 text-sm text-white outline-none focus:border-cyan/60" />
            </label>
            <p className="text-xs leading-5 text-muted">The repository is downloaded into isolated project storage and scanned by the existing background pipeline.</p>
          </div>
        ) : (
        <label
          htmlFor="project-zip"
          className="flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-line bg-ink/50 px-6 py-16 text-center transition hover:border-cyan/50 hover:bg-cyan/[0.03]"
        >
          <div className="rounded-xl bg-cyan/10 p-4 text-cyan">
            {file ? <FileArchive size={28} /> : <UploadCloud size={28} />}
          </div>
          <p className="mt-5 text-sm font-medium text-white">
            {file ? file.name : "Choose a ZIP archive"}
          </p>
          <p className="mt-2 text-xs text-muted">Python backend projects · ZIP only</p>
          <input
            id="project-zip"
            type="file"
            accept=".zip,application/zip"
            className="sr-only"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        )}
        {error && <p className="mt-4 text-sm text-danger">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-3 text-sm font-semibold text-ink transition hover:bg-cyan/80 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? <><Loader2 size={16} className="animate-spin" /> {mode === "github" ? "Downloading..." : "Uploading..."}</> : mode === "github" ? "Connect and scan" : "Upload and inspect"}
        </button>
      </form>
    </div>
  );
}
