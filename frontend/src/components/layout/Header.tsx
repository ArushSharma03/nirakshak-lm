"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { checkBackendStatus } from "@/lib/api";
import { SystemStatus } from "@/types";

interface HeaderProps {
  onToggleMobileMenu: () => void;
}

export default function Header({ onToggleMobileMenu }: HeaderProps) {
  const pathname = usePathname();
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    isLive: false,
    backendVersion: undefined,
    databaseAvailable: false,
    mode: "Demonstrator Mode",
  });

  useEffect(() => {
    async function loadStatus() {
      const status = await checkBackendStatus();
      setSystemStatus(status);
    }
    loadStatus();

    // Check status periodically
    const interval = setInterval(loadStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  // Generate breadcrumb title
  const getBreadcrumb = () => {
    if (pathname === "/") return "Executive Inspection Dashboard";
    if (pathname.startsWith("/inspections/new")) return "Inspections > New Inspection Setup";
    if (pathname.startsWith("/inspections")) return "Inspections > Repository Archive";
    if (pathname.startsWith("/inspect")) return "Live Screening > Guided Multi-View Capture";
    if (pathname.startsWith("/rules")) return "Legal Metrology Rules > Statutory Knowledge Base";
    if (pathname.startsWith("/products")) return "Commodities > Packaged Product Catalog";
    if (pathname.startsWith("/analytics")) return "Analytics > Compliance Intelligence";
    if (pathname.startsWith("/reports")) return "Audit Reports > Official Memo Export";
    if (pathname.startsWith("/settings")) return "Configuration > System & Scale Calibration";
    return "Nirikshak-LM";
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between z-10 shrink-0 shadow-xs">
      {/* Left: Mobile Toggle & Breadcrumb */}
      <div className="flex items-center space-x-3">
        <button
          onClick={onToggleMobileMenu}
          className="p-1.5 rounded-lg text-slate-600 hover:bg-slate-100 md:hidden"
          title="Open Navigation Menu"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <div>
          <h2 className="text-sm sm:text-base font-semibold text-slate-800 tracking-tight flex items-center space-x-1.5">
            <span>{getBreadcrumb()}</span>
          </h2>
          <p className="text-[11px] text-slate-400 hidden sm:block">
            Legal Metrology (Packaged Commodities) Compliance Screening
          </p>
        </div>
      </div>

      {/* Right: Mode Indicator + Inspector Badge + Quick Action */}
      <div className="flex items-center space-x-3 sm:space-x-4">
        {/* System Mode Indicator Pill */}
        <div
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium border shadow-2xs ${
            systemStatus.isLive
              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
              : "bg-teal-50 text-teal-800 border-teal-200"
          }`}
          title={
            systemStatus.isLive
              ? `FastAPI backend active (${systemStatus.backendVersion})`
              : "Backend offline — running safely in offline demonstrator mode with sample commodities"
          }
        >
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              systemStatus.isLive ? "bg-emerald-500 animate-pulse" : "bg-teal-600"
            }`}
          />
          <span className="hidden md:inline font-medium">
            {systemStatus.isLive ? "Live Backend" : "Demonstrator Mode"}
          </span>
          <span className="md:hidden font-medium">
            {systemStatus.isLive ? "Live" : "Demo"}
          </span>
        </div>

        {/* Quick Launch CTA */}
        {pathname !== "/inspect" && (
          <Link
            href="/inspect"
            className="hidden sm:inline-flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition-colors shadow-xs"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>Start Capture</span>
          </Link>
        )}

        {/* Inspector Identity Badge */}
        <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-slate-900 text-teal-300 font-semibold text-xs flex items-center justify-center border border-slate-700">
            AS
          </div>
          <div className="hidden lg:block text-left text-xs">
            <span className="font-semibold text-slate-800 block leading-tight">
              Mr. Arush Sharma
            </span>
            <span className="text-[10px] text-slate-500 block leading-tight">
              Lead Inspector (Grp 27)
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
