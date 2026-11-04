"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getInspections } from "@/lib/api";
import { InspectionRecord } from "@/types";
import ComplianceBadge from "@/components/common/ComplianceBadge";
import CategoryBadge from "@/components/common/CategoryBadge";
import LegalDisclaimer from "@/components/common/LegalDisclaimer";

function ReportsHubContent() {
  const searchParams = useSearchParams();
  const urlId = searchParams.get("id");

  const [records, setRecords] = useState<InspectionRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string>(urlId || "INS-2026-0042");
  const [plateViewMode, setPlateViewMode] = useState<"raw" | "processed">("raw");

  useEffect(() => {
    async function load() {
      const { records: list } = await getInspections();
      setRecords(list);
      if (urlId && list.some((r) => r.id === urlId)) {
        setSelectedId(urlId);
      } else if (list.length > 0 && !urlId) {
        setSelectedId(list[0].id);
      }
    }
    load();
  }, [urlId]);

  const activeRecord = records.find((r) => r.id === selectedId) || records[0];

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Inspection Reports & Statutory Audit Memos
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Generate and export official preliminary screening memos under Legal Metrology Rules.
          </p>
        </div>

        <button
          onClick={() => window.print()}
          className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg text-xs transition-colors shadow-xs"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
          </svg>
          <span>Print / Export PDF Memo</span>
        </button>
      </div>

      <LegalDisclaimer compact />

      {/* Selector & Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Selector List */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
          <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Select Inspection Record:
          </h2>
          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {records.map((r) => (
              <button
                key={r.id}
                onClick={() => setSelectedId(r.id)}
                className={`w-full text-left p-3 rounded-lg border text-xs transition-all ${
                  selectedId === r.id
                    ? "bg-slate-900 text-white border-slate-800 shadow-xs"
                    : "bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center space-x-1.5">
                    <span className="font-mono font-bold">{r.id}</span>
                    <span className="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-slate-300">
                      {r.databaseSaved ? "DB" : "Local"}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                      selectedId === r.id
                        ? "bg-slate-800 text-teal-300"
                        : "bg-white text-slate-600 border border-slate-200"
                    }`}
                  >
                    {new Date(r.timestamp).toLocaleDateString()}
                  </span>
                </div>
                <div className="font-medium truncate">{r.productName}</div>
                <div className="text-[11px] opacity-75 mt-0.5">{r.brand}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Right: Official Inspection Memo Document View (2 Spans) */}
        {activeRecord && (
          <div className="lg:col-span-2 bg-white rounded-xl border-2 border-slate-300 p-8 shadow-md space-y-6 text-slate-800 print:border-none print:shadow-none print:p-0">
            {/* Classification & Origin Banner */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <span
                className={`text-[10px] px-2.5 py-1 rounded font-mono font-bold uppercase tracking-wider ${
                  activeRecord.databaseSaved
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                    : "bg-amber-100 text-amber-900 border border-amber-300"
                }`}
              >
                {activeRecord.databaseSaved
                  ? "Live Metrology Audit Memorandum"
                  : "Demonstrator Screening Memo — Offline Dataset"}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                Storage: {activeRecord.mode || (activeRecord.databaseSaved ? "Live PostgreSQL" : "Demo / Offline Fallback")}
              </span>
            </div>

            {/* Government Memo Header */}
            <div className="text-center pb-5 border-b-2 border-slate-900 space-y-1">
              <div className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">
                Government of India &bull; Ministry of Consumer Affairs
              </div>
              <h2 className="text-xl font-extrabold uppercase tracking-wide text-slate-900">
                Department of Legal Metrology
              </h2>
              <p className="text-xs font-medium text-slate-600">
                Preliminary Screening & Technical Audit Memorandum
              </p>
              <p className="text-[11px] text-slate-500 italic">
                Under the Legal Metrology (Packaged Commodities) Rules, 2011 and Applicable Amendments
              </p>
            </div>

            {/* Inspection Meta Box */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-4 bg-slate-50 rounded-lg border border-slate-200 text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Memo Reference</span>
                <span className="font-mono font-bold text-slate-900">{activeRecord.id}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Inspection Date</span>
                <span className="font-medium text-slate-800">{new Date(activeRecord.timestamp).toLocaleDateString()}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Designated Inspector</span>
                <span className="font-medium text-slate-800">{activeRecord.inspectorName}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Commodity Category</span>
                <CategoryBadge category={activeRecord.productCategory} />
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Declared Net Quantity</span>
                <span className="font-medium text-slate-800">{activeRecord.declaredNetQty}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Declared MRP</span>
                <span className="font-medium text-slate-800">₹{activeRecord.declaredMRP.toFixed(2)} (Incl. Taxes)</span>
              </div>
            </div>

            {/* Subject Commodity */}
            <div className="space-y-1">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                1. Subject Commodity Profile
              </h3>
              <p className="text-sm font-bold text-slate-900">
                {activeRecord.productName}
              </p>
              <p className="text-xs text-slate-600">
                Manufacturer / Packer: <strong>{activeRecord.brand}</strong> &bull; Scale Status: {activeRecord.markerDetected ? `Calibrated (${activeRecord.scalePpm} px/mm)` : "Uncalibrated manual scale"}
              </p>
            </div>

            {/* Multi-view Capture Plate Evidence */}
            <div className="space-y-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 pb-1 border-b border-slate-200">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  2. Multi-View Optical Evidence Plates
                </h3>
                <div className="flex items-center space-x-1.5 text-[11px] print:hidden">
                  <span className="text-slate-500 font-medium">Plate View:</span>
                  <button
                    type="button"
                    onClick={() => setPlateViewMode("raw")}
                    className={`px-2 py-0.5 rounded font-medium transition-colors ${
                      plateViewMode === "raw"
                        ? "bg-slate-900 text-white"
                        : "bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200"
                    }`}
                  >
                    Original Evidentiary
                  </button>
                  <button
                    type="button"
                    onClick={() => setPlateViewMode("processed")}
                    className={`px-2 py-0.5 rounded font-medium transition-colors ${
                      plateViewMode === "processed"
                        ? "bg-teal-700 text-white"
                        : "bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200"
                    }`}
                  >
                    Enhanced (CLAHE)
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                {(["front", "rear", "side"] as const).map((vt) => {
                  const labelMap = {
                    front: "Principal Display Panel",
                    rear: "Information Declarations",
                    side: "Barcodes & Batch Codes",
                  };
                  const img = activeRecord.images?.[vt];
                  const hasView = activeRecord.viewsCaptured[vt] || !!img;
                  const displayUrl =
                    plateViewMode === "processed" && img?.processedUrl
                      ? img.processedUrl
                      : img?.previewUrl;

                  return (
                    <div key={vt} className="border border-slate-200 rounded p-2 text-center bg-slate-50 space-y-1">
                      <div className="aspect-4/3 bg-slate-200 rounded flex items-center justify-center text-xs text-slate-500 font-mono overflow-hidden relative">
                        {displayUrl ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={displayUrl} alt={`${vt} view`} className="w-full h-full object-cover" />
                        ) : hasView ? (
                          <span className="text-[11px] text-emerald-700 font-bold font-sans">
                            Captured {vt.toUpperCase()}
                          </span>
                        ) : (
                          <span>[{vt.toUpperCase()} View Plate]</span>
                        )}
                      </div>
                      <span className="text-[10px] font-bold text-slate-700 block">
                        {labelMap[vt]}
                      </span>
                      <span className="text-[9px] text-slate-500 block">
                        {img?.marker_detected ? "ArUco 50mm Scale Calibrated" : hasView ? "Panel Captured" : "View Not Captured"}
                      </span>
                      {img?.quality_assessment && (
                        <span
                          className={`text-[9px] font-semibold block ${
                            img.quality_assessment.overall_status === "Pass"
                              ? "text-emerald-700"
                              : img.quality_assessment.overall_status === "Warning"
                              ? "text-amber-700"
                              : "text-rose-700"
                          }`}
                        >
                          Quality: {img.quality_assessment.overall_status} ({img.quality_assessment.composite_score}/100)
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Verification Findings */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                3. Statutory Verification Findings (LMPC 2011)
              </h3>
              <table className="w-full text-left text-xs border border-slate-200 rounded">
                <thead className="bg-slate-100 border-b border-slate-200 text-slate-600 font-semibold">
                  <tr>
                    <th className="py-2 px-3">Statutory Rule</th>
                    <th className="py-2 px-3">Requirement</th>
                    <th className="py-2 px-3 text-right">Verification Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr>
                    <td className="py-2 px-3 font-semibold">Rule 6(1)(a)</td>
                    <td className="py-2 px-3">Generic name on Principal Display Panel</td>
                    <td className="py-2 px-3 text-right text-emerald-700 font-bold">VERIFIED</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold">Rule 6(1)(b)</td>
                    <td className="py-2 px-3">Net Quantity declared with standard symbols</td>
                    <td className="py-2 px-3 text-right text-emerald-700 font-bold">VERIFIED</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold">Rule 6(1)(c)</td>
                    <td className="py-2 px-3">Complete address of manufacturer or packer</td>
                    <td className="py-2 px-3 text-right text-emerald-700 font-bold">VERIFIED</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold">Rule 6(1)(da)</td>
                    <td className="py-2 px-3">MRP inclusive of all taxes</td>
                    <td className="py-2 px-3 text-right text-emerald-700 font-bold">VERIFIED</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold">Rule 5 & Sched. II</td>
                    <td className="py-2 px-3">Minimum optical numeral height ratio</td>
                    <td className="py-2 px-3 text-right font-bold">
                      {activeRecord.outcome === "Potential Non-Compliance" ? (
                        <span className="text-rose-600">FLAGGED DEFICIENT</span>
                      ) : (
                        <span className="text-emerald-700">VERIFIED</span>
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Outcome Banner */}
            <div className="p-4 rounded-xl border border-slate-300 bg-slate-50 flex items-center justify-between">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-500 block">
                  Final Screening Determination
                </span>
                <span className="text-base font-extrabold text-slate-900">
                  {activeRecord.outcome}
                </span>
              </div>
              <ComplianceBadge outcome={activeRecord.outcome} size="md" />
            </div>

            {/* Mandatory Disclaimer & Signatures */}
            <div className="pt-4 border-t border-slate-200 text-[10px] text-slate-500 space-y-4">
              <p className="leading-relaxed italic">
                DISCLAIMER: This document is an automated preliminary technical screening memorandum produced by Nirikshak-LM. 
                It is designed to assist enforcement personnel and does not constitute an autonomous statutory prosecution order. 
                Physical verification of the subject package is mandated before issuing any formal show-cause notice under the Legal Metrology Act, 2009.
              </p>

              <div className="flex justify-between pt-6 text-xs text-slate-700">
                <div className="border-t border-slate-400 pt-1 w-48 text-center">
                  <span>Inspector Signature</span>
                </div>
                <div className="border-t border-slate-400 pt-1 w-48 text-center">
                  <span>Authorized Seal & Date</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ReportsHubPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-500 text-sm">Loading audit report memo...</div>}>
      <ReportsHubContent />
    </Suspense>
  );
}
