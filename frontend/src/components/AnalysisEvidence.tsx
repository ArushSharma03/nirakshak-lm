import type { Analysis } from "@/lib/analysis";
import { VIEW_LABEL, fieldLabel, type ViewName } from "@/lib/format";
import { Icon, Badge, type Tone } from "@/components/ui";

export function providerLabel(provider: string): string {
  if (provider === "xiaomi") return "Xiaomi-OCR";
  const detail = provider.match(/^xiaomi_detail_(\d+)$/);
  if (detail) return `Xiaomi-OCR detail scan ${Number(detail[1]) + 1}`;
  if (provider === "tesseract") return "Tesseract";
  return provider;
}

const FIELD_STATUS: Record<string, { tone: Tone; label: string }> = {
  observed: { tone: "accent", label: "Read" },
  conflict: { tone: "warn", label: "Conflicting readings" },
  missing: { tone: "neutral", label: "Not found" },
};

const PROFILE_STATUS: Record<string, { tone: Tone; label: string }> = {
  selected: { tone: "accent", label: "Profile selected" },
  review_required: { tone: "warn", label: "Profile needs review" },
  unsupported: { tone: "danger", label: "No profile for this category" },
};

function viewName(view: string): string {
  return VIEW_LABEL[view as ViewName] ?? view;
}

export default function AnalysisEvidence({ analysis }: { analysis: Analysis }) {
  const profile = analysis.profile;
  const ruleFor = (field: string) => profile.rules.find((rule) => rule.field === field);
  const profileStatus = PROFILE_STATUS[profile.status] ?? { tone: "neutral" as Tone, label: profile.status };
  const read = analysis.fields.filter((f) => f.status === "observed").length;

  return (
    <div className="page-stack">
      <section className="space-y-3" aria-labelledby="declarations">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <h2 id="declarations" className="text-base font-semibold">Declarations</h2>
          <p className="text-sm text-ink-2">
            {read} of {analysis.fields.length} read from the photos. A missing reading is not proof the declaration is absent.
          </p>
        </div>

        <ol className="divide-y divide-rule overflow-hidden rounded-xl border border-rule bg-sheet shadow-[0_1px_2px_rgb(15_23_42/0.04)]">
          {analysis.fields.map((field) => {
            const status = FIELD_STATUS[field.status] ?? { tone: "neutral" as Tone, label: field.status };
            const rule = ruleFor(field.field);
            return (
              <li key={field.field} className="grid gap-x-6 gap-y-3 px-4 py-4 lg:grid-cols-[13rem_minmax(0,1fr)]">
                <div className="space-y-1.5">
                  <p className="text-sm font-semibold">{fieldLabel(field.field)}</p>
                  {rule && <p className="text-xs text-ink-3">{rule.citation}</p>}
                  <Badge tone={status.tone}>{status.label}</Badge>
                </div>
                <div className="min-w-0 space-y-3">
                  <p className={`text-base ${field.value ? "font-semibold" : "text-ink-3"}`}>{field.value ?? (field.status === "conflict" ? "Conflicting readings. Review the source photo." : "Not extracted.")}</p>
                  <p className="text-xs text-ink-3">{field.reason}</p>
                  {field.evidence.length > 0 && (
                    <ul className="space-y-2">
                      {field.evidence.map((item, index) => (
                        <li key={`${item.provider}-${item.view}-${index}`} className="rounded-lg border border-rule bg-ground/60 px-3 py-2.5 text-sm">
                          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-2">
                            <span className="font-semibold text-ink">{viewName(item.view)} photo</span>
                            <span aria-hidden="true">·</span>
                            <span>{providerLabel(item.provider)}</span>
                            <span aria-hidden="true">·</span>
                            <span>{item.confidence === null ? "No confidence reported" : `OCR confidence ${(item.confidence * 100).toFixed(0)}%`}</span>
                            {item.height_mm !== null && (
                              <>
                                <span aria-hidden="true">·</span>
                                <span>Line box ≈ {item.height_mm} mm tall</span>
                              </>
                            )}
                          </p>
                          <blockquote className="serial mt-1.5 rounded-md bg-sheet px-2.5 py-1.5 text-[0.8rem] text-ink ring-1 ring-rule">{item.source_text}</blockquote>
                          {item.box && (
                            <p className="serial mt-1 text-xs text-ink-3">
                              Original pixels ({item.box.x0}, {item.box.y0}) to ({item.box.x1}, {item.box.y1})
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
        <p className="text-xs text-ink-3">
          Physical values estimate text-line box height in a confirmed marker plane. Glyph height, legal thresholds and compliance checks are not implemented.
        </p>
      </section>

      {analysis.warnings.length > 0 && (
        <section className="space-y-2" aria-labelledby="warnings">
          <h2 id="warnings" className="text-base font-bold">Analysis warnings</h2>
          <ul className="space-y-1 text-sm text-warn">
            {analysis.warnings.map((warning) => (
              <li key={warning} className="flex gap-2">
                <Icon name="alert" className="mt-0.5 size-3.5" />
                {warning}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-3 rounded-xl border border-rule bg-sheet p-4" aria-labelledby="profile">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="profile" className="text-base font-bold">
            Rule profile <span className="serial ml-1 text-sm font-normal text-ink-2">{[profile.id, profile.version].filter(Boolean).join(" · ")}</span>
          </h2>
          <Badge tone={profileStatus.tone}>{profileStatus.label}</Badge>
        </div>
        <p className="text-sm text-ink-2">{profile.reason}</p>
        <p className="text-sm text-warn">{profile.advisory}</p>
        <p className="text-xs text-ink-3">
          Inputs: {profile.inputs.category.replaceAll("_", " ")}, origin {profile.inputs.origin}, rules as of {profile.inputs.as_of}.
        </p>
        {profile.rules.length > 0 && (
          <details className="text-sm">
            <summary className="cursor-pointer font-semibold text-accent">{profile.rules.length} rules in this profile</summary>
            <ul className="mt-2 divide-y divide-rule">
              {profile.rules.map((rule) => (
                <li key={rule.id} className="py-2">
                  <span className="font-semibold">{rule.citation}</span> · {fieldLabel(rule.field)}
                  <span className="block text-ink-2">{rule.requirement}</span>
                  <a href={rule.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-accent hover:underline">
                    Source register <Icon name="external" className="size-3" />
                  </a>
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>

      <section className="space-y-2 rounded-xl border border-rule bg-sheet p-4 text-sm" aria-labelledby="jev">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="jev" className="text-base font-bold">Jev candidate ranking</h2>
          <Badge tone={analysis.decision.status === "ok" ? "accent" : "neutral"}>{analysis.decision.status === "ok" ? "Ran" : analysis.decision.status.replaceAll("_", " ")}</Badge>
        </div>
        <p className="text-ink-2">
          <span className="serial text-xs">{analysis.decision.model}</span> {analysis.decision.message}
        </p>
        {Object.entries(analysis.decision.answers).map(([field, answer]) => {
          const evidence = analysis.fields.find((item) => item.field === field)?.evidence;
          const index = Number(answer.choice.replace("candidate_", ""));
          const chosen = answer.choice === "none" ? "No reliable candidate" : evidence?.[index]?.value || "Candidate not in evidence list";
          return (
            <p key={field}>
              {fieldLabel(field)}: <strong>{chosen}</strong> <span className="text-ink-3">· model confidence {(answer.confidence * 100).toFixed(0)}%</span>
            </p>
          );
        })}
      </section>

      <section className="space-y-3" aria-labelledby="transcripts">
        <h2 id="transcripts" className="text-base font-bold">OCR transcripts and calibration</h2>
        <p className="text-sm text-ink-2">
          Xiaomi-OCR is the primary reading. Tesseract supplies line positions, used only where its text matches the primary reading.
        </p>
        <div className="space-y-2">
          {Object.entries(analysis.views).map(([view, result]) => (
            <details key={view} className="rounded-xl border border-rule bg-sheet">
              <summary className="flex cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 text-sm">
                <span className="font-semibold">{viewName(view)} photo</span>
                <span className="text-ink-3">
                  {result.ocr.length} transcript{result.ocr.length === 1 ? "" : "s"} · scale {result.calibration.status}
                </span>
                <span className="serial ml-auto text-xs text-ink-3" title="SHA-256 of the original photo">
                  {result.file_hash.slice(0, 12)}
                </span>
              </summary>
              <div className="space-y-4 border-t border-rule px-4 py-4">
                <p className="text-sm text-ink-2">
                  Calibration: {result.calibration.reason}
                  {result.calibration.pixels_per_mm !== null && ` (${result.calibration.pixels_per_mm} px/mm)`}
                </p>
                {result.ocr.map((ocr) => (
                  <div key={ocr.provider} className="space-y-1.5">
                    <p className="flex flex-wrap items-center gap-2 text-sm">
                      <span className="font-semibold">{providerLabel(ocr.provider)}</span>
                      <Badge tone={ocr.status === "ok" ? "neutral" : "danger"}>{ocr.status}</Badge>
                      <span className="text-xs text-ink-3">{ocr.lines.length} lines</span>
                    </p>
                    <p className="text-xs text-ink-3">
                      <span className="serial">{ocr.model}</span> · {ocr.message}
                    </p>
                    {ocr.lines.length > 0 && (
                      <pre className="serial max-h-72 overflow-auto rounded-md bg-ground px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap text-ink">
                        {ocr.lines.map((line) => line.text).join("\n")}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
