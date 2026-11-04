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
  | "completed"
  | "archived";

export interface PackageViewsState {
  front: boolean;
  rear: boolean;
  side: boolean;
}

export interface RuleCheckResult {
  ruleId: string;
  ruleCode: string;
  title: string;
  statutoryCitation: string;
  status: "verified" | "violated" | "requires_review";
  extractedValue?: string;
  expectedRequirement?: string;
  confidence: number; // 0.0 - 1.0
  notes?: string;
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
  id: string; // e.g. "INS-2026-0042"
  productName: string;
  productCategory: ProductCategory;
  brand: string;
  declaredNetQty: string;
  declaredMRP: number;
  location?: string;
  inspectorName: string;
  timestamp: string;
  status: InspectionStatus;
  outcome: ComplianceOutcome;
  viewsCaptured: PackageViewsState;
  markerDetected: boolean;
  scalePpm: number | null; // Pixels per millimeter
  violationsCount: number;
  checksPassed: number;
  totalChecks: number;
  isMock: boolean;
  databaseSaved?: boolean;
  mode?: string;
  images?: Record<string, InspectionImageView>;
  ruleResults?: RuleCheckResult[];
}

export interface ComplianceRule {
  id: string;
  ruleCode: string; // e.g. "Rule 6(1)(a)"
  title: string;
  description: string;
  statutoryCitation: string;
  category: "declaration" | "dimension" | "consumer_care" | "pricing";
  mandatory: boolean;
  summaryRequirement: string;
}

export interface ProductRecord {
  id: string;
  name: string;
  category: ProductCategory;
  brand: string;
  declaredNetQty: string;
  dimensions: string;
  sampleBarcode: string;
  verifiedStandard: string;
  activeInspectionsCount: number;
}

export interface AnalyticsSummary {
  totalInspections: number;
  complianceRate: number;
  potentialViolations: number;
  manualReviewQueue: number;
  categoryDistribution: Record<ProductCategory, number>;
  topViolations: { rule: string; count: number }[];
}

export interface SystemStatus {
  isLive: boolean;
  backendVersion?: string;
  databaseAvailable: boolean;
  mode: "Live Backend" | "Demonstrator Mode";
}
