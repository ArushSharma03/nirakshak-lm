"use client";

import React, { useState } from "react";
import { QualityAssessment } from "@/types";

interface QualityResultProps {
  assessment: QualityAssessment | null;
  loading: boolean;
  rawPreviewUrl?: string | null;
  processedUrl?: string | null;
  onRetake?: () => void;
}

export default function QualityResult({
  assessment,
  loading,
  rawPreviewUrl,
  processedUrl,
  onRetake,
}: QualityResultProps) {
  const [showProcessed, setShowProcessed] = useState<boolean>(false);

  if (loading) {
    return (
      <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-center space-x-3 text-xs text-slate-600 animate-pulse">
        <svg
          className="animate-spin h-4 w-4 text-blue-600"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
        <span className="font-medium">
          Evaluating capture quality (sharpness, exposure, contrast, glare)...
        </span>
      </div>
    );
  }

  if (!assessment) return null;

  const isRetake = assessment.overall_status === "Retake Recommended";
  const isWarning = assessment.overall_status === "Warning";

  return (
    <div
      className={`rounded-xl border p-4 space-y-4 text-xs transition-all ${
        isRetake
          ? "bg-rose-50/60 border-rose-200 text-rose-950"
          : isWarning
          ? "bg-amber-50/60 border-amber-200 text-amber-950"
          : "bg-emerald-50/50 border-emerald-200 text-emerald-950"
      }`}
    >
      {/* Header with Overall Status & Score */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-current/15">
        <div className="flex items-center space-x-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              isRetake
                ? "bg-rose-600 animate-ping"
                : isWarning
                ? "bg-amber-500"
                : "bg-emerald-600"
            }`}
          />
          <span className="font-extrabold text-sm uppercase tracking-wide">
            Capture Quality: {assessment.overall_status}
          </span>
          <span className="font-mono text-[11px] opacity-75">
            (Score: {assessment.composite_score}/100)
          </span>
        </div>

        {isRetake && onRetake && (
          <button
            type="button"
            onClick={onRetake}
            className="px-3 py-1 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-md text-xs transition-colors shadow-xs"
          >
            Retake Photo Recommended &rarr;
          </button>
        )}
      </div>

      {/* 5 Quality Pillars Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {/* Sharpness */}
        <div className="bg-white/80 rounded-lg p-2.5 border border-slate-200/80 space-y-1">
          <div className="flex items-center justify-between text-[11px] font-semibold text-slate-700">
            <span>Sharpness</span>
            <span
              className={`font-bold ${
                assessment.metrics.sharpness.status === "Pass"
                  ? "text-emerald-700"
                  : assessment.metrics.sharpness.status === "Warning"
                  ? "text-amber-700"
                  : "text-rose-700"
              }`}
            >
              {assessment.metrics.sharpness.status === "Pass" ? "✓ Sharp" : assessment.metrics.sharpness.status}
            </span>
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            Var: {assessment.metrics.sharpness.value ?? "N/A"}
          </div>
        </div>

        {/* Exposure */}
        <div className="bg-white/80 rounded-lg p-2.5 border border-slate-200/80 space-y-1">
          <div className="flex items-center justify-between text-[11px] font-semibold text-slate-700">
            <span>Exposure</span>
            <span
              className={`font-bold ${
                assessment.metrics.exposure.status === "Pass"
                  ? "text-emerald-700"
                  : assessment.metrics.exposure.status === "Warning"
                  ? "text-amber-700"
                  : "text-rose-700"
              }`}
            >
              {assessment.metrics.exposure.status === "Pass" ? "✓ Balanced" : assessment.metrics.exposure.status}
            </span>
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            Mean: {assessment.metrics.exposure.value ?? "N/A"}
          </div>
        </div>

        {/* Contrast */}
        <div className="bg-white/80 rounded-lg p-2.5 border border-slate-200/80 space-y-1">
          <div className="flex items-center justify-between text-[11px] font-semibold text-slate-700">
            <span>Contrast</span>
            <span
              className={`font-bold ${
                assessment.metrics.contrast.status === "Pass"
                  ? "text-emerald-700"
                  : assessment.metrics.contrast.status === "Warning"
                  ? "text-amber-700"
                  : "text-rose-700"
              }`}
            >
              {assessment.metrics.contrast.status === "Pass" ? "✓ Good" : assessment.metrics.contrast.status}
            </span>
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            Std: {assessment.metrics.contrast.value ?? "N/A"}
          </div>
        </div>

        {/* Glare */}
        <div className="bg-white/80 rounded-lg p-2.5 border border-slate-200/80 space-y-1">
          <div className="flex items-center justify-between text-[11px] font-semibold text-slate-700">
            <span>Glare Check</span>
            <span
              className={`font-bold ${
                assessment.metrics.glare.status === "Pass"
                  ? "text-emerald-700"
                  : assessment.metrics.glare.status === "Warning"
                  ? "text-amber-700"
                  : "text-rose-700"
              }`}
            >
              {assessment.metrics.glare.status === "Pass" ? "✓ Minimal" : assessment.metrics.glare.status}
            </span>
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            Hotspot: {assessment.metrics.glare.value ? `${assessment.metrics.glare.value}%` : "0%"}
          </div>
        </div>

        {/* Resolution */}
        <div className="bg-white/80 rounded-lg p-2.5 border border-slate-200/80 space-y-1 col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between text-[11px] font-semibold text-slate-700">
            <span>Dimensions</span>
            <span
              className={`font-bold ${
                assessment.metrics.resolution.status === "Pass"
                  ? "text-emerald-700"
                  : assessment.metrics.resolution.status === "Warning"
                  ? "text-amber-700"
                  : "text-rose-700"
              }`}
            >
              {assessment.metrics.resolution.status === "Pass" ? "✓ HD" : assessment.metrics.resolution.status}
            </span>
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            {assessment.metrics.resolution.width && assessment.metrics.resolution.height
              ? `${assessment.metrics.resolution.width}x${assessment.metrics.resolution.height}`
              : "Standard"}
          </div>
        </div>
      </div>

      {/* Actionable Inspector Guidance */}
      {assessment.recommendations && assessment.recommendations.length > 0 && (
        <div className="p-3 bg-white/70 rounded-lg border border-slate-200 text-slate-800 space-y-1">
          <span className="font-bold text-[11px] uppercase tracking-wider block text-slate-600">
            Actionable Guidance for Inspector:
          </span>
          <ul className="list-disc pl-4 space-y-0.5 text-[11px] text-slate-700">
            {assessment.recommendations.map((rec, idx) => (
              <li key={idx}>{rec}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Preprocessing / Enhanced View Toggle */}
      {processedUrl && (
        <div className="pt-2 border-t border-current/15 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="text-[11px] text-slate-600">
            <span>Edge-preserving CLAHE & bilateral filter enhanced copy generated.</span>
          </div>
          <button
            type="button"
            onClick={() => setShowProcessed(!showProcessed)}
            className="px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 rounded font-medium text-xs transition-colors self-start sm:self-auto"
          >
            {showProcessed ? "Show Original Capture" : "Inspect Preprocessed Copy (CLAHE)"}
          </button>
        </div>
      )}

      {/* Preprocessed Image Preview Modal / View if toggled */}
      {showProcessed && processedUrl && (
        <div className="mt-2 p-3 bg-slate-900 text-white rounded-lg space-y-2">
          <div className="flex justify-between items-center text-xs font-semibold">
            <span className="text-teal-300">Enhanced Preprocessed View (Bilateral Denoise + CLAHE)</span>
            <span className="text-[10px] text-slate-400 font-mono">Algorithm: v1.0.0-nir-prep</span>
          </div>
          <div className={`grid ${rawPreviewUrl ? "grid-cols-2" : "grid-cols-1"} gap-2 max-w-md mx-auto`}>
            {rawPreviewUrl && (
              <div className="space-y-1">
                <span className="text-[10px] text-slate-400 block text-center font-medium">Original Raw Evidence</span>
                <div className="aspect-[4/3] bg-black rounded overflow-hidden relative border border-slate-700">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={rawPreviewUrl} alt="Original raw evidence" className="w-full h-full object-contain" />
                </div>
              </div>
            )}
            <div className="space-y-1">
              <span className="text-[10px] text-teal-300 block text-center font-medium">Enhanced Copy</span>
              <div className="aspect-[4/3] bg-black rounded overflow-hidden relative border border-slate-700">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={processedUrl} alt="Preprocessed view" className="w-full h-full object-contain" />
              </div>
            </div>
          </div>
          <p className="text-[10px] text-slate-400 text-center italic">
            Original raw evidence is preserved unchanged in the evidentiary vault.
          </p>
        </div>
      )}

      {/* Quality Assessment Non-Legal Disclaimer */}
      <div className="text-[10px] text-slate-500 italic pt-1 border-t border-current/10">
        {assessment.disclaimer}
      </div>
    </div>
  );
}
