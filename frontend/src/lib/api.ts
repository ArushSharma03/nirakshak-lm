export interface MarkerDetectionResult {
  detected: boolean;
  bounding_box: number[] | null;
  pixel_width: number | null;
  pixel_height: number | null;
  score: number | null;
  message: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function detectMarker(imageBlob: Blob): Promise<MarkerDetectionResult> {
  const formData = new FormData();
  formData.append("file", imageBlob, "capture.jpg");

  const response = await fetch(`${API_BASE}/capture/detect-marker`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}
