"use client";

import { useCallback, useEffect, useRef, useState, type ChangeEvent } from "react";
import { Icon, buttonClass } from "@/components/ui";

interface CameraCaptureProps {
  onCapture: (photos: Blob[]) => void;
  /** Let the file picker return several photos at once. The camera still takes one. */
  multiple?: boolean;
  disabled?: boolean;
  hint?: string;
}

/** The API stores only JPEG and PNG evidence; re-encode anything else the browser can decode. */
async function uploadable(file: File): Promise<Blob> {
  if (file.type === "image/jpeg" || file.type === "image/png") return file;
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    throw new Error(`This browser cannot read ${file.name}. Use a JPEG or PNG photo.`);
  }
  const canvas = document.createElement("canvas");
  canvas.width = bitmap.width;
  canvas.height = bitmap.height;
  canvas.getContext("2d")?.drawImage(bitmap, 0, 0);
  bitmap.close();
  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error(`${file.name} could not be converted to JPEG.`))), "image/jpeg", 0.92),
  );
}

function cameraErrorMessage(error: unknown): string {
  if (error instanceof DOMException) {
    switch (error.name) {
      case "NotAllowedError":
      case "PermissionDeniedError":
        return "Camera permission was denied. Allow it in the browser address bar and try again, or upload a photo.";
      case "NotFoundError":
      case "DevicesNotFoundError":
        return "No camera was found on this device. Upload a photo instead.";
      case "NotReadableError":
      case "TrackStartError":
        return "Another app is using the camera. Close it and try again.";
      case "OverconstrainedError":
        return "The camera could not satisfy the requested resolution.";
      default:
        return `Camera error: ${error.message || error.name}`;
    }
  }
  return error instanceof Error ? error.message : "The camera could not be started.";
}

export default function CameraCapture({ onCapture, multiple = false, disabled = false, hint = "Fill the frame with this panel. Keep small text in focus and avoid glare." }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraOn, setCameraOn] = useState(false);
  const [starting, setStarting] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [deviceLabel, setDeviceLabel] = useState("");

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setStreaming(false);
  }, []);

  useEffect(() => {
    if (!cameraOn) return;
    let alive = true;

    async function start() {
      if (!window.isSecureContext) {
        setErrorMsg("The camera needs a secure page (https or localhost). Upload a photo instead.");
        setCameraOn(false);
        return;
      }
      if (!navigator.mediaDevices?.getUserMedia) {
        setErrorMsg("This browser does not support camera capture. Upload a photo instead.");
        setCameraOn(false);
        return;
      }
      setStarting(true);
      setErrorMsg("");
      stopStream();

      const attempts: MediaStreamConstraints[] = [
        ...(deviceId ? [{ video: { deviceId: { exact: deviceId }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false }] : []),
        { video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false },
        { video: true, audio: false },
      ];

      let stream: MediaStream | null = null;
      let lastError: unknown = null;
      for (const constraints of attempts) {
        try {
          stream = await navigator.mediaDevices.getUserMedia(constraints);
          break;
        } catch (error) {
          lastError = error;
        }
      }

      if (!alive) {
        stream?.getTracks().forEach((track) => track.stop());
        return;
      }
      setStarting(false);
      if (!stream) {
        setErrorMsg(cameraErrorMessage(lastError));
        setCameraOn(false);
        return;
      }

      streamRef.current = stream;
      const track = stream.getVideoTracks()[0];
      if (track?.label) setDeviceLabel(track.label);
      try {
        const all = await navigator.mediaDevices.enumerateDevices();
        if (alive) setDevices(all.filter((d) => d.kind === "videoinput"));
      } catch {
        // device list is optional
      }
      const video = videoRef.current;
      if (video) {
        video.srcObject = stream;
        video.muted = true;
        video.play().catch(() => undefined);
      }
    }

    void start();
    return () => {
      alive = false;
      stopStream();
    };
  }, [cameraOn, deviceId, stopStream]);

  const capture = () => {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        setCameraOn(false);
        onCapture([blob]);
      },
      "image/jpeg",
      0.92,
    );
  };

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = [...(event.target.files ?? [])];
    event.target.value = "";
    if (files.length === 0) return;
    setCameraOn(false);
    setErrorMsg("");
    try {
      onCapture(await Promise.all(files.map(uploadable)));
    } catch (cause) {
      setErrorMsg(cause instanceof Error ? cause.message : "The photo could not be read.");
    }
  };

  const switchCamera = () => {
    if (devices.length < 2) return;
    const current = devices.findIndex((d) => d.deviceId === (deviceId || streamRef.current?.getVideoTracks()[0]?.getSettings().deviceId));
    setDeviceId(devices[(current + 1) % devices.length].deviceId);
  };

  const uploadButton = (
    <label className={`${cameraOn ? buttonClass.secondary : buttonClass.primary} cursor-pointer ${disabled ? "pointer-events-none opacity-45" : ""}`}>
      <Icon name="upload" />
      {multiple ? "Upload photos" : "Upload photo"}
      <input type="file" accept="image/*" multiple={multiple} onChange={(event) => void upload(event)} disabled={disabled} className="sr-only" />
    </label>
  );

  if (!cameraOn) {
    return (
      <div className="grid min-h-64 place-items-center rounded-xl border-2 border-dashed border-rule-strong bg-sheet px-6 py-10 text-center">
        <div className="space-y-4">
          <p className="mx-auto max-w-sm text-sm text-ink-2">{hint}</p>
          <div className="flex flex-wrap justify-center gap-2">
            {uploadButton}
            <button type="button" disabled={disabled} onClick={() => setCameraOn(true)} className={buttonClass.secondary}>
              <Icon name="camera" />
              Use camera
            </button>
          </div>
          {errorMsg && (
            <p role="alert" className="mx-auto max-w-sm text-sm text-danger">
              {errorMsg}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-ink">
        <video
          ref={videoRef}
          playsInline
          muted
          autoPlay
          onPlaying={() => setStreaming(true)}
          className={`size-full object-cover transition-opacity duration-300 ${streaming ? "opacity-100" : "opacity-0"}`}
        />
        {/* framing guide */}
        <div aria-hidden="true" className="pointer-events-none absolute inset-[8%] rounded-md border border-dashed border-white/50" />
        {(starting || !streaming) && (
          <p role="status" className="absolute inset-0 grid place-items-center text-sm text-white/80">
            Starting camera…
          </p>
        )}
        {streaming && deviceLabel && (
          <span className="absolute left-3 top-3 max-w-[70%] truncate rounded bg-black/60 px-2 py-1 text-xs text-white">{deviceLabel}</span>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={capture} disabled={!streaming || disabled} className={buttonClass.primary}>
          <Icon name="camera" />
          Take photo
        </button>
        {devices.length > 1 && (
          <button type="button" onClick={switchCamera} className={buttonClass.secondary}>
            <Icon name="switch" />
            Switch camera
          </button>
        )}
        {uploadButton}
        <button type="button" onClick={() => setCameraOn(false)} className={buttonClass.quiet}>
          Cancel
        </button>
      </div>
    </div>
  );
}
