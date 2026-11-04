"use client";

import React, { useState } from "react";
import CameraCapture from "./CameraCapture";
import MarkerResult from "./MarkerResult";
import QualityResult from "./QualityResult";
import ReferenceMarkerModal from "./common/ReferenceMarkerModal";
import type { MarkerDetectionResult } from "@/lib/api";
import type { QualityAssessment } from "@/types";

interface ViewStepProps {
  viewType: "front" | "rear" | "side";
  label: string;
  instructions: string;
  capturedBlob: Blob | null;
  capturedPreview: string | null;
  markerResult: MarkerDetectionResult | null;
  markerLoading: boolean;
  qualityAssessment?: QualityAssessment | null;
  qualityLoading?: boolean;
  processedUrl?: string | null;
  onCapture: (blob: Blob, previewUrl: string) => void;
  onRetake: () => void;
  onNext: () => void;
  canProceed: boolean;
}

export default function ViewStep({
  label,
  instructions,
  capturedPreview,
  markerResult,
  markerLoading,
  qualityAssessment = null,
  qualityLoading = false,
  processedUrl = null,
  onCapture,
  onRetake,
  onNext,
  canProceed,
}: ViewStepProps) {
  const [showMarkerGuide, setShowMarkerGuide] = useState(false);

  return (
    <div className="max-w-2xl w-full mx-auto p-6 bg-white rounded-xl shadow-sm border border-gray-100 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{label}</h2>
          <p className="text-gray-600 text-sm mt-1">{instructions}</p>
        </div>
        <button
          type="button"
          onClick={() => setShowMarkerGuide(true)}
          className="ml-4 shrink-0 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg text-xs font-semibold border border-slate-300 transition-colors flex items-center space-x-1.5"
        >
          <svg className="w-3.5 h-3.5 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"
            />
          </svg>
          <span>50mm Marker Guide</span>
        </button>
      </div>

      <div className="my-2">
        <CameraCapture
          onCapture={onCapture}
          currentPreview={capturedPreview}
          onRetake={onRetake}
        />
      </div>

      {capturedPreview && (
        <div className="space-y-3 pt-2">
          {/* 1. Physical Scale & ArUco Calibration */}
          <MarkerResult result={markerResult} loading={markerLoading} />

          {/* 2. Image Quality Assessment & Preprocessing */}
          <QualityResult
            assessment={qualityAssessment}
            loading={qualityLoading}
            rawPreviewUrl={capturedPreview}
            processedUrl={processedUrl}
            onRetake={onRetake}
          />
        </div>
      )}

      <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
        <span className="text-xs text-slate-500">
          {qualityAssessment?.overall_status === "Retake Recommended"
            ? "Notice: Quality assessment recommends retaking this photo before completing inspection."
            : "Review optical metrics before continuing to the next view."}
        </span>
        <button
          onClick={onNext}
          disabled={!canProceed}
          className={`px-6 py-2 rounded-lg font-medium transition-colors ${
            canProceed
              ? "bg-blue-600 text-white hover:bg-blue-700 shadow-sm"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          Next Step &rarr;
        </button>
      </div>

      <ReferenceMarkerModal isOpen={showMarkerGuide} onClose={() => setShowMarkerGuide(false)} />
    </div>
  );
}
