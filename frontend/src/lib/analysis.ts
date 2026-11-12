import { z } from "zod";

const probability = z.number().min(0).max(1);
const view = z.enum(["front", "rear", "side"]);
const fieldName = z.enum(["generic_name", "net_quantity", "mrp", "manufacturer", "date", "consumer_care", "country_of_origin"]);
const box = z.object({ x0: z.number(), y0: z.number(), x1: z.number(), y1: z.number() });
const line = z.object({ text: z.string(), box: box.nullable(), confidence: probability.nullable() });
const candidate = z.object({
  field: fieldName, value: z.string(), view, provider: z.string(), source_text: z.string(),
  box: box.nullable(), confidence: probability.nullable(), height_mm: z.number().nullable(),
});
export const profileInputsSchema = z.object({
  category: z.enum(["food_grocery", "beverage", "personal_care", "household"]),
  origin: z.enum(["domestic", "imported", "unknown"]), as_of: z.string(),
});
export const ruleSchema = z.object({
  id: z.string(), version: z.string(), citation: z.string(), field: fieldName,
  requirement: z.string(), effective_from: z.string(), effective_to: z.string().nullable(),
  origins: z.array(z.enum(["domestic", "imported"])), source_url: z.string(),
});
export const profileSchema = z.object({
  status: z.enum(["selected", "review_required", "unsupported"]), id: z.string().nullable(),
  version: z.string().nullable(), reason: z.string(), inputs: profileInputsSchema,
  rules: z.array(ruleSchema), advisory: z.string(),
});
export const rulesetSchema = z.object({
  id: z.string(), version: z.string(), category: z.string(), effective_from: z.string(),
  effective_to: z.string().nullable(), review_status: z.string(), rules: z.array(ruleSchema),
});
export const analysisSchema = z.object({
  version: z.string(),
  views: z.partialRecord(view, z.object({
    file_hash: z.string(),
    calibration: z.object({
      status: z.enum(["available", "unavailable"]), reason: z.string(), marker_mm: z.number(),
      pixels_per_mm: z.number().nullable(), homography: z.array(z.array(z.number())).nullable(),
    }),
    ocr: z.array(z.object({ provider: z.string(), model: z.string(), status: z.enum(["ok", "unavailable", "failed"]), lines: z.array(line), message: z.string() })),
  })),
  fields: z.array(z.object({ field: fieldName, status: z.enum(["observed", "conflict", "missing"]), value: z.string().nullable(), evidence: z.array(candidate), reason: z.string() })),
  profile: profileSchema, warnings: z.array(z.string()),
  decision: z.object({
    status: z.enum(["ok", "unavailable", "failed", "not_needed"]), model: z.string(), message: z.string(),
    answers: z.record(z.string(), z.object({ type: z.literal("choice"), choice: z.string(), confidence: probability, probabilities: z.record(z.string(), probability) })),
    usage: z.record(z.string(), z.number().int()),
  }),
});
export type Analysis = z.infer<typeof analysisSchema>;
export type ProfileInputs = z.infer<typeof profileInputsSchema>;
export type Profile = z.infer<typeof profileSchema>;
export type RuleSet = z.infer<typeof rulesetSchema>;
export type View = z.infer<typeof view>;

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function checkedResponse(response: Response): Promise<unknown> {
  const data: unknown = await response.json();
  if (!response.ok) {
    const error = z.object({ detail: z.string() }).safeParse(data);
    throw new Error(error.success ? error.data.detail : `Request failed (${response.status})`);
  }
  return data;
}

export async function analyzeInspection(id: string, input: Omit<ProfileInputs, "category"> & { coplanar_views: View[]; use_jev: boolean }): Promise<Analysis> {
  const response = await fetch(`${API_BASE}/inspections/${encodeURIComponent(id)}/analyze`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
  });
  return z.object({ analysis: analysisSchema }).parse(await checkedResponse(response)).analysis;
}

export async function removeInspectionView(id: string, view: View): Promise<void> {
  await checkedResponse(await fetch(`${API_BASE}/inspections/${encodeURIComponent(id)}/images/${view}`, { method: "DELETE" }));
}

export async function getRuleSet(): Promise<RuleSet> {
  return rulesetSchema.parse(await checkedResponse(await fetch(`${API_BASE}/profiles/`)));
}

export async function selectProfile(input: ProfileInputs): Promise<Profile> {
  return profileSchema.parse(await checkedResponse(await fetch(`${API_BASE}/profiles/select`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
  })));
}
