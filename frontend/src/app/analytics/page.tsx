"use client";

import { TopBarContent } from "@/components/layout/TopBarContent";

import { useMemo } from "react";
import { LoadError, progressOf, useInspections } from "@/components/InspectionLedger";
import { providerLabel } from "@/components/AnalysisEvidence";
import { Card, EmptyState, Loading, Meter } from "@/components/ui";
import { CATEGORY_LABEL, VIEWS, VIEW_LABEL, fieldLabel } from "@/lib/format";
import type { InspectionRecord, ProductCategory } from "@/types";

const FIELD_ORDER = ["generic_name", "net_quantity", "mrp", "manufacturer", "date", "consumer_care", "country_of_origin"];

function summarize(records: InspectionRecord[]) {
  const analyzed = records.filter((r) => r.analysis);

  const fields = FIELD_ORDER.map((field) => {
    const tally = { observed: 0, conflict: 0, missing: 0 };
    for (const r of analyzed) {
      const hit = r.analysis!.fields.find((f) => f.field === field);
      if (hit) tally[hit.status] += 1;
    }
    return { field, ...tally, total: tally.observed + tally.conflict + tally.missing };
  });

  const optics = VIEWS.map((view) => {
    const scores = records.map((r) => r.images[view]?.quality_assessment).filter((q): q is NonNullable<typeof q> => !!q);
    const sorted = scores.map((q) => q.composite_score).sort((a, b) => a - b);
    const median = sorted.length ? sorted[Math.floor((sorted.length - 1) / 2)] : null;
    return {
      view,
      photos: records.filter((r) => r.images[view]).length,
      checked: scores.length,
      median,
      pass: scores.filter((q) => q.overall_status === "Pass").length,
      warning: scores.filter((q) => q.overall_status === "Warning").length,
      retake: scores.filter((q) => q.overall_status === "Retake Recommended").length,
      markers: records.filter((r) => r.images[view]?.marker_detected).length,
    };
  });

  const providers = new Map<string, { ok: number; failed: number; unavailable: number }>();
  let calibrated = 0;
  let viewRuns = 0;
  for (const r of analyzed) {
    for (const result of Object.values(r.analysis!.views)) {
      if (!result) continue;
      viewRuns += 1;
      if (result.calibration.status === "available") calibrated += 1;
      for (const ocr of result.ocr) {
        const key = ocr.provider.startsWith("xiaomi_detail") ? "xiaomi_detail" : ocr.provider;
        const row = providers.get(key) ?? { ok: 0, failed: 0, unavailable: 0 };
        row[ocr.status] += 1;
        providers.set(key, row);
      }
    }
  }
  const jevRan = analyzed.filter((r) => r.analysis!.decision.status === "ok").length;

  const categories = (Object.keys(CATEGORY_LABEL) as ProductCategory[]).map((key) => ({
    key,
    total: records.filter((r) => r.productCategory === key).length,
    analyzed: analyzed.filter((r) => r.productCategory === key).length,
  }));

  return { analyzed, fields, optics, providers: [...providers.entries()], calibrated, viewRuns, jevRan, categories };
}

function Legend({ items }: { items: [string, string][] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
      {items.map(([label, color]) => (
        <li key={label} className="inline-flex items-center gap-1.5">
          <span className={`size-2.5 rounded-sm ${color}`} aria-hidden="true" />
          {label}
        </li>
      ))}
    </ul>
  );
}

export default function AnalyticsPage() {
  const { records, error, reload } = useInspections();
  const data = useMemo(() => (records ? summarize(records) : null), [records]);

  return (
    <div className="page-stack">
      <TopBarContent
        title="Analytics"
        lede="Counts computed in the browser from the inspections stored on the API. Repeated test runs of the same package are counted separately. None of these figures is a compliance rate."
      />

      {error && <LoadError error={error} onRetry={reload} />}
      {!error && !records && <Loading label="Loading inspections from the API" />}

      {records && data && records.length === 0 && <EmptyState title="Nothing to count yet">Analytics fill in once inspections are stored.</EmptyState>}

      {records && data && records.length > 0 && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
            {[
              ["Inspections", records.length, "Stored on the API"],
              ["Analyzed", data.analyzed.length, "OCR and extraction run"],
              ["Photos awaiting analysis", records.filter((r) => progressOf(r) === "awaiting").length, "Captured, not yet read"],
              ["Jev ranking used", data.jevRan, `Of ${data.analyzed.length} analyses`],
            ].map(([label, value, detail]) => (
              <div key={label as string} className="rounded-xl border border-rule bg-sheet px-5 py-4">
                <span className="block text-sm font-medium text-ink-2">{label}</span>
                <span className="tabular mt-1 block text-xl font-semibold text-ink">{value}</span>
                <span className="mt-0.5 block text-xs text-ink-3">{detail}</span>
              </div>
            ))}
          </div>

          <Card
            title={`Declaration readings across ${data.analyzed.length} analyzed inspection${data.analyzed.length === 1 ? "" : "s"}`}
            aside={<Legend items={[["Read", "bg-accent"], ["Conflicting", "bg-amber-500"], ["Not found", "bg-slate-300"]]} />}
          >
            {data.analyzed.length === 0 ? (
              <p className="text-sm text-ink-3">No analyzed inspections yet.</p>
            ) : (
              <>
                <ul className="space-y-3">
                  {data.fields.map((f) => (
                    <li key={f.field} className="grid gap-1.5 sm:grid-cols-[10rem_minmax(0,1fr)_12rem] sm:items-center sm:gap-4">
                      <span className="text-sm text-ink">{fieldLabel(f.field)}</span>
                      <span className="flex h-2.5 overflow-hidden rounded-full bg-slate-100" role="img" aria-label={`${f.observed} read, ${f.conflict} conflicting, ${f.missing} not found`}>
                        {f.total > 0 && (
                          <>
                            <span className="bg-accent" style={{ width: `${(f.observed / f.total) * 100}%` }} />
                            <span className="bg-amber-500" style={{ width: `${(f.conflict / f.total) * 100}%` }} />
                            <span className="bg-slate-300" style={{ width: `${(f.missing / f.total) * 100}%` }} />
                          </>
                        )}
                      </span>
                      <span className="tabular text-xs text-ink-2 sm:text-right">
                        {f.observed} read · {f.conflict} conflict · {f.missing} none
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="mt-4 text-xs text-ink-3">&ldquo;Not found&rdquo; means OCR returned no matching text on the captured panels. It is not proof the declaration is absent from the package.</p>
              </>
            )}
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Photo optics by panel" bodyClass="">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-rule bg-ground/70 text-xs text-ink-3">
                    <tr>
                      <th scope="col" className="px-5 py-2.5 font-medium">Panel</th>
                      <th scope="col" className="px-3 py-2.5 text-right font-medium">Photos</th>
                      <th scope="col" className="px-3 py-2.5 text-right font-medium">Median score</th>
                      <th scope="col" className="px-3 py-2.5 text-right font-medium">Pass / warn / retake</th>
                      <th scope="col" className="px-5 py-2.5 text-right font-medium">Marker found</th>
                    </tr>
                  </thead>
                  <tbody className="tabular divide-y divide-rule">
                    {data.optics.map((o) => (
                      <tr key={o.view}>
                        <td className="px-5 py-2.5 font-medium text-ink">{VIEW_LABEL[o.view]}</td>
                        <td className="px-3 py-2.5 text-right text-ink-2">{o.photos}</td>
                        <td className="px-3 py-2.5 text-right text-ink">{o.median ?? "—"}</td>
                        <td className="px-3 py-2.5 text-right text-ink-2">
                          {o.pass} / {o.warning} / {o.retake}
                        </td>
                        <td className="px-5 py-2.5 text-right text-ink-2">{o.markers}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="border-t border-rule px-5 py-3 text-xs text-ink-3">
                The optical score (0–100) rates sharpness, exposure, contrast, glare and resolution of the original photo. It is not OCR accuracy and says nothing about compliance.
              </p>
            </Card>

            <Card title="OCR runs and calibration" bodyClass="">
              <ul className="divide-y divide-rule text-sm">
                {data.providers.length === 0 && <li className="px-5 py-3 text-ink-3">No OCR runs recorded yet.</li>}
                {data.providers.map(([provider, row]) => {
                  const total = row.ok + row.failed + row.unavailable;
                  return (
                    <li key={provider} className="space-y-1.5 px-5 py-3">
                      <span className="flex items-baseline justify-between gap-3">
                        <span className="font-medium text-ink">{provider === "xiaomi_detail" ? "Xiaomi-OCR detail scans" : providerLabel(provider)}</span>
                        <span className="tabular text-xs text-ink-2">
                          {row.ok} ok{row.failed ? ` · ${row.failed} failed` : ""}
                          {row.unavailable ? ` · ${row.unavailable} unavailable` : ""}
                        </span>
                      </span>
                      <Meter value={row.ok} max={total} />
                    </li>
                  );
                })}
                <li className="space-y-1.5 px-5 py-3">
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="font-medium text-ink">Physical scale available</span>
                    <span className="tabular text-xs text-ink-2">
                      {data.calibrated} of {data.viewRuns} analyzed panels
                    </span>
                  </span>
                  <Meter value={data.calibrated} max={data.viewRuns} tone="neutral" />
                </li>
              </ul>
              <p className="border-t border-rule px-5 py-3 text-xs text-ink-3">
                Xiaomi-OCR is the primary reading. Tesseract supplies line positions only where its text matches. Scale needs a detected marker confirmed flat in the label plane.
              </p>
            </Card>
          </div>

          <Card title="Inspections by category" bodyClass="">
            <ul className="divide-y divide-rule text-sm">
              {data.categories.map((c) => (
                <li key={c.key} className="grid gap-1.5 px-5 py-3 sm:grid-cols-[12rem_minmax(0,1fr)_9rem] sm:items-center sm:gap-4">
                  <span className="text-ink">{CATEGORY_LABEL[c.key]}</span>
                  <Meter value={c.total} max={records.length} tone={c.total ? "accent" : "neutral"} />
                  <span className="tabular text-xs text-ink-2 sm:text-right">
                    {c.total} stored · {c.analyzed} analyzed
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}
