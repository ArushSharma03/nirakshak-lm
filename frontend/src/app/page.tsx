"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { getInspections, getAnalyticsData } from "@/lib/api";
import { InspectionRecord, AnalyticsSummary } from "@/types";
import ComplianceBadge from "@/components/common/ComplianceBadge";
import CategoryBadge from "@/components/common/CategoryBadge";
import StatCard from "@/components/common/StatCard";
import LegalDisclaimer from "@/components/common/LegalDisclaimer";

export default function DashboardPage() {
  const [inspections, setInspections] = useState<InspectionRecord[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    async function loadData() {
      const { records, isLive: liveStatus } = await getInspections();
      setInspections(records.slice(0, 5)); // show latest 5
      setIsLive(liveStatus);

      const stats = await getAnalyticsData();
      setAnalytics(stats);
    }
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Welcome Banner & Primary Inspection CTA */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-6 sm:p-8 text-white shadow-md border border-slate-700/80 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded-full bg-teal-500/20 text-teal-300 text-xs font-medium border border-teal-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-400" />
            <span>Legal Metrology (Packaged Commodities) Rules, 2011</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            Nirikshak-LM Inspector Console
          </h1>
          <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
            Evidence-calibrated multiview screening system for preliminary packaged-commodity compliance verification.
            Evaluate mandatory declarations, net quantity, MRP, and physical character-height ratios.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full md:w-auto shrink-0">
          <Link
            href="/inspect"
            className="inline-flex items-center justify-center space-x-2 px-6 py-3.5 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl transition-all shadow-lg hover:shadow-blue-500/25 text-sm"
          >
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <circle cx="12" cy="13" r="3" strokeWidth="2" />
            </svg>
            <span>Start Guided Multi-View Inspection</span>
          </Link>
          <Link
            href="/inspections/new"
            className="inline-flex items-center justify-center px-4 py-3.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600/80 font-medium rounded-xl transition-colors text-sm"
          >
            Manual Setup
          </Link>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Screenings"
          value={analytics ? analytics.totalInspections : "64"}
          subtitle="Packaged commodities audited"
          trend="+12% this month"
          trendType="positive"
          icon={
            <svg className="w-5 h-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          }
        />
        <StatCard
          title="Compliance Rate"
          value={analytics ? `${analytics.complianceRate}%` : "78.1%"}
          subtitle="Passed all implemented checks"
          trend="+3.2% vs baseline"
          trendType="positive"
          icon={
            <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          title="Potential Non-Compliance"
          value={analytics ? analytics.potentialViolations : "9"}
          subtitle="Statutory flags for physical review"
          trend="Flagged for inquiry"
          trendType="negative"
          icon={
            <svg className="w-5 h-5 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          }
        />
        <StatCard
          title="Manual Review Queue"
          value={analytics ? analytics.manualReviewQueue : "5"}
          subtitle="Unclear OCR or scale check"
          trend="Requires adjudication"
          trendType="neutral"
          icon={
            <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          }
        />
      </div>

      {/* Statutory Legal Disclaimer Banner */}
      <LegalDisclaimer />

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Recent Inspections Table (2 spans) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-xs flex flex-col">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Recent Compliance Screenings
              </h2>
              <p className="text-xs text-slate-500">
                {isLive ? "Live backend records" : "Showing verified demonstration sample dataset"}
              </p>
            </div>
            <Link
              href="/inspections"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center space-x-1"
            >
              <span>View All History</span>
              <span>&rarr;</span>
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/75 border-b border-slate-100 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Inspection ID</th>
                  <th className="py-3 px-4">Commodity / Brand</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4 text-center">Views (F/R/S)</th>
                  <th className="py-3 px-4">Compliance Outcome</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-normal">
                {inspections.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-medium text-slate-800">
                      {row.id}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">{row.productName}</div>
                      <div className="text-[11px] text-slate-500">{row.brand} &bull; {row.declaredNetQty}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <CategoryBadge category={row.productCategory} />
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span className="inline-flex space-x-1 font-mono text-[11px]">
                        <span className={row.viewsCaptured.front ? "text-emerald-600 font-bold" : "text-slate-300"}>F</span>
                        <span className="text-slate-300">/</span>
                        <span className={row.viewsCaptured.rear ? "text-emerald-600 font-bold" : "text-slate-300"}>R</span>
                        <span className="text-slate-300">/</span>
                        <span className={row.viewsCaptured.side ? "text-emerald-600 font-bold" : "text-slate-300"}>S</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <ComplianceBadge outcome={row.outcome} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <Link
                        href={`/inspections`}
                        className="inline-flex items-center px-2.5 py-1 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded transition-colors"
                      >
                        Inspect
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Categorical Distribution & Rule Base (1 span) */}
        <div className="space-y-6">
          {/* Category Scope Breakdown */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center justify-between">
              <span>Audited Category Scope</span>
              <span className="text-xs text-slate-400 font-normal">Approved Scope</span>
            </h3>

            <div className="space-y-3">
              {[
                { name: "Food and Grocery", count: 34, percent: "53%", color: "bg-blue-600" },
                { name: "Beverages", count: 12, percent: "19%", color: "bg-teal-500" },
                { name: "Personal Care Products", count: 11, percent: "17%", color: "bg-purple-500" },
                { name: "Household Commodities", count: 7, percent: "11%", color: "bg-indigo-500" },
              ].map((item) => (
                <div key={item.name} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-slate-700">{item.name}</span>
                    <span className="text-slate-500">{item.count} items ({item.percent})</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div className={`${item.color} h-1.5 rounded-full`} style={{ width: item.percent }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Legal Metrology Verification Suite */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-slate-900">
                LMPC 2011 Verified Checks
              </h3>
              <Link href="/rules" className="text-xs text-teal-600 hover:underline font-semibold">
                Explore All &rarr;
              </Link>
            </div>

            <ul className="text-xs space-y-2 text-slate-600">
              <li className="flex items-start space-x-2">
                <span className="text-teal-600 font-bold">&bull;</span>
                <span><strong>Rule 6(1)(a):</strong> Generic Name on Principal Display Panel</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-teal-600 font-bold">&bull;</span>
                <span><strong>Rule 6(1)(b):</strong> Net Quantity & standard metric unit validation</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-teal-600 font-bold">&bull;</span>
                <span><strong>Rule 6(1)(c):</strong> Complete Manufacturer / Packer postal identity</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-teal-600 font-bold">&bull;</span>
                <span><strong>Rule 6(1)(da):</strong> MRP format (incl. of all taxes) check</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-teal-600 font-bold">&bull;</span>
                <span><strong>Rule 5 / Sched. II:</strong> Character-height optical ratio estimation</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
