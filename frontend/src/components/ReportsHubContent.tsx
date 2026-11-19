"use client";

import { TopBarContent } from "@/components/layout/TopBarContent";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import AnalysisEvidence from "@/components/AnalysisEvidence";
import DeclarationChecks from "@/components/DeclarationChecks";
import { LoadError, useInspections } from "@/components/InspectionLedger";
import { ButtonLink, Field, Loading, Notice, Badge, buttonClass, qualityTone, type Tone } from "@/components/ui";
import { CATEGORY_LABEL, VIEWS, VIEW_LABEL, capturedViews, fieldLabel, formatDate, hasSetupNotes, storageLabel } from "@/lib/format";
import { API_BASE } from "@/lib/api";
import type { Analysis } from "@/lib/analysis";
import type { ComplianceOutcome, InspectionRecord } from "@/types";

const OUTCOME_TONE: Record<ComplianceOutcome, Tone> = {
  "Manual Review Required": "warn",
  "Potential Non-Compliance": "danger",
  "Compliant within Implemented Checks": "ok",
};

const ORIGIN_LABEL: Record<Analysis["profile"]["inputs"]["origin"], string> = {
  domestic: "Domestic", imported: "Imported", unknown: "Unknown",
};

function labelValue(analysis: Analysis, name: Analysis["fields"][number]["field"]) {
  const field = analysis.fields.find((f) => f.field === name);
  if (field?.status === "observed") return field.value;
  return <span className="text-ink-3">{field?.status === "conflict" ? "Conflicting readings" : "Not read"}</span>;
}

export default function ReportsHubContent({ inspectionId: urlId }: { inspectionId: string | null }) {
  const router = useRouter();
  const { records, error, reload } = useInspections();

  const analyzed = useMemo(() => records?.filter((r) => r.analysis) ?? [], [records]);
  const selected: InspectionRecord | undefined = urlId ? records?.find((r) => r.id === urlId) : analyzed[0];

  const reportUrl = selected && `${API_BASE}/inspections/${encodeURIComponent(selected.id)}/report`;
  const choose = (id: string) => router.replace(`/reports?id=${encodeURIComponent(id)}`, { scroll: false });

  if (error) return <LoadError error={error} onRetry={reload} />;
  if (!records) return <Loading label="Loading reports from the API" />;

  return (
    <div className="page-stack">
      <TopBarContent title="Reports" lede="Review the photos, declarations and source evidence for an analyzed inspection."
        actions={selected && <>
          <Link href={`/inspect?id=${encodeURIComponent(selected.id)}`} className={buttonClass.secondary}>Photos and re-run</Link>
          {selected.analysis && <>
            <a href={`${reportUrl}?download=false`} target="_blank" rel="noreferrer" className={buttonClass.secondary}>Printable report</a>
            <a href={reportUrl} className={buttonClass.secondary}>Download report</a>
          </>}
        </>}
      />
      <div className="min-w-0 rounded-md border border-rule bg-sheet p-5 print:hidden">
        <label className="block text-sm font-medium">
          Inspection report · {analyzed.length} analyzed
          <select
            value={selected?.id ?? ""}
            onChange={(e) => choose(e.target.value)}
            className="mt-1.5 block min-h-10 w-full min-w-0 rounded-lg border border-rule-strong bg-sheet px-3 text-sm"
          >
            {analyzed.length === 0 && <option value="">No analyzed inspections</option>}
            {selected && !selected.analysis && <option value={selected.id}>{selected.id} (not analyzed)</option>}
            {analyzed.map((r) => <option key={r.id} value={r.id}>{r.id} · {r.productName}</option>)}
          </select>
        </label>
      </div>

      <div className="min-w-0">
        {urlId && !selected && (
          <Notice tone="danger" title={`No inspection ${urlId} on the API`} action={<ButtonLink href="/inspections" variant="secondary">All inspections</ButtonLink>}>
            Check the serial, or pick an analyzed inspection from the list.
          </Notice>
        )}
        {!urlId && !selected && (
          <div className="rounded-xl border border-dashed border-rule-strong bg-sheet px-6 py-12 text-center">
            <p className="font-semibold">No analyzed inspections yet</p>
            <p className="mt-1 text-sm text-ink-2">Reports appear once an inspection&rsquo;s photos have been analyzed.</p>
            <div className="mt-4 flex justify-center">
              <ButtonLink href="/inspections">Go to inspections</ButtonLink>
            </div>
          </div>
        )}
        {selected && <Report key={selected.id} record={selected} />}
      </div>
    </div>
  );
}

function Report({ record }: { record: InspectionRecord }) {
  const [plate, setPlate] = useState<"raw" | "processed">("raw");
  const [analysis, setAnalysis] = useState(record.analysis);
  const outcome = analysis?.classification?.outcome ?? record.outcome;
  const views = capturedViews(record);
  const anyProcessed = views.some((v) => record.images[v]?.processedUrl);

  return (
    <article className="page-stack">
      <section aria-label="Report details" className="overflow-hidden rounded-xl border border-rule bg-sheet">
        <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-1.5">
            <p className="serial text-sm text-ink-3">{record.id}</p>
            <h2 className="text-lg font-semibold break-words">{record.productName}</h2>
            <p className="text-sm text-ink-2">
              {formatDate(record.timestamp, true)} · {CATEGORY_LABEL[record.productCategory] ?? record.productCategory} · stored in {storageLabel(record)}
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-start gap-3 sm:items-end">
            <Badge tone={OUTCOME_TONE[outcome] ?? "warn"} large>
              {outcome}
            </Badge>

            {analysis?.classification && <p className="max-w-sm text-sm text-ink-2">{analysis.classification.reason}</p>}
          </div>
        </div>
        <hr className="border-rule" />
        {analysis && (
          <div className="space-y-2 p-5">
            <span className="field-label">Read from the label · unverified OCR, evidence below</span>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <Field label="Brand">{record.labelBrand || <span className="text-ink-3">Not read</span>}</Field>
              {(["net_quantity", "mrp", "date", "expiry"] as const).map((name) => (
                <Field key={name} label={fieldLabel(name)}>{labelValue(analysis, name)}</Field>
              ))}
              <Field label="Origin">{ORIGIN_LABEL[analysis.profile.inputs.origin]}</Field>
            </div>
          </div>
        )}
        {hasSetupNotes(record) && (
          <div className="grid gap-5 border-t border-rule p-5 sm:grid-cols-2">
            <div className="space-y-1">
              <span className="field-label">Photo source</span>
              <p className="text-sm">{record.notes || <span className="text-ink-3">Not recorded at setup.</span>}</p>
            </div>
            <div className="space-y-2">
              <span className="field-label">Setup notes · typed at setup, not read from the label</span>
              <div className="grid grid-cols-2 gap-3 text-ink-2">
                <Field label="Brand">{record.brand || "Blank"}</Field>
                <Field label="Net quantity">{record.declaredNetQty || "Blank"}</Field>
                <Field label="MRP">{record.declaredMRP !== null ? `₹${record.declaredMRP.toFixed(2)}` : "Blank"}</Field>
                <Field label="Inspector">{record.inspectorName || "Blank"}</Field>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Photos */}
      <section className="space-y-3" aria-labelledby="photos">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="photos" className="text-base font-semibold">Photos</h2>
          {anyProcessed && (
            <div role="group" aria-label="Photo version" className="inline-flex rounded-lg border border-rule-strong bg-sheet p-0.5 print:hidden">
              {(["raw", "processed"] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  aria-pressed={plate === mode}
                  onClick={() => setPlate(mode)}
                  className={`min-h-8 rounded-md px-3 text-sm font-medium ${plate === mode ? "bg-rail text-white" : "text-ink-2 hover:text-ink"}`}
                >
                  {mode === "raw" ? "Original" : "Enhanced (CLAHE)"}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {VIEWS.map((view) => {
            const img = record.images[view];
            const url = plate === "processed" && img?.processedUrl ? img.processedUrl : img?.previewUrl;
            const quality = img?.quality_assessment;
            return (
              <figure key={view} className="overflow-hidden rounded-xl border border-rule bg-sheet">
                <div className="aspect-[4/3] bg-ground">
                  {url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img loading="eager" src={url} alt={`${VIEW_LABEL[view]} panel`} className="size-full object-contain" />
                  ) : (
                    <span className="grid size-full place-items-center text-sm text-ink-3">No {VIEW_LABEL[view].toLowerCase()} photo</span>
                  )}
                </div>
                <figcaption className="space-y-1.5 px-3 py-2.5">
                  <span className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold">{VIEW_LABEL[view]}</span>
                    {quality && <Badge tone={qualityTone(quality.overall_status)}>{quality.overall_status}</Badge>}
                  </span>
                  {img && (
                    <span className="block text-xs text-ink-3">
                      {quality ? `Optical score ${quality.composite_score}/100` : "No optical check"}
                      {img.originalFilename && <span className="serial block truncate">{img.originalFilename}</span>}
                    </span>
                  )}
                  {url && <a href={url} target="_blank" rel="noreferrer" className="block text-xs font-medium text-accent underline underline-offset-2" aria-label={`Open ${VIEW_LABEL[view].toLowerCase()} photo full size`}>Open full-size photo</a>}
                </figcaption>
              </figure>
            );
          })}
        </div>
        <p className="text-xs text-ink-3">The optical score rates the original photo&rsquo;s sharpness, exposure, contrast, glare and resolution. It is not OCR accuracy and says nothing about compliance.</p>
      </section>

      {analysis ? (
        <>
          <DeclarationChecks id={record.id} analysis={analysis} onUpdate={setAnalysis} />
          <AnalysisEvidence analysis={analysis} />
        </>
      ) : (
        <Notice
          tone="warn"
          title="Not analyzed yet"
          action={<ButtonLink href={`/inspect?id=${encodeURIComponent(record.id)}`}>{views.length ? "Analyze photos" : "Add photos"}</ButtonLink>}
        >
          No declarations have been read and no rule profile has been selected for this inspection.
        </Notice>
      )}

      <p className="border-t border-rule pt-4 text-xs leading-relaxed text-ink-3">
        Automated screening record from Nirikshak-LM. It supports an inspector and is not a statutory finding. Physically verify the package before any notice under the Legal Metrology Act, 2009.
      </p>
    </article>
  );
}
