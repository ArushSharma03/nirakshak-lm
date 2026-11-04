"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ViewStep from "@/components/ViewStep";
import ReviewPanel from "@/components/ReviewPanel";
import ReferenceMarkerModal from "@/components/common/ReferenceMarkerModal";
import {
  createInspection,
  uploadInspectionView,
  getInspectionById,
  type MarkerDetectionResult,
} from "@/lib/api";
import { InspectionRecord, QualityAssessment } from "@/types";

type ViewType = "front" | "rear" | "side";

interface ViewState {
  blob: Blob | null;
  previewUrl: string | null;
  processedUrl: string | null;
  markerResult: MarkerDetectionResult | null;
  markerLoading: boolean;
  qualityAssessment: QualityAssessment | null;
  qualityLoading: boolean;
}

function InspectCaptureFlow() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const inspectionId = searchParams.get("id");

  const [step, setStep] = useState<number>(0);
  const [showMarkerGuide, setShowMarkerGuide] = useState<boolean>(false);
  const [inspection, setInspection] = useState<InspectionRecord | null>(null);
  const [, setLoadingRecord] = useState<boolean>(!!inspectionId);

  const [views, setViews] = useState<Record<ViewType, ViewState>>({
    front: { blob: null, previewUrl: null, processedUrl: null, markerResult: null, markerLoading: false, qualityAssessment: null, qualityLoading: false },
    rear: { blob: null, previewUrl: null, processedUrl: null, markerResult: null, markerLoading: false, qualityAssessment: null, qualityLoading: false },
    side: { blob: null, previewUrl: null, processedUrl: null, markerResult: null, markerLoading: false, qualityAssessment: null, qualityLoading: false },
  });

  // Load inspection record if ID is provided in query params
  useEffect(() => {
    if (!inspectionId) return;

    let isMounted = true;
    async function load() {
      setLoadingRecord(true);
      const rec = await getInspectionById(inspectionId!);
      if (isMounted && rec) {
        setInspection(rec);

        // Populate previously captured views if available
        if (rec.images) {
          setViews((prev) => {
            const next = { ...prev };
            for (const vt of ["front", "rear", "side"] as const) {
              if (rec.images?.[vt]) {
                const img = rec.images[vt];
                next[vt] = {
                  blob: null,
                  previewUrl: img.previewUrl || null,
                  processedUrl: img.processedUrl || null,
                  markerResult: {
                    detected: !!img.marker_detected,
                    bounding_box: null,
                    pixel_width: img.pixel_width || null,
                    pixel_height: img.pixel_height || null,
                    score: img.score || null,
                    estimated_ppm: img.estimated_ppm || null,
                    message: img.marker_detected
                      ? "Calibrated reference marker detected."
                      : "Reference marker not detected.",
                  },
                  markerLoading: false,
                  qualityAssessment: img.quality_assessment || null,
                  qualityLoading: false,
                };
              }
            }
            return next;
          });
        }
      }
      if (isMounted) setLoadingRecord(false);
    }

    load();
    return () => {
      isMounted = false;
    };
  }, [inspectionId]);

  const updateView = (type: ViewType, updates: Partial<ViewState>) => {
    setViews((prev) => ({
      ...prev,
      [type]: { ...prev[type], ...updates },
    }));
  };

  const handleCapture = async (type: ViewType, blob: Blob, previewUrl: string) => {
    updateView(type, {
      blob,
      previewUrl,
      markerLoading: true,
      qualityLoading: true,
      markerResult: null,
      qualityAssessment: null,
    });

    let currentId = inspection?.id || inspectionId;
    if (!currentId) {
      try {
        const created = await createInspection({
          productName: "Generic Packaged Commodity",
          productCategory: "food_grocery",
          brand: "Standard Test Commodity",
        });
        currentId = created.id;
        setInspection(created);
      } catch {
        currentId = `INS-LOCAL-${Date.now()}`;
      }
    }

    try {
      const uploadRes = await uploadInspectionView(currentId, type, blob);
      updateView(type, {
        markerResult: uploadRes.markerResult,
        qualityAssessment: uploadRes.qualityAssessment,
        processedUrl: uploadRes.processedUrl,
        markerLoading: false,
        qualityLoading: false,
      });
      if (uploadRes.record) {
        setInspection(uploadRes.record);
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      updateView(type, {
        markerLoading: false,
        qualityLoading: false,
        markerResult: {
          detected: false,
          bounding_box: null,
          pixel_width: null,
          pixel_height: null,
          score: null,
          message: `Detection failed: ${errorMessage}`,
        },
      });
    }
  };

  const handleRetake = (type: ViewType) => {
    updateView(type, {
      blob: null,
      previewUrl: null,
      processedUrl: null,
      markerResult: null,
      markerLoading: false,
      qualityAssessment: null,
      qualityLoading: false,
    });
  };

  const handleSubmit = async () => {
    const targetId = inspection?.id || inspectionId;
    if (targetId) {
      router.push(`/reports?id=${encodeURIComponent(targetId)}`);
    } else {
      router.push("/inspections");
    }
  };

  const steps = ["Start", "Front", "Rear", "Side", "Review"];

  return (
    <div className="min-h-full bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex flex-col items-center">
        <div className="w-full max-w-2xl flex flex-col sm:flex-row items-center justify-between gap-2 mb-4">
          <h1 className="text-xl font-bold text-gray-800">Inspection Capture</h1>

          {/* Active Inspection Profile Pill */}
          {inspection && (
            <div className="bg-slate-100 border border-slate-200 rounded-lg px-3 py-1 text-xs flex items-center space-x-2 text-slate-700">
              <span className="font-mono font-bold text-slate-900">{inspection.id}</span>
              <span>&bull;</span>
              <span className="font-semibold truncate max-w-[140px] sm:max-w-[200px]">
                {inspection.productName}
              </span>
              <span className="hidden sm:inline">&bull;</span>
              <span className="hidden sm:inline text-slate-500">Net: {inspection.declaredNetQty}</span>
            </div>
          )}
        </div>

        {/* Progress indicator */}
        <div className="flex items-center space-x-2 text-sm max-w-lg w-full justify-between">
          {steps.map((s, i) => (
            <div key={s} className="flex items-center">
              <span
                className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
                  step === i
                    ? "bg-blue-600 text-white"
                    : step > i
                    ? "bg-green-100 text-green-700"
                    : "bg-gray-100 text-gray-500"
                }`}
              >
                {step > i ? "✓" : i}
              </span>
              <span
                className={`ml-2 hidden sm:block ${
                  step === i ? "text-gray-900 font-medium" : "text-gray-500"
                }`}
              >
                {s}
              </span>
              {i < steps.length - 1 && (
                <div className="w-4 sm:w-8 h-[2px] mx-2 bg-gray-200"></div>
              )}
            </div>
          ))}
        </div>
      </header>

      <main className="flex-grow p-6 flex items-center justify-center">
        {step === 0 && (
          <div className="max-w-xl mx-auto p-8 bg-white rounded-xl shadow-sm border border-gray-100 text-center">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-3">
              {inspection ? `Capture: ${inspection.productName}` : "New Inspection Capture"}
            </h2>
            <p className="text-gray-600 mb-6 text-sm leading-relaxed">
              You will be guided to capture three views of the packaged commodity: front, rear, and side panels.
              Each capture automatically evaluates sharpness, exposure balance, contrast, and specular glare,
              and generates a contrast-enhanced preprocessed copy.
            </p>

            {inspection && (
              <div className="p-4 mb-6 bg-blue-50/70 border border-blue-200 rounded-lg text-left text-xs space-y-1.5">
                <div className="flex justify-between items-center text-blue-900 font-semibold">
                  <span>Registered Inspection Record:</span>
                  <span className="font-mono bg-white px-2 py-0.5 rounded border border-blue-200 text-blue-800">
                    {inspection.id}
                  </span>
                </div>
                <div className="text-slate-600">
                  Brand: <strong>{inspection.brand}</strong> &bull; Declared Net Qty: <strong>{inspection.declaredNetQty}</strong> &bull; MRP: <strong>₹{inspection.declaredMRP}</strong>
                </div>
              </div>
            )}

            <div className="p-4 mb-6 bg-slate-50 border border-slate-200 rounded-lg text-left text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 uppercase tracking-wide">Standard Reference Marker:</span>
                <span className="px-2 py-0.5 rounded font-mono font-bold bg-teal-100 text-teal-800 border border-teal-300">
                  ArUco 4x4_50 (ID 0)
                </span>
              </div>
              <p className="text-slate-600 leading-normal">
                Standard calibrated side-length is 50.0 mm (5.0 cm). The outer white margin (quiet zone) must remain completely visible for contour detection.
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="px-8 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
              >
                Start Capture
              </button>
              <button
                type="button"
                onClick={() => setShowMarkerGuide(true)}
                className="px-5 py-3 bg-slate-100 text-slate-800 font-medium rounded-lg hover:bg-slate-200 transition-colors border border-slate-300 text-sm flex items-center space-x-1.5"
              >
                <svg className="w-4 h-4 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"
                  />
                </svg>
                <span>View / Print 50mm Marker</span>
              </button>
            </div>

            <ReferenceMarkerModal isOpen={showMarkerGuide} onClose={() => setShowMarkerGuide(false)} />
          </div>
        )}

        {step === 1 && (
          <ViewStep
            viewType="front"
            label="Front View"
            instructions="Position the front panel of the package facing the camera. Place the reference marker visibly in the frame."
            capturedBlob={views.front.blob}
            capturedPreview={views.front.previewUrl}
            markerResult={views.front.markerResult}
            markerLoading={views.front.markerLoading}
            qualityAssessment={views.front.qualityAssessment}
            qualityLoading={views.front.qualityLoading}
            processedUrl={views.front.processedUrl}
            onCapture={(blob, url) => handleCapture("front", blob, url)}
            onRetake={() => handleRetake("front")}
            onNext={() => setStep(2)}
            canProceed={!!views.front.previewUrl && !views.front.markerLoading && !views.front.qualityLoading}
          />
        )}

        {step === 2 && (
          <ViewStep
            viewType="rear"
            label="Rear View"
            instructions="Position the rear panel of the package facing the camera. Ensure all text and barcode are clearly visible. Place the reference marker in frame."
            capturedBlob={views.rear.blob}
            capturedPreview={views.rear.previewUrl}
            markerResult={views.rear.markerResult}
            markerLoading={views.rear.markerLoading}
            qualityAssessment={views.rear.qualityAssessment}
            qualityLoading={views.rear.qualityLoading}
            processedUrl={views.rear.processedUrl}
            onCapture={(blob, url) => handleCapture("rear", blob, url)}
            onRetake={() => handleRetake("rear")}
            onNext={() => setStep(3)}
            canProceed={!!views.rear.previewUrl && !views.rear.markerLoading && !views.rear.qualityLoading}
          />
        )}

        {step === 3 && (
          <ViewStep
            viewType="side"
            label="Side View"
            instructions="Position the side panel of the package facing the camera. Place the reference marker in the frame."
            capturedBlob={views.side.blob}
            capturedPreview={views.side.previewUrl}
            markerResult={views.side.markerResult}
            markerLoading={views.side.markerLoading}
            qualityAssessment={views.side.qualityAssessment}
            qualityLoading={views.side.qualityLoading}
            processedUrl={views.side.processedUrl}
            onCapture={(blob, url) => handleCapture("side", blob, url)}
            onRetake={() => handleRetake("side")}
            onNext={() => setStep(4)}
            canProceed={!!views.side.previewUrl && !views.side.markerLoading && !views.side.qualityLoading}
          />
        )}

        {step === 4 && (
          <ReviewPanel
            views={[
              { viewType: "front", label: "Front View", previewUrl: views.front.previewUrl, processedUrl: views.front.processedUrl, markerResult: views.front.markerResult, qualityAssessment: views.front.qualityAssessment },
              { viewType: "rear", label: "Rear View", previewUrl: views.rear.previewUrl, processedUrl: views.rear.processedUrl, markerResult: views.rear.markerResult, qualityAssessment: views.rear.qualityAssessment },
              { viewType: "side", label: "Side View", previewUrl: views.side.previewUrl, processedUrl: views.side.processedUrl, markerResult: views.side.markerResult, qualityAssessment: views.side.qualityAssessment },
            ]}
            onRetake={(type) => {
              if (type === "front") setStep(1);
              if (type === "rear") setStep(2);
              if (type === "side") setStep(3);
            }}
            onSubmit={handleSubmit}
          />
        )}
      </main>
    </div>
  );
}

export default function InspectPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-500 text-sm">Loading inspection capture session...</div>}>
      <InspectCaptureFlow />
    </Suspense>
  );
}
