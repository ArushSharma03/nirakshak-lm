import type { InspectionRecord, InspectionStatus, ProductCategory } from "@/types";

export const VIEWS = ["front", "rear", "side"] as const;
export type ViewName = (typeof VIEWS)[number];

export const VIEW_LABEL: Record<ViewName, string> = { front: "Front", rear: "Rear", side: "Side" };

export const CATEGORY_LABEL: Record<ProductCategory, string> = {
  food_grocery: "Food and grocery",
  beverage: "Beverage",
  personal_care: "Personal care",
  household: "Household",
};

const STATUS_LABEL: Record<InspectionStatus, string> = {
  created: "Set up, no photos",
  capturing: "Capturing",
  processing: "Processing",
  images_uploaded: "Photos in, not analyzed",
  analyzed: "Analyzed",
  completed: "Completed",
  archived: "Archived",
};

export function statusLabel(status: InspectionStatus): string {
  return STATUS_LABEL[status] ?? status;
}

export function capturedViews(record: InspectionRecord): ViewName[] {
  return VIEWS.filter((view) => !!record.images[view]);
}

export function formatDate(iso: string, withTime = false): string {
  if (!iso) return "Unknown date";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}

export function storageLabel(record: InspectionRecord): string {
  return record.databaseSaved ? "PostgreSQL" : "API file store";
}

export function fieldLabel(field: string): string {
  if (field === "mrp") return "MRP";
  const text = field.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function errorText(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}
