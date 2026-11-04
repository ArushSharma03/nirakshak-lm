"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

interface NavItem {
  name: string;
  href: string;
  icon: (active: boolean) => React.ReactNode;
  badge?: string;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

  const navItems: NavItem[] = [
    {
      name: "Dashboard",
      href: "/",
      icon: (active) => (
        <svg className={`w-5 h-5 ${active ? "text-teal-400" : "text-slate-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
    },
    {
      name: "New Inspection",
      href: "/inspections/new",
      icon: (active) => (
        <svg className={`w-5 h-5 ${active ? "text-teal-400" : "text-slate-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      ),
      badge: "Quick",
    },
    {
      name: "Guided Capture",
      href: "/inspect",
      icon: (active) => (
        <svg className={`w-5 h-5 ${active ? "text-teal-400" : "text-slate-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
          <circle cx="12" cy="13" r="3" strokeWidth="2" />
        </svg>
      ),
    },
    {
      name: "Inspection History",
      href: "/inspections",
      icon: (active) => (
        <svg className={`w-5 h-5 ${active ? "text-teal-400" : "text-slate-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
        </svg>
      ),
    },
    {
      name: "Compliance Rules",
      href: "/rules",
      icon: (active) => (
        <svg className={`w-5 h-5 ${active ? "text-teal-400" : "text-slate-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
      ),
      badge: "LMPC",
    },
    {
      name: "Product Catalog",
      href: "/products",
      icon: (active) => (
        <svg className={`w-5 h-5 ${active ? "text-teal-400" : "text-slate-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
      ),
    },
    {
      name: "Analytics & Trends",
      href: "/analytics",
      icon: (active) => (
        <svg className={`w-5 h-5 ${active ? "text-teal-400" : "text-slate-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
    },
    {
      name: "Reports Hub",
      href: "/reports",
      icon: (active) => (
        <svg className={`w-5 h-5 ${active ? "text-teal-400" : "text-slate-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
    },
    {
      name: "System Settings",
      href: "/settings",
      icon: (active) => (
        <svg className={`w-5 h-5 ${active ? "text-teal-400" : "text-slate-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <circle cx="12" cy="12" r="3" strokeWidth="2" />
        </svg>
      ),
    },
  ];

  return (
    <aside
      className={`bg-slate-900 text-slate-100 flex flex-col transition-all duration-300 ease-in-out shrink-0 border-r border-slate-800 ${
        collapsed ? "w-18" : "w-64"
      }`}
    >
      {/* Brand & Collapse Header */}
      <div className="h-16 px-4 flex items-center justify-between border-b border-slate-800">
        {!collapsed && (
          <Link href="/" className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center font-bold text-sm tracking-wider">
              NL
            </div>
            <div>
              <span className="font-bold text-sm tracking-wide text-white block">
                Nirikshak-LM
              </span>
              <span className="text-[10px] text-teal-400 font-medium block -mt-0.5">
                Compliance Screening
              </span>
            </div>
          </Link>
        )}

        {collapsed && (
          <Link href="/" className="mx-auto">
            <div className="w-8 h-8 rounded-lg bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center font-bold text-xs">
              NL
            </div>
          </Link>
        )}

        <button
          onClick={onToggle}
          title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800 transition-colors hidden md:block"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {collapsed ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            )}
          </svg>
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));

          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? "bg-slate-800 text-teal-300 shadow-xs border-l-2 border-teal-400"
                  : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
              } ${collapsed ? "justify-center" : "justify-between"}`}
              title={collapsed ? item.name : undefined}
            >
              <div className="flex items-center space-x-3">
                <span className="shrink-0">{item.icon(isActive)}</span>
                {!collapsed && <span className="truncate">{item.name}</span>}
              </div>

              {!collapsed && item.badge && (
                <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-slate-800 text-teal-400 border border-slate-700">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800 text-[11px] text-slate-400">
        {!collapsed ? (
          <div>
            <div className="flex items-center justify-between text-slate-300 mb-1">
              <span className="font-semibold">Legal Metrology 2011</span>
              <span className="text-[10px] bg-teal-950 text-teal-400 px-1 rounded border border-teal-800">
                v2026.1
              </span>
            </div>
            <p className="text-slate-400 text-[10px]">B.Tech CSE Minor Project Group 27</p>
          </div>
        ) : (
          <div className="text-center text-[10px] text-teal-400 font-mono">G27</div>
        )}
      </div>
    </aside>
  );
}
