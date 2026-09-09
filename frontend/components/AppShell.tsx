"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  FolderKanban,
  LayoutDashboard,
  ShieldCheck,
  UploadCloud
} from "lucide-react";

const nav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/projects/upload", label: "Upload project", icon: UploadCloud }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-ink text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-line bg-[#0e1629] lg:block">
        <div className="flex h-20 items-center gap-3 border-b border-line px-7">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan text-ink">
            <ShieldCheck size={21} strokeWidth={2.5} />
          </div>
          <div>
            <div className="text-sm font-bold tracking-[0.18em] text-white">
              SECGRAPH
            </div>
            <div className="text-[10px] uppercase tracking-widest text-muted">
              API security
            </div>
          </div>
        </div>
        <nav className="space-y-1 px-4 py-7">
          <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-muted">
            Workspace
          </p>
          {nav.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                  active
                    ? "bg-cyan/10 font-medium text-cyan"
                    : "text-slate-400 hover:bg-white/5 hover:text-white"
                }`}
              >
                <Icon size={17} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="absolute bottom-7 left-5 right-5 rounded-xl border border-line bg-panel p-4">
          <div className="mb-2 flex items-center gap-2 text-xs font-medium text-slate-300">
            <Activity size={14} className="text-cyan" />
            Analysis engine
          </div>
          <p className="text-[11px] leading-5 text-muted">
            Static analysis active. AI is routed only for relevant findings.
          </p>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="flex h-20 items-center justify-between border-b border-line px-6 lg:px-10">
          <div className="lg:hidden">
            <Link href="/" className="font-bold tracking-[0.18em] text-cyan">
              SECGRAPH
            </Link>
          </div>
          <div className="ml-auto flex items-center gap-3 text-xs text-muted">
            <span className="h-2 w-2 rounded-full bg-cyan shadow-[0_0_12px_#5eead4]" />
            API connected
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] px-6 py-8 lg:px-10">
          {children}
        </main>
      </div>
    </div>
  );
}
