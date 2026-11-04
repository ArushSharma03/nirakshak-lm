"use client";

import React, { useRef } from "react";
import { getReferenceMarkerUrl } from "@/lib/api";

interface ReferenceMarkerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// Exact 6x6 pixel grid (1-module black border + 4x4 code + 1-module black border) for ArUco 4x4_50 ID 0
const ARUCO_4X4_50_ID0_GRID = [
  [0, 0, 0, 0, 0, 0],
  [0, 1, 0, 1, 1, 0],
  [0, 0, 1, 0, 1, 0],
  [0, 0, 0, 1, 1, 0],
  [0, 0, 0, 1, 0, 0],
  [0, 0, 0, 0, 0, 0],
];

export default function ReferenceMarkerModal({ isOpen, onClose }: ReferenceMarkerModalProps) {
  const printableRef = useRef<HTMLDivElement>(null);

  if (!isOpen) return null;

  const handlePrint = () => {
    window.print();
  };

  const handleDownload = () => {
    const url = getReferenceMarkerUrl(0);
    const a = document.createElement("a");
    a.href = url;
    a.download = "nirikshak_aruco_4x4_id0_50mm.png";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full overflow-hidden border border-gray-200">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z" />
            </svg>
            <h3 className="font-bold text-base">ArUco Calibration Reference Marker</h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors p-1 rounded"
            title="Close"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {/* Printable Marker Preview Card */}
          <div
            ref={printableRef}
            className="flex flex-col items-center justify-center p-6 bg-white border-2 border-dashed border-gray-300 rounded-lg text-center"
          >
            {/* 50mm dimension label top */}
            <div className="w-48 text-xs font-mono text-gray-500 flex items-center justify-between mb-2">
              <span className="border-t border-gray-400 w-1/3"></span>
              <span className="font-semibold text-gray-700">50 mm (5.0 cm)</span>
              <span className="border-t border-gray-400 w-1/3"></span>
            </div>

            {/* Marker Canvas / SVG with surrounding Quiet Zone */}
            <div className="p-5 bg-white border border-gray-200 shadow-xs inline-block">
              <svg
                width="180"
                height="180"
                viewBox="0 0 6 6"
                className="shape-rendering-crispEdges block"
              >
                {ARUCO_4X4_50_ID0_GRID.map((row, rIdx) =>
                  row.map((cell, cIdx) => (
                    <rect
                      key={`${rIdx}-${cIdx}`}
                      x={cIdx}
                      y={rIdx}
                      width="1"
                      height="1"
                      fill={cell === 0 ? "#000000" : "#ffffff"}
                    />
                  ))
                )}
              </svg>
            </div>

            <div className="mt-3 space-y-0.5">
              <p className="text-xs font-bold text-gray-900 tracking-wide">
                ArUco 4x4_50 &bull; Marker ID: 0
              </p>
              <p className="text-[11px] text-gray-500">
                Official Nirikshak-LM Packaged Commodity Calibration Target
              </p>
            </div>
          </div>

          {/* Detailed Instructions Checklist */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs text-slate-700 space-y-2">
            <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider">
              Setup &amp; Detection Guidelines
            </h4>
            <ul className="space-y-1.5 list-disc list-inside">
              <li>
                <strong className="text-slate-800">Standard Specifications:</strong> Dictionary is{" "}
                <span className="font-mono bg-white px-1 py-0.5 rounded border border-gray-200">ArUco 4x4_50</span>, ID{" "}
                <span className="font-mono bg-white px-1 py-0.5 rounded border border-gray-200">0</span>, standard physical size: 50.0 mm.
              </li>
              <li>
                <strong className="text-slate-800">White Margin (Quiet Zone):</strong> The black marker must be surrounded by white space. If displaying on a phone screen, ensure the full white border is visible.
              </li>
              <li>
                <strong className="text-slate-800">Coplanar Placement:</strong> Place the marker flat right next to the package face (e.g. resting against the front/rear/side panel) at the same focal depth.
              </li>
              <li>
                <strong className="text-slate-800">Distance &amp; Focus:</strong> Keep 20–50 cm from the camera so the marker appears clear, sharp, and without heavy reflections.
              </li>
            </ul>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-3.5 bg-gray-50 border-t border-gray-200 flex flex-wrap items-center justify-between gap-2">
          <button
            type="button"
            onClick={handleDownload}
            className="px-3.5 py-1.5 bg-white border border-gray-300 hover:bg-gray-100 text-gray-700 rounded-lg text-xs font-medium transition-colors flex items-center space-x-1.5 shadow-xs"
          >
            <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>Download PNG</span>
          </button>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handlePrint}
              className="px-4 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-semibold transition-colors flex items-center space-x-1.5 shadow-xs"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
              </svg>
              <span>Print Target (100%)</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg text-xs font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
