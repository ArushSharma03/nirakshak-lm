/**
 * Nirikshak-LM API Client
 *
 * Implements a dual-mode communication layer:
 * 1. Live Mode: Directly contacts the FastAPI backend at http://localhost:8000
 * 2. Demonstrator Mode (Offline Safe): Falls back cleanly to verified mock datasets
 *    when backend services or PostgreSQL are offline, guaranteeing zero demo crashes.
 */

import {
  InspectionRecord,
  ProductRecord,
  AnalyticsSummary,
  SystemStatus,
  ProductCategory,
  InspectionStatus,
  ComplianceOutcome,
  QualityAssessment,
  PreprocessingMeta,
  InspectionImageView,
} from "@/types";
import {
  MOCK_INSPECTIONS,
  MOCK_PRODUCTS,
  MOCK_ANALYTICS,
} from "./mockData";
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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getReferenceMarkerUrl(markerId = 0): string {
  return `${API_BASE}/capture/reference-marker?marker_id=${markerId}`;
}

export function getViewImageUrl(inspectionId: string, viewType: string): string {
  return `${API_BASE}/inspections/${encodeURIComponent(inspectionId)}/images/${encodeURIComponent(viewType)}`;
}

export function getProcessedImageUrl(inspectionId: string, viewType: string): string {
  return `${API_BASE}/inspections/${encodeURIComponent(inspectionId)}/images/${encodeURIComponent(viewType)}/processed`;
}

/**
 * Check backend liveness and database connectivity
 */
export async function checkBackendStatus(): Promise<SystemStatus> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    const response = await fetch(`${API_BASE}/health`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (response.ok) {
      const data = await response.json();
      return {
        isLive: true,
        backendVersion: data.version || "0.2.0",
        databaseAvailable: false, // Database connection currently unverified
        mode: "Live Backend",
      };
    }
  } catch {
    // Backend unreachable, fallback to demonstrator mode
  }

  return {
    isLive: false,
    backendVersion: undefined,
    databaseAvailable: false,
    mode: "Demonstrator Mode",
  };
}

interface BackendImageMeta {
  view_type?: string;
  filename?: string;
  filepath?: string;
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
  declared_mrp?: number;
  location?: string;
  inspector_name?: string;
  timestamp?: string;
  status?: string;
  final_outcome?: string;
  views_captured?: { front: boolean; rear: boolean; side: boolean };
  marker_detected?: boolean;
  scale_ppm?: number | null;
  violations_count?: number;
  checks_passed?: number;
  total_checks?: number;
  database_saved?: boolean;
  mode?: string;
  images?: Record<string, BackendImageMeta>;
  analysis?: unknown;
}

function mapBackendRecord(item: BackendInspectionRecord): InspectionRecord {
  const imagesMapped: Record<string, InspectionImageView> = {};

  if (item.images && typeof item.images === "object") {
    for (const [key, val] of Object.entries(item.images)) {
      const v = val as BackendImageMeta;
      imagesMapped[key] = {
        view_type: v.view_type || key,
        filename: v.filename,
        filepath: v.filepath,
        previewUrl: `${API_BASE}/inspections/${item.id}/images/${key}`,
        processedUrl: `${API_BASE}/inspections/${item.id}/images/${key}/processed`,
        marker_detected: v.marker_detected,
        score: v.marker_score ?? v.score ?? null,
        pixel_width: v.pixel_width ?? null,
        pixel_height: v.pixel_height ?? null,
        estimated_ppm: v.estimated_ppm ?? null,
        quality_assessment: v.quality_assessment,
        preprocessing: v.preprocessing,
      };
    }
  }

  return {
    id: item.id,
    productName: item.product_name || "Untitled Packaged Commodity",
    productCategory: (item.product_category as ProductCategory) || "food_grocery",
    brand: item.brand || "Unspecified Manufacturer",
    declaredNetQty: item.declared_net_qty || "N/A",
    declaredMRP: typeof item.declared_mrp === "number" ? item.declared_mrp : 0,
    location: item.location || "Retail Bay 1",
    inspectorName: item.inspector_name || "Mr. Arush Sharma",
    timestamp: item.timestamp || new Date().toISOString(),
    status: (item.status as InspectionStatus) || "created",
    outcome: (item.final_outcome || "Manual Review Required") as ComplianceOutcome,
    viewsCaptured: item.views_captured || { front: false, rear: false, side: false },
    markerDetected: !!item.marker_detected,
    scalePpm: item.scale_ppm ?? null,
    violationsCount: item.violations_count ?? (item.final_outcome === "Potential Non-Compliance" ? 1 : 0),
    checksPassed: item.checks_passed ?? 0,
    totalChecks: item.total_checks ?? 0,
    isMock: false,
    databaseSaved: !!item.database_saved,
    mode: item.mode || (item.database_saved ? "Live PostgreSQL" : "Demo / Offline Fallback"),
    images: Object.keys(imagesMapped).length > 0 ? imagesMapped : undefined,
    analysis: item.analysis ? analysisSchema.parse(item.analysis) : undefined,
  };
}

function updateLocalStorageRecord(record: InspectionRecord) {
  if (typeof window === "undefined") return;
  try {
    const existing = localStorage.getItem("nirikshak_inspections");
    const currentList: InspectionRecord[] = existing ? JSON.parse(existing) : [];
    const idx = currentList.findIndex((r) => r.id === record.id);
    if (idx !== -1) {
      currentList[idx] = { ...currentList[idx], ...record };
    } else {
      currentList.unshift(record);
    }
    localStorage.setItem("nirikshak_inspections", JSON.stringify(currentList));
  } catch {
    // Ignore storage errors
  }
}

/**
 * Retrieve inspection list (live backend with mock and local fallback)
 */
export async function getInspections(): Promise<{ records: InspectionRecord[]; isLive: boolean }> {
  let backendRecords: InspectionRecord[] = [];
  let isLive = false;

  try {
    const response = await fetch(`${API_BASE}/inspections/`, { cache: "no-store" });
    if (response.ok) {
      const data = await response.json();
      if (Array.isArray(data)) {
        backendRecords = data.map(mapBackendRecord);
        isLive = true;
      }
    }
  } catch {
    // Backend offline or error
  }

  let localRecords: InspectionRecord[] = [];
  if (typeof window !== "undefined") {
    try {
      const stored = localStorage.getItem("nirikshak_inspections");
      if (stored) {
        localRecords = JSON.parse(stored);
      }
    } catch {
      // Storage access error
    }
  }

  const seenIds = new Set<string>();
  const merged: InspectionRecord[] = [];

  for (const r of backendRecords) {
    if (!seenIds.has(r.id)) {
      seenIds.add(r.id);
      merged.push(r);
    }
  }

  for (const r of localRecords) {
    if (!seenIds.has(r.id)) {
      seenIds.add(r.id);
      merged.push(r);
    }
  }

  for (const r of MOCK_INSPECTIONS) {
    if (!seenIds.has(r.id)) {
      seenIds.add(r.id);
      merged.push(r);
    }
  }

  return { records: merged, isLive };
}

/**
 * Retrieve single inspection by ID
 */
export async function getInspectionById(id: string): Promise<InspectionRecord | null> {
  try {
    const response = await fetch(`${API_BASE}/inspections/${encodeURIComponent(id)}`, { cache: "no-store" });
    if (response.ok) {
      const data = await response.json();
      return mapBackendRecord(data);
    }
  } catch {
    // Backend offline or error
  }

  const { records } = await getInspections();
  return records.find((r) => r.id === id) || null;
}

/**
 * Create a new inspection record
 */
export async function createInspection(
  payload: Partial<InspectionRecord>
): Promise<InspectionRecord> {
  const backendPayload = {
    product_name: payload.productName || "Generic Commodity Sample",
    product_category: payload.productCategory || "food_grocery",
    brand: payload.brand || "Unspecified Manufacturer",
    declared_net_qty: payload.declaredNetQty || "100 g",
    declared_mrp: typeof payload.declaredMRP === "number" ? payload.declaredMRP : 50.0,
    location: payload.location || "Retail Inspection Bay 1",
    inspector_name: payload.inspectorName || "Mr. Arush Sharma",
    views_captured: payload.viewsCaptured || { front: false, rear: false, side: false },
    marker_detected: !!payload.markerDetected,
    scale_ppm: payload.scalePpm || null,
  };

  try {
    const response = await fetch(`${API_BASE}/inspections/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(backendPayload),
    });

    if (response.ok) {
      const data = await response.json();
      const mapped = mapBackendRecord(data);
      updateLocalStorageRecord(mapped);
      return mapped;
    }
  } catch (err) {
    console.warn("Backend /inspections/ create failed, using offline fallback:", err);
  }

  const fallbackRecord: InspectionRecord = {
    id: `INS-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 9000) + 1000)}`,
    productName: payload.productName || "Generic Commodity Sample",
    productCategory: payload.productCategory || "food_grocery",
    brand: payload.brand || "Unspecified Manufacturer",
    declaredNetQty: payload.declaredNetQty || "100 g",
    declaredMRP: payload.declaredMRP || 50.0,
    location: payload.location || "Retail Inspection Bay 1",
    inspectorName: payload.inspectorName || "Mr. Arush Sharma",
    timestamp: new Date().toISOString(),
    status: "created",
    outcome: "Manual Review Required",
    viewsCaptured: payload.viewsCaptured || { front: false, rear: false, side: false },
    markerDetected: !!payload.markerDetected,
    scalePpm: payload.scalePpm || null,
    violationsCount: 0,
    checksPassed: 0,
    totalChecks: 7,
    isMock: true,
    databaseSaved: false,
    mode: "Demo / Offline Fallback",
  };

  updateLocalStorageRecord(fallbackRecord);
  return fallbackRecord;
}

/**
 * Upload captured package view image to inspection
 */
export async function uploadInspectionView(
  inspectionId: string,
  viewType: "front" | "rear" | "side",
  imageBlob: Blob
): Promise<{
  record: InspectionRecord | null;
  markerResult: MarkerDetectionResult | null;
  qualityAssessment: QualityAssessment | null;
  processedUrl: string | null;
}> {
  try {
    const formData = new FormData();
    formData.append("view_type", viewType);
    formData.append("file", imageBlob, `${viewType}.jpg`);

    const response = await fetch(`${API_BASE}/inspections/${encodeURIComponent(inspectionId)}/images`, {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      const data = await response.json();
      const mapped = mapBackendRecord(data);

      const viewMeta = data.images?.[viewType];
      const markerResult: MarkerDetectionResult = {
        detected: viewMeta?.marker_detected ?? false,
        marker_id: viewMeta?.marker_id ?? 0,
        dictionary: viewMeta?.dictionary ?? "DICT_4X4_50",
        bounding_box: null,
        pixel_width: viewMeta?.pixel_width ?? null,
        pixel_height: viewMeta?.pixel_height ?? null,
        score: viewMeta?.marker_score ?? null,
        estimated_ppm: viewMeta?.estimated_ppm ?? null,
        message: viewMeta?.marker_detected
          ? "Reference marker detected. Confirm coplanarity before physical measurement."
          : "Reference marker not detected — calibration unavailable.",
      };

      const qualityAssessment: QualityAssessment | null = viewMeta?.quality_assessment || null;
      const processedUrl: string | null = viewMeta?.preprocessing
        ? `${API_BASE}/inspections/${encodeURIComponent(inspectionId)}/images/${viewType}/processed`
        : null;

      updateLocalStorageRecord(mapped);
      return { record: mapped, markerResult, qualityAssessment, processedUrl };
    }
    throw new Error(`Image upload failed (${response.status}). Retake or retry with the backend available.`);
  } catch (error) {
    throw error instanceof Error ? error : new Error("Image upload failed. Check backend availability.");
  }
}

/**
 * Retrieve product catalog
 */
export async function getProducts(): Promise<ProductRecord[]> {
  return MOCK_PRODUCTS;
}

/**
 * Retrieve analytics overview
 */
export async function getAnalyticsData(): Promise<AnalyticsSummary> {
  return MOCK_ANALYTICS;
}
