"use client";

import React, { useEffect, useRef, useState } from "react";

interface CameraCaptureProps {
  onCapture: (blob: Blob, previewUrl: string) => void;
  currentPreview?: string | null;
  onRetake: () => void;
}

export default function CameraCapture({ onCapture, currentPreview, onRetake }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [hasCamera, setHasCamera] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string>("");

  useEffect(() => {
    if (currentPreview) return;

    let isMounted = true;

    async function setupCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment", width: { ideal: 1920 }, height: { ideal: 1080 } },
        });
        if (isMounted) {
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
          }
          streamRef.current = stream;
          setHasCamera(true);
        } else {
          stream.getTracks().forEach(track => track.stop());
        }
      } catch (err: unknown) {
        if (isMounted) {
          setHasCamera(false);
          const message = err instanceof Error ? err.message : "Camera unavailable";
          setErrorMsg(message);
        }
      }
    }

    setupCamera();

    return () => {
      isMounted = false;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    };
  }, [currentPreview]);

  const handleCapture = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (blob) {
        const url = URL.createObjectURL(blob);
        onCapture(blob, url);
      }
    }, "image/jpeg", 0.9);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      onCapture(file, url);
    }
  };

  if (currentPreview) {
    return (
      <div className="flex flex-col items-center space-y-4">
        <div className="max-w-lg w-full aspect-[4/3] rounded-lg border border-gray-300 overflow-hidden bg-black flex items-center justify-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={currentPreview} alt="Captured preview" className="max-w-full max-h-full object-contain" />
        </div>
        <button
          onClick={onRetake}
          className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 transition-colors"
        >
          Retake
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center space-y-4">
      <div className="max-w-lg w-full aspect-[4/3] rounded-lg border border-gray-300 overflow-hidden bg-black flex flex-col items-center justify-center text-white relative">
        {hasCamera ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="p-4 text-center">
            <p className="mb-4">Camera not available ({errorMsg})</p>
            <label className="cursor-pointer bg-blue-600 px-4 py-2 rounded text-white hover:bg-blue-700">
              Upload Image
              <input type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
            </label>
          </div>
        )}
      </div>

      {hasCamera && (
        <button
          onClick={handleCapture}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Capture
        </button>
      )}
    </div>
  );
}
