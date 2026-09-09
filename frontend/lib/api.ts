export type ScanStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export type Project = {
  id: string;
  name: string;
  source_type: string;
  backend_framework?: string | null;
  python_version?: string | null;
  created_at: string;
  updated_at: string;
};

export type Scan = {
  id: string;
  project_id: string;
  status: ScanStatus;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
};

export type Summary = {
  project_id: string;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  overall_security_score: number;
};

export type AIAnalysis = {
  id: string;
  decision: string;
  status: string;
  provider?: string | null;
  model?: string | null;
  ai_confidence?: number | null;
  response?: string | null;
  explanation_status?: string | null;
  structured_output?: {
    severity: string;
    confidence: number;
    explanation: string;
    potential_attack: string;
    impact: string;
    suggested_fix: string;
  } | null;
  validation_error?: string | null;
  created_at: string;
};

export type Finding = {
  id: string;
  project_id: string;
  rule_id: string;
  title: string;
  severity: string;
  confidence: number;
  file: string;
  line?: number | null;
  endpoint?: string | null;
  description: string;
  evidence: string;
  remediation: string;
  context_package: Record<string, unknown>;
  ai_analysis?: AIAnalysis | null;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options?.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...(process.env.NEXT_PUBLIC_API_KEY
        ? { "X-API-Key": process.env.NEXT_PUBLIC_API_KEY }
        : {}),
      ...options?.headers
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  projects: () => request<Project[]>("/projects"),
  project: (id: string) => request<ProjectDetail>(`/projects/${id}`),
  summary: (id: string) => request<Summary>(`/projects/${id}/summary`),
  scans: (id: string) => request<Scan[]>(`/projects/${id}/scans`),
  scan: (id: string) => request<Scan>(`/scans/${id}`),
  startScan: (id: string) =>
    request<Scan>(`/projects/${id}/scan`, { method: "POST" }),
  findings: (projectId?: string, params?: Record<string, string>) => {
    const query = new URLSearchParams(params);
    if (projectId) query.set("project_id", projectId);
    return request<Finding[]>(
      `/findings${query.toString() ? `?${query.toString()}` : ""}`
    );
  },
  finding: (id: string) => request<Finding>(`/findings/${id}`),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Project>("/projects/upload", {
      method: "POST",
      body: form
    });
  },
  github: (repository_url: string, repository_ref: string) =>
    request<{ project: Project; scan: Scan }>("/projects/github", {
      method: "POST",
      body: JSON.stringify({ repository_url, repository_ref })
    })
};

export type ProjectDetail = Project & {
  file_count: number;
  scan_count: number;
  latest_scan?: Scan | null;
};

export function formatDate(value?: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
