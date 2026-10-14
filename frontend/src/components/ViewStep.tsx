"use client";

import React from "react";
import CameraCapture from "./CameraCapture";
import MarkerResult from "./MarkerResult";
import type { MarkerDetectionResult } from "@/lib/api";

interface ViewStepProps {
  viewType: "front" | "rear" | "side";
  label: string;
  instructions: string;
  capturedBlob: Blob | null;
  capturedPreview: string | null;
  markerResult: MarkerDetectionResult | null;
  markerLoading: boolean;
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
  onCapture,
  onRetake,
  onNext,
  canProceed,
}: ViewStepProps) {
  return (
    <div className="max-w-2xl w-full mx-auto p-6 bg-white rounded-xl shadow-sm border border-gray-100">
      <h2 className="text-2xl font-bold text-gray-900 mb-2">{label}</h2>
      <p className="text-gray-600 mb-6">{instructions}</p>

      <CameraCapture
        onCapture={onCapture}
        currentPreview={capturedPreview}
        onRetake={onRetake}
      />

      {capturedPreview && (
        <MarkerResult result={markerResult} loading={markerLoading} />
      )}

      <div className="mt-8 flex justify-end">
        <button
          onClick={onNext}
          disabled={!canProceed}
          className={`px-6 py-2 rounded-lg font-medium transition-colors ${
            canProceed
              ? "bg-blue-600 text-white hover:bg-blue-700"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          Next Step
        </button>
      </div>
    </div>
  );
}
