/**
 * Nirikshak-LM Core Domain Type Definitions
 * Approved Legal Metrology Packaged Commodities (LMPC) Compliance Types
 */

export type ProductCategory =
  | "food_grocery"
  | "beverage"
  | "personal_care"
  | "household";

export type ComplianceOutcome =
  | "Compliant within Implemented Checks"
  | "Potential Non-Compliance"
  | "Manual Review Required";

export type InspectionStatus =
  | "created"
  | "capturing"
  | "processing"
  | "images_uploaded"
  | "analyzed"
  | "completed"
  | "archived";

export interface PackageViewsState {
  front: boolean;
  rear: boolean;
  side: boolean;
}

export type QualityStatus = "Pass" | "Warning" | "Retake Recommended";

export interface QualityMetricItem {
  metric: string;
  name: string;
  value?: number;
  score: number;
  unit?: string;
  status: QualityStatus;
  message: string;
  width?: number;
  height?: number;
  dark_ratio_pct?: number;
  bright_ratio_pct?: number;
  total_megapixels?: number;
}

export interface QualityAssessment {
  overall_status: QualityStatus;
  is_acceptable: boolean;
  composite_score: number;
  metrics: {
    sharpness: QualityMetricItem;
    exposure: QualityMetricItem;
    contrast: QualityMetricItem;
    resolution: QualityMetricItem;
    glare: QualityMetricItem;
  };
  recommendations: string[];
  disclaimer: string;
}

export interface PreprocessingMeta {
  filename?: string;
  filepath?: string;
  processed_filename?: string;
  processed_filepath?: string;
  processed_url?: string;
  file_hash?: string;
  algorithm_version?: string;
  steps_applied?: string[];
  perspective_rectified?: boolean;
  perspective_reason?: string;
  original_dimensions?: [number, number];
  processed_dimensions?: [number, number];
  timestamp?: string;
}

export interface InspectionImageView {
  view_type: string;
  filename?: string;
  filepath?: string;
  originalFilename?: string;
  previewUrl?: string;
  processedUrl?: string;
  file_hash?: string;
  marker_detected?: boolean;
  score?: number | null;
  pixel_width?: number | null;
  pixel_height?: number | null;
  estimated_ppm?: number | null;
  quality_assessment?: QualityAssessment;
  preprocessing?: PreprocessingMeta;
}

export interface InspectionRecord {
  id: string;
  productName: string;
  productCategory: ProductCategory;
  /** Setup metadata typed by the inspector (or a server placeholder); never read from the label. */
  brand: string;
  declaredNetQty: string;
  declaredMRP: number | null;
  location?: string;
  inspectorName: string;
  notes: string;
  timestamp: string;
  status: InspectionStatus;
  outcome: ComplianceOutcome;
  viewsCaptured: PackageViewsState;
  markerDetected: boolean;
  scalePpm: number | null;
  databaseSaved: boolean;
  images: Record<string, InspectionImageView>;
  analysis?: import("@/lib/analysis").Analysis;
}

export interface SystemStatus {
  isLive: boolean;
  backendVersion?: string;
}
