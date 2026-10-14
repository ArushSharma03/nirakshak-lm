"use client";

import React, { useState } from "react";
import ViewStep from "@/components/ViewStep";
import ReviewPanel from "@/components/ReviewPanel";
import { detectMarker, type MarkerDetectionResult } from "@/lib/api";

type ViewType = "front" | "rear" | "side";

interface ViewState {
  blob: Blob | null;
  previewUrl: string | null;
  markerResult: MarkerDetectionResult | null;
  markerLoading: boolean;
}

export default function InspectPage() {
  const [step, setStep] = useState<number>(0);
  const [views, setViews] = useState<Record<ViewType, ViewState>>({
    front: { blob: null, previewUrl: null, markerResult: null, markerLoading: false },
    rear: { blob: null, previewUrl: null, markerResult: null, markerLoading: false },
    side: { blob: null, previewUrl: null, markerResult: null, markerLoading: false },
  });

  const updateView = (type: ViewType, updates: Partial<ViewState>) => {
    setViews((prev) => ({
      ...prev,
      [type]: { ...prev[type], ...updates },
    }));
  };

  const handleCapture = async (type: ViewType, blob: Blob, previewUrl: string) => {
    updateView(type, { blob, previewUrl, markerLoading: true, markerResult: null });

    try {
      const result = await detectMarker(blob);
      updateView(type, { markerResult: result, markerLoading: false });
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      updateView(type, {
        markerLoading: false,
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
    updateView(type, { blob: null, previewUrl: null, markerResult: null, markerLoading: false });
  };

  const handleSubmit = () => {
    alert("Inspection complete! Ready to submit to backend.");
  };

  const steps = ["Start", "Front", "Rear", "Side", "Review"];

  return (
    <div className="min-h-full bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex flex-col items-center">
        <h1 className="text-xl font-bold text-gray-800 mb-4">Inspection Capture</h1>

        {/* Progress indicator */}
        <div className="flex items-center space-x-2 text-sm max-w-lg w-full justify-between">
          {steps.map((s, i) => (
            <div key={s} className="flex items-center">
              <span className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
                step === i
                  ? "bg-blue-600 text-white"
                  : step > i
                    ? "bg-green-100 text-green-700"
                    : "bg-gray-100 text-gray-500"
              }`}>
                {step > i ? "✓" : i}
              </span>
              <span className={`ml-2 hidden sm:block ${step === i ? "text-gray-900 font-medium" : "text-gray-500"}`}>
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
            <h2 className="text-3xl font-bold text-gray-900 mb-4">New Inspection</h2>
            <p className="text-gray-600 mb-8">
              You will be guided to capture three views of the packaged commodity: front, rear, and side.
              Please ensure the reference marker is visible in each capture to enable calibration.
            </p>
            <button
              onClick={() => setStep(1)}
              className="px-8 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
            >
              Start Capture
            </button>
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
            onCapture={(blob, url) => handleCapture("front", blob, url)}
            onRetake={() => handleRetake("front")}
            onNext={() => setStep(2)}
            canProceed={!!views.front.previewUrl && !views.front.markerLoading}
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
            onCapture={(blob, url) => handleCapture("rear", blob, url)}
            onRetake={() => handleRetake("rear")}
            onNext={() => setStep(3)}
            canProceed={!!views.rear.previewUrl && !views.rear.markerLoading}
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
            onCapture={(blob, url) => handleCapture("side", blob, url)}
            onRetake={() => handleRetake("side")}
            onNext={() => setStep(4)}
            canProceed={!!views.side.previewUrl && !views.side.markerLoading}
          />
        )}

        {step === 4 && (
          <ReviewPanel
            views={[
              { viewType: "front", label: "Front View", previewUrl: views.front.previewUrl, markerResult: views.front.markerResult },
              { viewType: "rear", label: "Rear View", previewUrl: views.rear.previewUrl, markerResult: views.rear.markerResult },
              { viewType: "side", label: "Side View", previewUrl: views.side.previewUrl, markerResult: views.side.markerResult },
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
