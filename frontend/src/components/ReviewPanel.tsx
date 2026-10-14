"use client";

import React from "react";
import type { MarkerDetectionResult } from "@/lib/api";

interface ViewReview {
  viewType: string;
  label: string;
  previewUrl: string | null;
  markerResult: MarkerDetectionResult | null;
}

interface ReviewPanelProps {
  views: ViewReview[];
  onRetake: (viewType: string) => void;
  onSubmit: () => void;
}

export default function ReviewPanel({ views, onRetake, onSubmit }: ReviewPanelProps) {
  const allCaptured = views.every(v => v.previewUrl !== null);

  return (
    <div className="max-w-4xl w-full mx-auto p-6 bg-white rounded-xl shadow-sm border border-gray-100">
      <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">Review Inspection</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {views.map((view) => (
          <div key={view.viewType} className="border border-gray-200 rounded-lg p-4 flex flex-col">
            <h3 className="font-semibold text-lg text-gray-800 mb-3 text-center">{view.label}</h3>

            <div className="aspect-[4/3] bg-gray-100 rounded-md overflow-hidden flex items-center justify-center mb-4 relative border border-gray-200">
              {view.previewUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={view.previewUrl} alt={view.label} className="w-full h-full object-cover" />
              ) : (
                <span className="text-gray-400 text-sm">Not captured</span>
              )}
            </div>

            <div className="mb-4 flex-grow text-center flex justify-center">
              {view.markerResult ? (
                view.markerResult.detected ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    Marker OK
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                    <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    No Marker
                  </span>
                )
              ) : (
                <span className="text-gray-400 text-xs">Pending</span>
              )}
            </div>

            <button
              onClick={() => onRetake(view.viewType)}
              className="w-full py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors text-sm font-medium"
            >
              Retake
            </button>
          </div>
        ))}
      </div>

      <div className="flex justify-center border-t border-gray-100 pt-6">
        <button
          onClick={onSubmit}
          disabled={!allCaptured}
          className={`px-8 py-3 rounded-lg font-bold text-lg transition-colors ${
            allCaptured
              ? "bg-blue-600 text-white hover:bg-blue-700 shadow-md"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          Complete Inspection
        </button>
      </div>
    </div>
  );
}
