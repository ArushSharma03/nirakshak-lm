"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";

interface CameraCaptureProps {
  onCapture: (blob: Blob, previewUrl: string) => void;
  currentPreview?: string | null;
  onRetake: () => void;
}

export default function CameraCapture({ onCapture, currentPreview, onRetake }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [hasCamera, setHasCamera] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [retryKey, setRetryKey] = useState<number>(0);

  // Multi-camera support
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const [currentDeviceId, setCurrentDeviceId] = useState<string>("");
  const [activeDeviceLabel, setActiveDeviceLabel] = useState<string>("");

  const stopStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // ignore
        }
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  // Enumerate video devices
  const refreshDevices = useCallback(async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
    try {
      const allDevices = await navigator.mediaDevices.enumerateDevices();
      const videoInputs = allDevices.filter((d) => d.kind === "videoinput");
      setDevices(videoInputs);
    } catch (e) {
      console.warn("Failed to enumerate devices:", e);
    }
  }, []);

  useEffect(() => {
    if (currentPreview) {
      stopStream();
      return;
    }

    let isMounted = true;

    async function setupCamera() {
      if (typeof window === "undefined") return;

      // 1. Check secure context (localhost or HTTPS)
      const isLocalhost =
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1" ||
        window.location.hostname === "[::1]";

      if (!window.isSecureContext && !isLocalhost) {
        if (isMounted) {
          setHasCamera(false);
          setErrorMsg("Camera access requires a secure context. Please open http://localhost:3000 in your browser.");
          setIsLoading(false);
        }
        return;
      }

      // 2. Check MediaDevices support
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        if (isMounted) {
          setHasCamera(false);
          setErrorMsg("Camera API (navigator.mediaDevices.getUserMedia) is not supported in this browser.");
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      setErrorMsg("");

      // Stop any existing stream before opening new one
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }

      // 3. Progressive constraint fallback cascade
      const constraintsList: MediaStreamConstraints[] = [];

      if (selectedDeviceId) {
        constraintsList.push({
          video: {
            deviceId: { exact: selectedDeviceId },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        });
        constraintsList.push({
          video: {
            deviceId: { exact: selectedDeviceId },
          },
          audio: false,
        });
      }

      // General fallback constraints
      constraintsList.push(
        {
          video: {
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        },
        {
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        },
        {
          video: true,
          audio: false,
        }
      );

      let activeStream: MediaStream | null = null;
      let caughtError: unknown = null;

      for (const constraints of constraintsList) {
        try {
          activeStream = await navigator.mediaDevices.getUserMedia(constraints);
          if (activeStream) break;
        } catch (err: unknown) {
          caughtError = err;
        }
      }

      if (!activeStream) {
        if (isMounted) {
          setHasCamera(false);
          setIsLoading(false);

          let friendlyMessage = "Unable to access camera.";
          if (caughtError instanceof DOMException) {
            switch (caughtError.name) {
              case "NotAllowedError":
              case "PermissionDeniedError":
                friendlyMessage =
                  "Camera permission was denied. Please allow camera permissions in your browser address bar and click Retry.";
                break;
              case "NotFoundError":
              case "DevicesNotFoundError":
                friendlyMessage = "No camera hardware detected on this device. You can use the upload option below.";
                break;
              case "NotReadableError":
              case "TrackStartError":
                friendlyMessage =
                  "Camera is already in use by another application. Please close other webcam apps and click Retry.";
                break;
              case "OverconstrainedError":
                friendlyMessage = "Camera could not satisfy the requested resolution.";
                break;
              default:
                friendlyMessage = `Camera error: ${caughtError.message || caughtError.name}`;
            }
          } else if (caughtError instanceof Error) {
            friendlyMessage = caughtError.message;
          }

          setErrorMsg(friendlyMessage);
        }
        return;
      }

      if (!isMounted) {
        activeStream.getTracks().forEach((track) => track.stop());
        return;
      }

      streamRef.current = activeStream;
      setHasCamera(true);
      setIsLoading(false);

      // Track active device metadata without triggering re-render cascades
      const videoTrack = activeStream.getVideoTracks()[0];
      if (videoTrack) {
        const settings = videoTrack.getSettings();
        if (settings.deviceId) {
          setCurrentDeviceId(settings.deviceId);
        }
        if (videoTrack.label) {
          setActiveDeviceLabel(videoTrack.label);
        }
      }

      // Enumerate available devices once permission is granted
      refreshDevices();

      // Attach stream to video
      if (videoRef.current && videoRef.current.srcObject !== activeStream) {
        videoRef.current.srcObject = activeStream;
        videoRef.current.muted = true;
        const playPromise = videoRef.current.play();
        if (playPromise !== undefined) {
          playPromise.catch((playErr: unknown) => {
            const errName = playErr instanceof DOMException ? playErr.name : "";
            if (errName !== "AbortError") {
              console.warn("Video playback was interrupted or prevented:", playErr);
            }
          });
        }
      }
    }

    setupCamera();

    return () => {
      isMounted = false;
      stopStream();
    };
  }, [currentPreview, retryKey, selectedDeviceId, stopStream, refreshDevices]);

  // Ensure stream stays attached if ref mounts after stream is acquired
  useEffect(() => {
    if (hasCamera && videoRef.current && streamRef.current && videoRef.current.srcObject !== streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.muted = true;
      const playPromise = videoRef.current.play();
      if (playPromise !== undefined) {
        playPromise.catch((playErr: unknown) => {
          const errName = playErr instanceof DOMException ? playErr.name : "";
          if (errName !== "AbortError") {
            console.warn("Video playback error on ref sync:", playErr);
          }
        });
      }
    }
  });

  const handleCapture = () => {
    const video = videoRef.current;
    if (!video) return;
    const width = video.videoWidth || 1280;
    const height = video.videoHeight || 720;

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, width, height);

    canvas.toBlob(
      (blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          onCapture(blob, url);
        }
      },
      "image/jpeg",
      0.92
    );
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      onCapture(file, url);
    }
  };

  const handleSwitchCamera = () => {
    if (devices.length < 2) return;
    const currentId = selectedDeviceId || currentDeviceId;
    const currentIndex = devices.findIndex((d) => d.deviceId === currentId);
    const nextIndex = (currentIndex + 1) % devices.length;
    const nextDevice = devices[nextIndex];
    if (nextDevice) {
      setIsStreaming(false);
      setSelectedDeviceId(nextDevice.deviceId);
      if (nextDevice.label) {
        setActiveDeviceLabel(nextDevice.label);
      }
    }
  };

  // Preview Mode
  if (currentPreview) {
    return (
      <div className="flex flex-col items-center space-y-4">
        <div className="max-w-lg w-full aspect-[4/3] rounded-lg border border-gray-300 overflow-hidden bg-black flex items-center justify-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={currentPreview} alt="Captured preview" className="max-w-full max-h-full object-contain" />
        </div>
        <button
          onClick={onRetake}
          className="px-5 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors font-medium shadow-sm flex items-center space-x-2"
        >
          <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>Retake View</span>
        </button>
      </div>
    );
  }

  // Active Camera / Fallback Mode
  const currentCamIndex = devices.findIndex((d) => d.deviceId === (selectedDeviceId || currentDeviceId));

  return (
    <div className="flex flex-col items-center space-y-4">
      <div className="max-w-lg w-full aspect-[4/3] rounded-lg border border-gray-300 overflow-hidden bg-black flex flex-col items-center justify-center text-white relative shadow-inner">
        {/* Video element is ALWAYS mounted while in camera mode */}
        {hasCamera && (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            onLoadedMetadata={(e) => {
              const p = e.currentTarget.play();
              if (p !== undefined) p.catch(() => {});
              setIsStreaming(true);
            }}
            onPlay={() => setIsStreaming(true)}
            className={`w-full h-full object-cover transition-opacity duration-300 ${
              isStreaming ? "opacity-100" : "opacity-0"
            }`}
          />
        )}

        {/* Live indicator & device switcher overlay */}
        {isStreaming && (
          <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none z-20">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/90 text-white shadow-sm backdrop-blur-xs">
              <span className="w-2 h-2 mr-1.5 rounded-full bg-white animate-pulse"></span>
              Live Feed
            </span>

            {devices.length > 1 && (
              <button
                type="button"
                onClick={handleSwitchCamera}
                className="pointer-events-auto inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-black/60 hover:bg-black/80 text-white border border-white/20 shadow-sm backdrop-blur-xs transition-colors"
                title={activeDeviceLabel || "Switch Camera"}
              >
                <svg className="w-3.5 h-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Switch Cam ({currentCamIndex >= 0 ? currentCamIndex + 1 : 1}/{devices.length})
              </button>
            )}
          </div>
        )}

        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-slate-950/80 flex flex-col items-center justify-center p-4 text-center z-10">
            <svg className="animate-spin h-8 w-8 text-blue-400 mb-2" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="text-sm font-medium text-gray-200">Initializing camera feed...</p>
            <p className="text-xs text-gray-400 mt-1">Requesting video stream from device</p>
          </div>
        )}

        {/* Error / No Camera overlay */}
        {!isLoading && !hasCamera && (
          <div className="p-6 text-center max-w-md z-10">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </div>
            <p className="font-semibold text-gray-100 mb-1">Camera Unavailable</p>
            <p className="text-xs text-gray-300 mb-4">{errorMsg}</p>
            <div className="flex flex-wrap items-center justify-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setHasCamera(true);
                  setRetryKey((k) => k + 1);
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm font-medium transition-colors"
              >
                Retry Camera
              </button>
              <label className="cursor-pointer bg-blue-600 px-4 py-2 rounded text-sm text-white hover:bg-blue-700 font-medium transition-colors">
                Upload Image
                <input type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
              </label>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center space-x-3">
        {hasCamera && (
          <button
            onClick={handleCapture}
            disabled={isLoading}
            className={`px-6 py-2.5 rounded-lg font-medium shadow-sm flex items-center space-x-2 transition-colors ${
              isLoading
                ? "bg-gray-400 text-white cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <circle cx="12" cy="12" r="3" strokeWidth="2" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            </svg>
            <span>Capture Frame</span>
          </button>
        )}

        <label className="cursor-pointer px-4 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-colors border border-gray-200 flex items-center space-x-1.5">
          <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          <span>Upload File Instead</span>
          <input type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
        </label>
      </div>
    </div>
  );
}
