/**
 * Nirikshak-LM API client.
 *
 * Talks only to the FastAPI backend. There is no sample-data fallback: when the
 * API is unreachable, calls throw and the UI shows an offline state.
 */

import {
  InspectionRecord,
  SystemStatus,
  ProductCategory,
  InspectionStatus,
  ComplianceOutcome,
  QualityAssessment,
  PreprocessingMeta,
  InspectionImageView,
} from "@/types";
import { analysisSchema } from "./analysis";

export interface MarkerDetectionResult {
  detected: boolean;
  marker_id?: number | null;
  dictionary?: string | null;
  bounding_box: number[] | null;
  pixel_width: number | null;
  pixel_height: number | null;
  score: number | null;
  estimated_ppm?: number | null;
  message: string;
}

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiUnavailableError extends Error {
  constructor(message = `The inspection API at ${API_BASE} is not reachable.`) {
    super(message);
    this.name = "ApiUnavailableError";
  }
}

export function getReferenceMarkerUrl(markerId = 0): string {
  return `${API_BASE}/capture/reference-marker?marker_id=${markerId}`;
}

export function getViewImageUrl(inspectionId: string, viewType: string): string {
  return `${API_BASE}/inspections/${encodeURIComponent(inspectionId)}/images/${encodeURIComponent(viewType)}`;
}

export function getProcessedImageUrl(inspectionId: string, viewType: string): string {
  return `${getViewImageUrl(inspectionId, viewType)}/processed`;
}

export async function checkBackendStatus(): Promise<SystemStatus> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);
    const response = await fetch(`${API_BASE}/health`, { signal: controller.signal, cache: "no-store" });
    clearTimeout(timeoutId);
    if (response.ok) {
      const data: { version?: string } = await response.json();
      return { isLive: true, backendVersion: data.version };
    }
  } catch {
    // unreachable
  }
  return { isLive: false };
}

interface BackendImageMeta {
  view_type?: string;
  filename?: string;
  filepath?: string;
  original_filename?: string;
  file_hash?: string;
  marker_detected?: boolean;
  marker_score?: number | null;
  score?: number | null;
  pixel_width?: number | null;
  pixel_height?: number | null;
  estimated_ppm?: number | null;
  marker_id?: number | null;
  dictionary?: string | null;
  quality_assessment?: QualityAssessment;
  preprocessing?: PreprocessingMeta;
}

interface BackendInspectionRecord {
  id: string;
  product_name?: string;
  product_category?: string;
  brand?: string;
  declared_net_qty?: string;
  declared_mrp?: number | null;
  location?: string;
  inspector_name?: string;
  notes?: string | null;
  timestamp?: string;
  status?: string;
  final_outcome?: string;
  views_captured?: { front: boolean; rear: boolean; side: boolean };
  marker_detected?: boolean;
  scale_ppm?: number | null;
  database_saved?: boolean;
  mode?: string;
  images?: Record<string, BackendImageMeta>;
  analysis?: unknown;
}

function mapBackendRecord(item: BackendInspectionRecord): InspectionRecord {
  const images: Record<string, InspectionImageView> = {};
  for (const [key, v] of Object.entries(item.images ?? {})) {
    images[key] = {
      view_type: v.view_type || key,
      filename: v.filename,
      filepath: v.filepath,
      originalFilename: v.original_filename,
      file_hash: v.file_hash,
      previewUrl: getViewImageUrl(item.id, key),
      processedUrl: v.preprocessing ? getProcessedImageUrl(item.id, key) : undefined,
      marker_detected: v.marker_detected,
      score: v.marker_score ?? v.score ?? null,
      pixel_width: v.pixel_width ?? null,
      pixel_height: v.pixel_height ?? null,
      estimated_ppm: v.estimated_ppm ?? null,
      quality_assessment: v.quality_assessment,
      preprocessing: v.preprocessing,
    };
  }

  return {
    id: item.id,
    productName: item.product_name || "Untitled package",
    productCategory: (item.product_category as ProductCategory) || "food_grocery",
    brand: item.brand || "",
    declaredNetQty: item.declared_net_qty || "",
    declaredMRP: typeof item.declared_mrp === "number" ? item.declared_mrp : null,
    location: item.location,
    inspectorName: item.inspector_name || "",
    notes: item.notes || "",
    timestamp: item.timestamp || "",
    status: (item.status as InspectionStatus) || "created",
    outcome: (item.final_outcome || "Manual Review Required") as ComplianceOutcome,
    viewsCaptured: item.views_captured || { front: false, rear: false, side: false },
    markerDetected: !!item.marker_detected,
    scalePpm: item.scale_ppm ?? null,
    databaseSaved: !!item.database_saved,
    images,
    analysis: item.analysis ? analysisSchema.parse(item.analysis) : undefined,
  };
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });
  } catch {
    throw new ApiUnavailableError();
  }
}

async function errorFrom(response: Response, fallback: string): Promise<Error> {
  try {
    const data: unknown = await response.json();
    if (data && typeof data === "object" && "detail" in data && typeof data.detail === "string") {
      return new Error(data.detail);
    }
  } catch {
    // body was not JSON
  }
  return new Error(`${fallback} (HTTP ${response.status}).`);
}

export async function getInspections(): Promise<InspectionRecord[]> {
  const response = await request("/inspections/");
  if (!response.ok) throw await errorFrom(response, "Could not load inspections");
  const data: unknown = await response.json();
  if (!Array.isArray(data)) throw new Error("The API returned an unexpected inspection list.");
  return (data as BackendInspectionRecord[]).map(mapBackendRecord);
}

/** Returns null when the API answers 404 for this ID. */
export async function getInspectionById(id: string): Promise<InspectionRecord | null> {
  const response = await request(`/inspections/${encodeURIComponent(id)}`);
  if (response.status === 404) return null;
  if (!response.ok) throw await errorFrom(response, "Could not load the inspection");
  return mapBackendRecord(await response.json());
}

export interface InspectionSetup {
  productName: string;
  productCategory: ProductCategory;
  brand?: string;
  declaredNetQty?: string;
  declaredMRP?: number | null;
  location?: string;
  inspectorName?: string;
  notes?: string;
}

export async function createInspection(setup: InspectionSetup): Promise<InspectionRecord> {
  const blankToNull = (value?: string) => (value && value.trim() ? value.trim() : null);
  const response = await request("/inspections/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      product_name: setup.productName.trim(),
      product_category: setup.productCategory,
      brand: blankToNull(setup.brand),
      declared_net_qty: blankToNull(setup.declaredNetQty),
      declared_mrp: setup.declaredMRP ?? null,
      location: blankToNull(setup.location),
      inspector_name: blankToNull(setup.inspectorName),
      notes: blankToNull(setup.notes),
      views_captured: { front: false, rear: false, side: false },
    }),
  });
  if (!response.ok) throw await errorFrom(response, "Could not create the inspection");
  return mapBackendRecord(await response.json());
}

export async function uploadInspectionView(
  inspectionId: string,
  viewType: "front" | "rear" | "side",
  imageBlob: Blob,
): Promise<{
  record: InspectionRecord;
  markerResult: MarkerDetectionResult;
  qualityAssessment: QualityAssessment | null;
  processedUrl: string | null;
}> {
  const formData = new FormData();
  formData.append("view_type", viewType);
  formData.append("file", imageBlob, `${viewType}.jpg`);
  const response = await request(`/inspections/${encodeURIComponent(inspectionId)}/images`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) throw await errorFrom(response, "Photo upload failed");

  const data: BackendInspectionRecord = await response.json();
  const record = mapBackendRecord(data);
  const viewMeta = data.images?.[viewType];
  const markerResult: MarkerDetectionResult = {
    detected: viewMeta?.marker_detected ?? false,
    marker_id: viewMeta?.marker_id ?? null,
    dictionary: viewMeta?.dictionary ?? null,
    bounding_box: null,
    pixel_width: viewMeta?.pixel_width ?? null,
    pixel_height: viewMeta?.pixel_height ?? null,
    score: viewMeta?.marker_score ?? null,
    estimated_ppm: viewMeta?.estimated_ppm ?? null,
    message: viewMeta?.marker_detected
      ? "Marker found. Confirm it lies flat in the label plane before relying on physical measurements."
      : "No reference marker found in this photo. Physical text height cannot be estimated for this view.",
  };
  return {
    record,
    markerResult,
    qualityAssessment: viewMeta?.quality_assessment ?? null,
    processedUrl: viewMeta?.preprocessing ? getProcessedImageUrl(inspectionId, viewType) : null,
  };
}

/** Photo removal also invalidates analysis; return the updated server record. */
export async function removeInspectionView(id: string, view: "front" | "rear" | "side"): Promise<InspectionRecord> {
  const response = await request(`/inspections/${encodeURIComponent(id)}/images/${view}`, { method: "DELETE" });
  if (!response.ok) throw await errorFrom(response, "Photo removal failed");
  const record: BackendInspectionRecord = await response.json();
  return mapBackendRecord(record);
}
