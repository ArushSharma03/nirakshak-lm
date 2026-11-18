import { z } from "zod";

const probability = z.number().min(0).max(1);
const view = z.enum(["front", "rear", "side"]);
const fieldName = z.enum(["generic_name", "net_quantity", "mrp", "manufacturer", "date", "consumer_care", "country_of_origin"]);
const box = z.object({ x0: z.number(), y0: z.number(), x1: z.number(), y1: z.number() });
const line = z.object({ text: z.string(), box: box.nullable(), confidence: probability.nullable() });
const candidate = z.object({
  field: fieldName, value: z.string(), view, provider: z.string(), source_text: z.string(),
  box: box.nullable(), confidence: probability.nullable(), height_mm: z.number().nullable(),
  glyph_box: box.nullable().optional(),
});
export const profileInputsSchema = z.object({
  category: z.enum(["food_grocery", "beverage", "personal_care", "household"]),
  origin: z.enum(["domestic", "imported", "unknown"]), as_of: z.string(),
});
export const ruleSchema = z.object({
  id: z.string(), version: z.string(), citation: z.string(), field: fieldName,
  requirement: z.string(), effective_from: z.string(), effective_to: z.string().nullable(),
  origins: z.array(z.enum(["domestic", "imported"])), source_url: z.string(),
  required_view: view.nullable().optional(), minimum_glyph_height_mm: z.number().positive().nullable().optional(),
  constraints_verified: z.boolean().optional(),
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
    ocr: z.array(z.object({ provider: z.string(), model: z.string(), status: z.enum(["ok", "partial", "unavailable", "failed"]), lines: z.array(line), message: z.string(), raw_text: z.string().nullable().optional() })),
  })),
  fields: z.array(z.object({ field: fieldName, status: z.enum(["observed", "conflict", "missing"]), value: z.string().nullable(), evidence: z.array(candidate), reason: z.string() })),
  profile: profileSchema, warnings: z.array(z.string()),
  classification: z.object({
    outcome: z.enum(["Manual Review Required", "Potential Non-Compliance", "Compliant within Implemented Checks"]),
    reason: z.string(),
  }).nullish(),
  checks: z.object({
    version: z.string(), scope: z.string(),
    results: z.array(z.object({
      rule_id: z.string(), field: fieldName,
      kind: z.enum(["presence", "completeness", "units", "consistency", "placement", "readability", "character_height"]),
      status: z.enum(["pass", "fail", "insufficient_evidence", "not_applicable"]), reason: z.string(),
      citation: z.string(), source_url: z.string(), evidence: z.array(candidate),
      measured_mm: z.number().nullable(), required_mm: z.number().nullable(),
    })),
  }).nullable().optional(),
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

const regulationIndexSchema = z.object({
  retrieved_on: z.string(), purpose: z.string(),
  sources: z.array(z.object({
    id: z.string(), title: z.string(), publisher: z.string().optional(), official_index_url: z.url(), reference_text_url: z.url(),
    sections_reviewed: z.array(z.string()), consolidation_status: z.string(),
  })),
  documents: z.array(z.object({ source_id: z.string().optional(), title: z.string(), url: z.url(), verification_status: z.string() })),
  unknowns: z.array(z.string()),
});
export type RegulationIndex = z.infer<typeof regulationIndexSchema>;

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function checkedResponse(response: Response): Promise<unknown> {
  const data: unknown = await response.json();
  if (!response.ok) {
    const error = z.object({ detail: z.string() }).safeParse(data);
    throw new Error(error.success ? error.data.detail : `Request failed (${response.status})`);
  }
  return data;
}

export async function analyzeInspection(id: string, input: Omit<ProfileInputs, "category"> & { use_jev: boolean; reuse_ocr?: boolean }): Promise<Analysis> {
  const response = await fetch(`${API_BASE}/inspections/${encodeURIComponent(id)}/analyze`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
  });
  return z.object({ analysis: analysisSchema }).parse(await checkedResponse(response)).analysis;
}

export async function checkInspection(id: string, input: Omit<ProfileInputs, "category">): Promise<Analysis> {
  const response = await fetch(`${API_BASE}/inspections/${encodeURIComponent(id)}/checks`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
  });
  return z.object({ analysis: analysisSchema }).parse(await checkedResponse(response)).analysis;
}

export async function getRuleSet(): Promise<RuleSet> {
  return rulesetSchema.parse(await checkedResponse(await fetch(`${API_BASE}/profiles/`)));
}

export async function getRegulationIndex(query: string): Promise<RegulationIndex> {
  return regulationIndexSchema.parse(await checkedResponse(await fetch(
    `${API_BASE}/profiles/regulations?q=${encodeURIComponent(query)}`,
  )));
}

export async function selectProfile(input: ProfileInputs): Promise<Profile> {
  return profileSchema.parse(await checkedResponse(await fetch(`${API_BASE}/profiles/select`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
  })));
}
