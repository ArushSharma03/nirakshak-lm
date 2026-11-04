"use client";

import React, { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { getInspections } from "@/lib/api";
import { InspectionRecord } from "@/types";
import ComplianceBadge from "@/components/common/ComplianceBadge";
import CategoryBadge from "@/components/common/CategoryBadge";
import LegalDisclaimer from "@/components/common/LegalDisclaimer";

function InspectionsHistoryContent() {
  const searchParams = useSearchParams();
  const highlightId = searchParams.get("highlight");

  const [records, setRecords] = useState<InspectionRecord[]>([]);
  const [isLiveRepo, setIsLiveRepo] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedOutcome, setSelectedOutcome] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [activeRecord, setActiveRecord] = useState<InspectionRecord | null>(null);

  useEffect(() => {
    async function loadData() {
      const { records: list, isLive } = await getInspections();
      setRecords(list);
      setIsLiveRepo(isLive);

      if (highlightId) {
        const found = list.find((r) => r.id === highlightId);
        if (found) {
          setActiveRecord(found);
        }
      }
    }
    loadData();
  }, [highlightId]);

  const filteredRecords = records.filter((r) => {
    const matchesSearch =
      r.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.productName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.brand.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesOutcome =
      selectedOutcome === "ALL" || r.outcome === selectedOutcome;

    const matchesCategory =
      selectedCategory === "ALL" || r.productCategory === selectedCategory;

    return matchesSearch && matchesOutcome && matchesCategory;
  });

  return (
    <div className="space-y-6">
      {/* Page Title & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Inspection History & Audit Repository
            </h1>
            <span
              className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold uppercase tracking-wider ${
                isLiveRepo
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                  : "bg-amber-100 text-amber-800 border border-amber-300"
              }`}
            >
              {isLiveRepo ? "Live Repository" : "Demo / Offline Fallback"}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Searchable regulatory archive of multi-view packaged-commodity screenings under Legal Metrology Rules.
          </p>
        </div>

        <Link
          href="/inspections/new"
          className="inline-flex items-center space-x-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg text-sm transition-colors shadow-xs"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span>New Inspection</span>
        </Link>
      </div>

      <LegalDisclaimer compact />

      {/* Filter and Search Controls */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-col md:flex-row items-stretch md:items-center gap-4">
        {/* Search */}
        <div className="flex-1 relative">
          <svg className="w-4 h-4 text-slate-400 absolute left-3 top-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by ID, product, or brand (e.g. Britannia, Amul, INS-2026)..."
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs sm:text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20"
          />
        </div>

        {/* Outcome Filter */}
        <div className="shrink-0 flex items-center space-x-2">
          <span className="text-xs font-semibold text-slate-500">Outcome:</span>
          <select
            value={selectedOutcome}
            onChange={(e) => setSelectedOutcome(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs font-medium text-slate-800"
          >
            <option value="ALL">All Outcomes</option>
            <option value="Compliant within Implemented Checks">Compliant</option>
            <option value="Potential Non-Compliance">Potential Non-Compliance</option>
            <option value="Manual Review Required">Manual Review</option>
          </select>
        </div>

        {/* Category Filter */}
        <div className="shrink-0 flex items-center space-x-2">
          <span className="text-xs font-semibold text-slate-500">Category:</span>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs font-medium text-slate-800"
          >
            <option value="ALL">All Categories</option>
            <option value="food_grocery">Food and Grocery</option>
            <option value="beverage">Beverages</option>
            <option value="personal_care">Personal Care</option>
            <option value="household">Household</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Inspection ID</th>
                <th className="py-3 px-4">Commodity / Brand</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Scale / Marker</th>
                <th className="py-3 px-4 text-center">Panels (F/R/S)</th>
                <th className="py-3 px-4">Compliance Outcome</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-normal">
              {filteredRecords.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 text-sm">
                    No inspections found matching your search and filter criteria.
                  </td>
                </tr>
              ) : (
                filteredRecords.map((r) => (
                  <tr
                    key={r.id}
                    className={`hover:bg-slate-50/80 transition-colors ${
                      highlightId === r.id ? "bg-blue-50/50" : ""
                    }`}
                  >
                    <td className="py-3.5 px-4 font-mono font-medium text-slate-900">
                      <div className="flex items-center space-x-1.5">
                        <span>{r.id}</span>
                        {r.mode && (
                          <span
                            className="text-[9px] px-1 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200"
                            title={r.mode}
                          >
                            {r.databaseSaved ? "DB" : "Local"}
                          </span>
                        )}
                      </div>
                      <span className="block text-[10px] text-slate-400 font-sans mt-0.5">
                        {new Date(r.timestamp).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">{r.productName}</div>
                      <div className="text-[11px] text-slate-500">
                        {r.brand} &bull; Net: {r.declaredNetQty} &bull; MRP: ₹{r.declaredMRP}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <CategoryBadge category={r.productCategory} />
                    </td>
                    <td className="py-3.5 px-4">
                      {r.markerDetected ? (
                        <span className="inline-flex items-center text-emerald-700 text-[11px] font-medium">
                          <svg className="w-3.5 h-3.5 mr-1" fill="currentColor" viewBox="0 0 20 20">
                            <path
                              fillRule="evenodd"
                              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                              clipRule="evenodd"
                            />
                          </svg>
                          {r.scalePpm ? `${r.scalePpm} px/mm` : "Calibrated"}
                        </span>
                      ) : (
                        <span className="inline-flex items-center text-amber-700 text-[11px] font-medium">
                          <svg className="w-3.5 h-3.5 mr-1" fill="currentColor" viewBox="0 0 20 20">
                            <path
                              fillRule="evenodd"
                              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                              clipRule="evenodd"
                            />
                          </svg>
                          No Scale
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span className="inline-flex space-x-1 font-mono text-[11px]">
                        <span className={r.viewsCaptured.front ? "text-emerald-600 font-bold" : "text-slate-300"}>
                          F
                        </span>
                        <span className="text-slate-300">/</span>
                        <span className={r.viewsCaptured.rear ? "text-emerald-600 font-bold" : "text-slate-300"}>
                          R
                        </span>
                        <span className="text-slate-300">/</span>
                        <span className={r.viewsCaptured.side ? "text-emerald-600 font-bold" : "text-slate-300"}>
                          S
                        </span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <ComplianceBadge outcome={r.outcome} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-1.5">
                      <button
                        onClick={() => setActiveRecord(r)}
                        className="px-2.5 py-1 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded transition-colors"
                      >
                        Inspect
                      </button>
                      <Link
                        href={`/reports?id=${encodeURIComponent(r.id)}`}
                        className="px-2.5 py-1 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded transition-colors"
                      >
                        Memo
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Slide-over Inspection Detail Drawer */}
      {activeRecord && (
        <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
          <div
            className="fixed inset-0 bg-slate-900/50 backdrop-blur-2xs transition-opacity"
            onClick={() => setActiveRecord(null)}
          />

          <div className="relative w-full max-w-lg bg-white shadow-2xl z-10 p-6 flex flex-col justify-between overflow-y-auto">
            <div className="space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono font-medium text-slate-500">
                      {activeRecord.id}
                    </span>
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold ${
                        activeRecord.databaseSaved
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {activeRecord.mode || (activeRecord.databaseSaved ? "Live DB" : "Demo Store")}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                    {activeRecord.productName}
                  </h3>
                </div>
                <button
                  onClick={() => setActiveRecord(null)}
                  className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                >
                  &times;
                </button>
              </div>

              {/* Status & Outcome */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                  Preliminary Compliance Verdict
                </span>
                <ComplianceBadge outcome={activeRecord.outcome} size="md" />
              </div>

              {/* Optical Evidence Plates (Real Captured Thumbnails) */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                  Captured Multi-View Optical Evidence
                </span>
                <div className="grid grid-cols-3 gap-2">
                  {(["front", "rear", "side"] as const).map((vt) => {
                    const img = activeRecord.images?.[vt];
                    const isCaptured = activeRecord.viewsCaptured[vt] || !!img;
                    return (
                      <div key={vt} className="border border-slate-200 rounded-lg p-2 bg-slate-50 text-center space-y-1">
                        <div className="aspect-[4/3] bg-slate-200 rounded overflow-hidden flex items-center justify-center relative">
                          {img?.previewUrl ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={img.previewUrl} alt={`${vt} view`} className="w-full h-full object-cover" />
                          ) : isCaptured ? (
                            <span className="text-[10px] text-emerald-700 font-semibold">Captured</span>
                          ) : (
                            <span className="text-[10px] text-slate-400">Missing</span>
                          )}
                        </div>
                        <span className="text-[10px] font-bold text-slate-700 uppercase block">
                          {vt} View
                        </span>
                        <div className="flex flex-col text-[9px] text-slate-500 space-y-0.5">
                          <span>{img?.marker_detected ? "Marker Calibrated" : isCaptured ? "Uploaded" : "Pending"}</span>
                          {img?.quality_assessment && (
                            <span
                              className={`font-semibold ${
                                img.quality_assessment.overall_status === "Pass"
                                  ? "text-emerald-700"
                                  : img.quality_assessment.overall_status === "Warning"
                                  ? "text-amber-700"
                                  : "text-rose-700"
                              }`}
                            >
                              Quality: {img.quality_assessment.overall_status}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Details Grid */}
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 space-y-2.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Brand / Manufacturer:</span>
                  <span className="font-semibold text-slate-800">{activeRecord.brand}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Declared Net Quantity:</span>
                  <span className="font-semibold text-slate-800">{activeRecord.declaredNetQty}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Declared MRP:</span>
                  <span className="font-semibold text-slate-800">₹{activeRecord.declaredMRP.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Scale Calibration:</span>
                  <span className="font-semibold text-slate-800">
                    {activeRecord.scalePpm ? `${activeRecord.scalePpm} px/mm (ArUco 50mm)` : "Unavailable"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Designated Inspector:</span>
                  <span className="font-semibold text-slate-800">{activeRecord.inspectorName}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Screening Timestamp:</span>
                  <span className="font-semibold text-slate-800">
                    {new Date(activeRecord.timestamp).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Verified Checks List */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                  Screening Summary
                </span>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 space-y-1">
                  <div className="flex justify-between font-medium">
                    <span>Passed Implemented Checks:</span>
                    <span className="text-emerald-600 font-bold">
                      {activeRecord.checksPassed} / {activeRecord.totalChecks}
                    </span>
                  </div>
                  <div className="flex justify-between font-medium">
                    <span>Flagged Non-Compliances:</span>
                    <span className="text-rose-600 font-bold">{activeRecord.violationsCount}</span>
                  </div>
                </div>
              </div>

              <LegalDisclaimer compact />
            </div>

            <div className="pt-4 border-t border-slate-200 flex gap-3">
              <Link
                href={`/reports?id=${encodeURIComponent(activeRecord.id)}`}
                className="flex-1 py-2 text-center bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold"
              >
                Generate Audit Memo &rarr;
              </Link>
              <button
                onClick={() => setActiveRecord(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function InspectionsHistoryPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-500 text-sm">Loading inspection archive...</div>}>
      <InspectionsHistoryContent />
    </Suspense>
  );
}
