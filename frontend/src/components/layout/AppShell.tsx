"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { checkBackendStatus } from "@/lib/api";
import { Icon, type IconName } from "@/components/ui";
import { TopBarTarget } from "./TopBarContent";
import type { SystemStatus } from "@/types";

interface NavItem {
  href: string;
  label: string;
  icon: IconName;
  match: (path: string) => boolean;
}

const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "Screening",
    items: [
      { href: "/", label: "Dashboard", icon: "home", match: (p) => p === "/" },
      { href: "/inspections/new", label: "New inspection", icon: "plus", match: (p) => p.startsWith("/inspections/new") },
      { href: "/inspect", label: "Guided capture", icon: "camera", match: (p) => p === "/inspect" },
      { href: "/inspections", label: "Inspection history", icon: "history", match: (p) => p === "/inspections" },
      { href: "/reports", label: "Reports", icon: "report", match: (p) => p.startsWith("/reports") },
    ],
  },
  {
    label: "Reference",
    items: [
      { href: "/rules", label: "Compliance rules", icon: "book", match: (p) => p.startsWith("/rules") },
      { href: "/products", label: "Product catalog", icon: "box", match: (p) => p.startsWith("/products") },
      { href: "/analytics", label: "Analytics", icon: "chart", match: (p) => p.startsWith("/analytics") },
      { href: "/settings", label: "System", icon: "system", match: (p) => p.startsWith("/settings") },
    ],
  },
];

const TITLES: [string, string, string][] = [
  ["/inspections/new", "New inspection", "Inspections"],
  ["/inspections", "Inspection history", "Inspections"],
  ["/inspect", "Guided capture", "Inspections"],
  ["/reports", "Reports", "Inspections"],
  ["/rules", "Compliance rules", "Reference"],
  ["/products", "Product catalog", "Reference"],
  ["/analytics", "Analytics", "Reference"],
  ["/settings", "System", "Reference"],
];

function pageTitle(path: string): [string, string | null] {
  if (path === "/") return ["Dashboard", null];
  const hit = TITLES.find(([prefix]) => path.startsWith(prefix));
  return hit ? [hit[1], hit[2]] : ["Nirikshak-LM", null];
}

function useApiStatus() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      const next = await checkBackendStatus();
      if (alive) setStatus(next);
    };
    void load();
    const timer = setInterval(load, 20000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);
  return status;
}

function ApiStatus({ status }: { status: SystemStatus | null }) {
  const label = status === null ? "Checking API" : status.isLive ? "API online" : "API offline";
  const style = status !== null && !status.isLive ? "text-danger" : "text-ink-2";
  return (
    <Link
      href="/settings"
      aria-live="polite"
      title={status?.isLive ? `Backend ${status.backendVersion ?? ""} on port 8000`.trim() : "Inspections cannot be loaded or saved until the backend responds."}
      className={`inline-flex min-h-8 shrink-0 items-center gap-2 whitespace-nowrap text-xs ${style}`}
    >
      <span>{label}</span>
      {status?.isLive && status.backendVersion && <span className="serial hidden opacity-70 lg:inline">v{status.backendVersion}</span>}
    </Link>
  );
}

function Sidebar({ collapsed, onToggle, onNavigate, mobile = false }: { collapsed: boolean; onToggle: () => void; onNavigate?: () => void; mobile?: boolean }) {
  const pathname = usePathname();
  return (
    <aside className={`flex h-full flex-col border-r border-rail-line bg-rail text-slate-300 transition-[width] duration-200 ease-out ${collapsed ? "w-[4.25rem]" : "w-64"}`}>
      <div className={`flex h-16 shrink-0 items-center border-b border-rail-line px-4 ${collapsed ? "justify-center" : "justify-between"}`}>
        <Link href="/" onClick={onNavigate} className="flex items-center gap-2.5" aria-label="Nirikshak-LM dashboard">
          <span aria-hidden="true" className="grid size-8 place-items-center rounded-md bg-rail-2 text-xs font-semibold text-slate-200">
            NL
          </span>
          {!collapsed && (
            <span className="leading-tight">
              <span className="block text-sm font-bold text-white">Nirikshak-LM</span>
              <span className="block text-[11px] text-slate-400">Package label screening</span>
            </span>
          )}
        </Link>
        {mobile ? (
          <button type="button" onClick={onToggle} aria-label="Close navigation" className="grid size-9 place-items-center rounded-md text-slate-400 hover:bg-rail-2 hover:text-white">
            <Icon name="close" />
          </button>
        ) : (
          !collapsed && (
            <button type="button" onClick={onToggle} aria-label="Collapse sidebar" title="Collapse sidebar" className="grid size-8 place-items-center rounded-md text-slate-400 hover:bg-rail-2 hover:text-white">
              <Icon name="collapse" />
            </button>
          )
        )}
      </div>

      <nav aria-label="Main" className="flex-1 space-y-5 overflow-y-auto px-2.5 py-4">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="space-y-0.5">
            {!collapsed && <p className="px-3 pb-1 text-[11px] font-medium text-slate-500">{group.label}</p>}
            {group.items.map((item) => {
              const active = item.match(pathname);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  title={collapsed ? item.label : undefined}
                  className={`flex min-h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors ${collapsed ? "justify-center" : ""} ${
                    active ? "bg-rail-2 text-white" : "text-slate-400 hover:bg-rail-2/60 hover:text-slate-100"
                  }`}
                >
                  <Icon name={item.icon} className={`size-[1.15rem] ${active ? "text-white" : ""}`} />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="shrink-0 border-t border-rail-line p-3">
        {collapsed ? (
          <button type="button" onClick={onToggle} aria-label="Expand sidebar" title="Expand sidebar" className="mx-auto grid size-9 place-items-center rounded-md text-slate-400 hover:bg-rail-2 hover:text-white">
            <Icon name="expand" />
          </button>
        ) : (
          <div className="space-y-0.5 px-1 text-[11px] leading-relaxed">
            <p className="font-medium text-slate-300">Legal Metrology (Packaged Commodities) Rules, 2011</p>
            <p className="text-slate-500">B.Tech CSE minor project, Group 27</p>
          </div>
        )}
      </div>
    </aside>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const status = useApiStatus();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [title] = pageTitle(pathname);
  const [topBarTarget, setTopBarTarget] = useState<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setMobileOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileOpen]);


  return (
    <TopBarTarget value={topBarTarget}>
    <div className="flex h-dvh overflow-hidden bg-ground print:block print:h-auto print:overflow-visible">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-[60] focus:rounded-md focus:bg-sheet focus:px-3 focus:py-2">
        Skip to content
      </a>

      <div className="hidden md:flex print:hidden">
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden print:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div className="relative z-10 h-full">
            <Sidebar collapsed={false} mobile onToggle={() => setMobileOpen(false)} onNavigate={() => setMobileOpen(false)} />
          </div>
          <button type="button" aria-label="Close navigation" onClick={() => setMobileOpen(false)} className="flex-1 bg-slate-900/50" />
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden print:overflow-visible">
        <header className="shell-header shrink-0 border-b border-rule bg-sheet print:hidden">
          <div className="page-container flex min-h-16 items-start gap-3 py-3">
            <button type="button" onClick={() => setMobileOpen(true)} aria-label="Open navigation" className="-ml-1.5 grid size-10 shrink-0 place-items-center rounded-lg text-ink-2 hover:bg-ground md:hidden">
              <Icon name="menu" className="size-5" />
            </button>
            <div className="topbar-page min-w-0 flex-1">
              <h1 className="topbar-fallback py-2 text-base font-semibold text-ink">{title}</h1>
              <div ref={setTopBarTarget} className="topbar-slot" />
            </div>
            <ApiStatus status={status} />
          </div>
        </header>

        <main id="main" className="flex-1 overflow-y-auto print:overflow-visible">
          <div className="page-container py-6">{children}</div>
          <footer className="page-container pb-6 print:hidden">
            <p className="border-t border-rule pt-4 text-xs leading-relaxed text-ink-3">
              Screening support only. Readings come from OCR and need an authorised inspector&rsquo;s physical verification. Nothing here is a statutory finding under the Legal Metrology Act, 2009.
            </p>
          </footer>
        </main>
      </div>
    </div>
    </TopBarTarget>
  );
}
