"use client";

import React from "react";
import type { MarkerDetectionResult } from "@/lib/api";
import type { QualityAssessment } from "@/types";

interface ViewReview {
  viewType: string;
  label: string;
  previewUrl: string | null;
  processedUrl?: string | null;
  markerResult: MarkerDetectionResult | null;
  qualityAssessment?: QualityAssessment | null;
}

interface ReviewPanelProps {
  views: ViewReview[];
  onRetake: (viewType: string) => void;
  onSubmit: () => void;
}

export default function ReviewPanel({ views, onRetake, onSubmit }: ReviewPanelProps) {
  const allCaptured = views.every((v) => v.previewUrl !== null);
  const viewsNeedingRetake = views.filter(
    (v) => v.qualityAssessment?.overall_status === "Retake Recommended"
  );

  return (
    <div className="max-w-4xl w-full mx-auto p-6 bg-white rounded-xl shadow-sm border border-gray-100 space-y-6">
      <div className="text-center space-y-1">
        <h2 className="text-2xl font-bold text-gray-900">Review Multi-View Evidence</h2>
        <p className="text-xs text-slate-500">
          Verify optical capture clarity, reference-marker scale calibration, and preprocessed enhancements.
        </p>
      </div>

      {/* Advisory Banner if quality issues detected */}
      {viewsNeedingRetake.length > 0 && (
        <div className="p-3 bg-amber-50 border border-amber-300 rounded-lg text-xs text-amber-900 flex items-start space-x-2">
          <svg className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <div>
            <span className="font-bold">Quality Advisory:</span> Retake is recommended on{" "}
            <strong>{viewsNeedingRetake.map((v) => v.label).join(", ")}</strong> due to blur, low contrast, or specular glare. You may retake those panels now or proceed.
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {views.map((view) => {
          const qual = view.qualityAssessment;
          return (
            <div key={view.viewType} className="border border-gray-200 rounded-lg p-4 flex flex-col justify-between space-y-3">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-sm text-gray-800">{view.label}</h3>
                  {qual && (
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                        qual.overall_status === "Pass"
                          ? "bg-emerald-100 text-emerald-800"
                          : qual.overall_status === "Warning"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-rose-100 text-rose-800"
                      }`}
                    >
                      {qual.overall_status}
                    </span>
                  )}
                </div>

                <div className="aspect-[4/3] bg-gray-100 rounded-md overflow-hidden flex items-center justify-center relative border border-gray-200">
                  {view.previewUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={view.previewUrl} alt={view.label} className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-gray-400 text-xs">Not captured</span>
                  )}
                </div>

                {/* Status Badges: Marker + Quality Score */}
                <div className="space-y-1.5 text-center text-xs">
                  <div className="flex items-center justify-center space-x-2">
                    {view.markerResult ? (
                      view.markerResult.detected ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-100 text-emerald-800">
                          ✓ Marker (50mm)
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-800">
                          No Marker
                        </span>
                      )
                    ) : (
                      <span className="text-gray-400 text-[10px]">Marker: Pending</span>
                    )}

                    {qual && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700">
                        Score: {qual.composite_score}/100
                      </span>
                    )}
                  </div>

                  {view.processedUrl && (
                    <span className="block text-[10px] text-teal-700 font-mono">
                      ✓ Enhanced Copy Available
                    </span>
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={() => onRetake(view.viewType)}
                className="w-full py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded transition-colors text-xs font-semibold"
              >
                Retake {view.label}
              </button>
            </div>
          );
        })}
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-between border-t border-gray-100 pt-6 gap-3">
        <span className="text-xs text-slate-500">
          Once finalized, evidence plates and calibration metrics are locked into the audit memorandum.
        </span>
        <button
          onClick={onSubmit}
          disabled={!allCaptured}
          className={`px-8 py-3 rounded-lg font-bold text-sm transition-colors ${
            allCaptured
              ? "bg-blue-600 text-white hover:bg-blue-700 shadow-md"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          Complete Inspection & Generate Memo &rarr;
        </button>
      </div>
    </div>
  );
}
