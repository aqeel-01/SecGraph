"use client";

import Link from "next/link";
import { ArrowRight, FolderKanban, Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";

import { api, type Project } from "@/lib/api";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.projects().then(setProjects).catch((reason: Error) => setError(reason.message));
  }, []);

  const filtered = projects.filter((project) =>
    project.name.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-7">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan">Workspace</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Projects</h1>
          <p className="mt-2 text-sm text-muted">Manage codebases and review their security posture.</p>
        </div>
        <Link
          href="/projects/upload"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-2.5 text-sm font-semibold text-ink"
        >
          <Plus size={16} /> Upload project
        </Link>
      </div>
      <div className="flex max-w-sm items-center gap-3 rounded-lg border border-line bg-panel px-3 py-2.5">
        <Search size={16} className="text-muted" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search projects..."
          className="w-full bg-transparent text-sm text-white outline-none placeholder:text-muted"
        />
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((project) => (
          <Link
            key={project.id}
            href={`/projects/${project.id}`}
            className="group rounded-xl border border-line bg-panel p-5 transition hover:border-cyan/40 hover:bg-panel2"
          >
            <div className="flex items-start justify-between">
              <div className="rounded-xl bg-cyan/10 p-3 text-cyan">
                <FolderKanban size={21} />
              </div>
              <ArrowRight size={17} className="text-muted transition group-hover:text-cyan" />
            </div>
            <h2 className="mt-6 font-semibold text-white">{project.name}</h2>
            <p className="mt-2 text-xs text-muted">{project.source_type} · {project.backend_framework ?? "Framework pending"}</p>
            <div className="mt-6 flex items-center justify-between border-t border-line pt-4 text-xs text-muted">
              <span>Python {project.python_version ?? "—"}</span>
              <span>{new Date(project.created_at).toLocaleDateString()}</span>
            </div>
          </Link>
        ))}
      </div>
      {!filtered.length && <div className="rounded-xl border border-line bg-panel px-5 py-16 text-center text-sm text-muted">No projects found.</div>}
    </div>
  );
}
