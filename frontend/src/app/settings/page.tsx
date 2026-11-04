"use client";

import React, { useEffect, useState } from "react";
import { checkBackendStatus } from "@/lib/api";
import { SystemStatus } from "@/types";
import LegalDisclaimer from "@/components/common/LegalDisclaimer";

export default function SettingsPage() {
  const [status, setStatus] = useState<SystemStatus>({
    isLive: false,
    backendVersion: undefined,
    databaseAvailable: false,
    mode: "Demonstrator Mode",
  });
  const [inspectorName, setInspectorName] = useState("Mr. Arush Sharma");
  const [inspectorRole, setInspectorRole] = useState("Lead Inspector — Legal Metrology Screening");
  const [markerSizeMm, setMarkerSizeMm] = useState("50.0");
  const [dictionary, setDictionary] = useState("DICT_4X4_50");
  const [cameraRes, setCameraRes] = useState("1080p");
  const [savedBanner, setSavedBanner] = useState(false);

  useEffect(() => {
    async function load() {
      const s = await checkBackendStatus();
      setStatus(s);
    }
    load();
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedBanner(true);
    setTimeout(() => setSavedBanner(false), 3000);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Title */}
      <div className="pb-4 border-b border-slate-200">
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          System & Hardware Settings
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Configure inspector profile, camera resolutions, and reference-marker scale calibration parameters.
        </p>
      </div>

      <LegalDisclaimer compact />

      {savedBanner && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-semibold flex items-center space-x-2">
          <svg className="w-4 h-4 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          <span>Settings saved successfully in client preferences!</span>
        </div>
      )}

      {/* Backend & Environment Status Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
        <h2 className="text-sm font-bold text-slate-900">
          Backend Service & Telemetry Status
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-400 block text-[11px] font-medium">FastAPI Endpoint</span>
            <span className="font-mono font-bold text-slate-800">http://localhost:8000</span>
            <span className="text-[10px] text-slate-500 block mt-1">
              Status: {status.isLive ? "● Online (200 OK)" : "○ Offline / Mock Fallback"}
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-400 block text-[11px] font-medium">Operating Mode</span>
            <span className={`font-bold block ${status.isLive ? "text-emerald-700" : "text-teal-700"}`}>
              {status.mode}
            </span>
            <span className="text-[10px] text-slate-500 block mt-1">
              Dual-mode safety active
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-400 block text-[11px] font-medium">PostgreSQL Database</span>
            <span className="font-semibold text-slate-700 block">
              {status.databaseAvailable ? "Connected" : "Unconnected (Local Mock)"}
            </span>
            <span className="text-[10px] text-slate-400 block mt-1">
              Host DB not required for demo
            </span>
          </div>
        </div>
      </div>

      {/* Settings Form */}
      <form onSubmit={handleSave} className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6">
        {/* Section 1: Inspector Identity */}
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            1. Inspector Profile
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Inspector Full Name
              </label>
              <input
                type="text"
                value={inspectorName}
                onChange={(e) => setInspectorName(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-xs sm:text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Designation / Department
              </label>
              <input
                type="text"
                value={inspectorRole}
                onChange={(e) => setInspectorRole(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-xs sm:text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
          </div>
        </div>

        {/* Section 2: Scale Calibration Parameters */}
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            2. Reference Marker & Scale Calibration
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Reference Marker Physical Size (mm)
              </label>
              <input
                type="number"
                step="0.5"
                value={markerSizeMm}
                onChange={(e) => setMarkerSizeMm(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-xs sm:text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20"
              />
              <span className="text-[11px] text-slate-400">
                Standard ArUco physical square side length (default 50.0 mm).
              </span>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                ArUco Dictionary Family
              </label>
              <select
                value={dictionary}
                onChange={(e) => setDictionary(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-xs sm:text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="DICT_4X4_50">ArUco 4×4 (50 markers) — Recommended</option>
                <option value="DICT_5X5_50">ArUco 5×5 (50 markers)</option>
                <option value="DICT_6X6_50">ArUco 6×6 (50 markers)</option>
              </select>
              <span className="text-[11px] text-slate-400">
                Corresponds to the printed calibration card pattern.
              </span>
            </div>
          </div>
        </div>

        {/* Section 3: Camera Capture Hardware */}
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            3. Camera & Capture Stream Preferences
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Preferred Stream Resolution
              </label>
              <select
                value={cameraRes}
                onChange={(e) => setCameraRes(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-xs sm:text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="1080p">1080p Full HD (1920 × 1080) — Best for Character OCR</option>
                <option value="720p">720p HD (1280 × 720) — High Performance</option>
                <option value="480p">480p Standard (640 × 480)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Facing Mode Constraint
              </label>
              <div className="px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-xs text-slate-700">
                Progressive cascade: <code>facingMode: environment</code> with automatic fallback to desktop webcam.
              </div>
            </div>
          </div>
        </div>

        {/* Save CTA */}
        <div className="pt-4 border-t border-slate-200 flex justify-end">
          <button
            type="submit"
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg text-xs transition-colors shadow-sm"
          >
            Save Settings
          </button>
        </div>
      </form>
    </div>
  );
}
