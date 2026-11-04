"use client";

import React, { useState } from "react";
import type { MarkerDetectionResult } from "@/lib/api";
import ReferenceMarkerModal from "@/components/common/ReferenceMarkerModal";

interface MarkerResultProps {
  result: MarkerDetectionResult | null;
  loading: boolean;
}

export default function MarkerResult({ result, loading }: MarkerResultProps) {
  const [showModal, setShowModal] = useState(false);

  if (loading) {
    return (
      <div className="mt-4 p-4 border rounded-lg bg-gray-50 flex items-center justify-center text-gray-600">
        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>Detecting reference marker in captured frame...</span>
      </div>
    );
  }

  if (!result) return null;

  if (result.detected) {
    return (
      <>
        <div className="mt-4 p-4 border border-emerald-200 rounded-lg bg-emerald-50 text-emerald-900">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-semibold flex items-center text-emerald-800">
              <svg className="w-5 h-5 mr-2 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Reference Marker Detected
            </h4>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
              {result.dictionary || "ArUco 4x4_50"} (ID: {result.marker_id ?? 0})
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs text-emerald-800 ml-7 mb-2 bg-emerald-100/60 p-2.5 rounded border border-emerald-200/60">
            <div>
              <span className="text-emerald-700 block font-medium">Planar Quality:</span>
              <span className="font-bold">{result.score ? (result.score * 100).toFixed(1) : "N/A"}%</span>
            </div>
            <div>
              <span className="text-emerald-700 block font-medium">Pixel Size:</span>
              <span className="font-bold">{result.pixel_width} &times; {result.pixel_height} px</span>
            </div>
            <div>
              <span className="text-emerald-700 block font-medium">Preliminary Scale:</span>
              <span className="font-bold">{result.estimated_ppm ? `${result.estimated_ppm} px/mm` : "Available"}</span>
            </div>
          </div>

          <p className="text-[11px] text-emerald-700 ml-7">
            Preliminary scale derived assuming standard 50.0 mm coplanar target. Physical metric accuracy is verified in downstream inspection analysis.
          </p>
        </div>

        <ReferenceMarkerModal isOpen={showModal} onClose={() => setShowModal(false)} />
      </>
    );
  }

  return (
    <>
      <div className="mt-4 p-4 border border-amber-300 rounded-lg bg-amber-50 text-amber-900 shadow-xs">
        <div className="flex items-start justify-between">
          <div className="flex items-center mb-1">
            <svg className="w-5 h-5 mr-2 text-amber-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <h4 className="font-semibold text-amber-900 text-sm">
              Reference marker not detected &mdash; calibration unavailable
            </h4>
          </div>

          <button
            type="button"
            onClick={() => setShowModal(true)}
            className="text-xs px-2.5 py-1 bg-amber-200 hover:bg-amber-300 text-amber-900 rounded font-semibold transition-colors flex items-center space-x-1"
          >
            <span>View / Print Marker</span>
          </button>
        </div>

        <p className="text-xs text-amber-800 ml-7 mb-3">{result.message}</p>

        {/* Troubleshooting Instructions */}
        <div className="ml-7 p-3 bg-white/80 rounded-md border border-amber-200 text-xs text-amber-900 space-y-1.5">
          <p className="font-bold text-amber-950 uppercase tracking-wide text-[11px]">
            Troubleshooting Marker Visibility &amp; Scale Calibration:
          </p>
          <ul className="list-disc list-inside space-y-1 text-amber-800">
            <li>
              <strong>Marker Dictionary &amp; ID:</strong> Must be <strong>ArUco 4x4_50, ID 0</strong> (standard 50 mm &times; 50 mm).
            </li>
            <li>
              <strong>White Quiet Zone:</strong> The outer white border surrounding the black marker square must be completely visible.
            </li>
            <li>
              <strong>Coplanar Alignment:</strong> Place marker flat on the same plane as the package panel (not behind or in front).
            </li>
            <li>
              <strong>Distance &amp; Lighting:</strong> Keep 20&ndash;50 cm from camera. Avoid reflections or dark shadows over the marker.
            </li>
          </ul>
        </div>
      </div>

      <ReferenceMarkerModal isOpen={showModal} onClose={() => setShowModal(false)} />
    </>
  );
}
