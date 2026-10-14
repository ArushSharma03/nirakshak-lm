"use client";

import React from "react";
import type { MarkerDetectionResult } from "@/lib/api";

interface MarkerResultProps {
  result: MarkerDetectionResult | null;
  loading: boolean;
}

export default function MarkerResult({ result, loading }: MarkerResultProps) {
  if (loading) {
    return (
      <div className="mt-4 p-4 border rounded-lg bg-gray-50 flex items-center justify-center text-gray-600">
        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Detecting reference marker...
      </div>
    );
  }

  if (!result) return null;

  if (result.detected) {
    return (
      <div className="mt-4 p-4 border border-green-200 rounded-lg bg-green-50 text-green-800">
        <h4 className="font-semibold flex items-center mb-1">
          <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          Reference Marker Detected
        </h4>
        <div className="text-sm space-y-1 ml-7">
          <p>Confidence Score: {result.score ? (result.score * 100).toFixed(1) : "N/A"}%</p>
          <p>Dimensions: {result.pixel_width}x{result.pixel_height} px</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-4 p-4 border border-amber-200 rounded-lg bg-amber-50 text-amber-800">
      <h4 className="font-semibold flex items-center">
        <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
        Reference marker not detected — calibration unavailable.
      </h4>
      <p className="text-sm ml-7 mt-1">{result.message}</p>
    </div>
  );
}
