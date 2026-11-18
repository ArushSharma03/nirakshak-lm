"use client";

import { TopBarContent } from "@/components/layout/TopBarContent";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CategoryTag, InspectionTable, LoadError, ProgressBadge, nextAction, progressOf, useInspections, type Progress } from "@/components/InspectionLedger";
import { Badge, ButtonLink, Card, EmptyState, Field, Icon, Loading, buttonClass, inputClass, qualityTone } from "@/components/ui";
import { CATEGORY_LABEL, VIEWS, VIEW_LABEL, fieldLabel, formatDate, hasSetupNotes, storageLabel } from "@/lib/format";
import type { InspectionRecord, ProductCategory } from "@/types";

const FILTERS: { id: "all" | Progress; label: string }[] = [
  { id: "all", label: "All" },
  { id: "analyzed", label: "Analyzed" },
  { id: "awaiting", label: "Awaiting analysis" },
  { id: "empty", label: "No photos" },
];

function QuickLook({ record, onClose }: { record: InspectionRecord; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const action = nextAction(record);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const fields = record.analysis?.fields ?? [];
  const read = fields.filter((f) => f.status === "observed").length;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-labelledby="quick-look-title">
      <button type="button" aria-label="Close" onClick={onClose} className="absolute inset-0 bg-slate-900/40" />
      <div className="relative flex h-full w-full max-w-md flex-col bg-sheet shadow-[-8px_0_24px_rgb(15_23_42/0.12)]">
        <div className="flex items-start justify-between gap-3 border-b border-rule px-5 py-4">
          <div className="min-w-0">
            <p className="serial text-xs text-ink-3">{record.id}</p>
            <h2 id="quick-look-title" className="text-lg font-semibold text-ink">{record.productName}</h2>
            <p className="text-xs text-ink-3">{formatDate(record.timestamp, true)} · {storageLabel(record)}</p>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} aria-label="Close quick look" className="grid size-9 shrink-0 place-items-center rounded-md text-ink-2 hover:bg-ground">
            <Icon name="close" />
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
          <div className="flex flex-wrap items-center gap-2">
            <ProgressBadge record={record} full />
            <CategoryTag category={record.productCategory} />
          </div>

          <div className="grid grid-cols-3 gap-2">
            {VIEWS.map((view) => {
              const img = record.images[view];
              const quality = img?.quality_assessment;
              return (
                <figure key={view} className="overflow-hidden rounded-lg border border-rule">
                  <div className="aspect-square bg-ground">
                    {img?.previewUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={img.previewUrl} alt={`${VIEW_LABEL[view]} panel`} className="size-full object-contain" />
                    ) : (
                      <span className="grid size-full place-items-center text-xs text-ink-3">No photo</span>
                    )}
                  </div>
                  <figcaption className="flex items-center justify-between gap-1 px-2 py-1.5 text-xs">
                    <span className="font-medium text-ink">{VIEW_LABEL[view]}</span>
                    {quality && <Badge tone={qualityTone(quality.overall_status)}>{quality.composite_score}</Badge>}
                  </figcaption>
                </figure>
              );
            })}
          </div>
          <p className="text-xs text-ink-3">Numbers are optical scores of the original photo (0–100). They are not OCR accuracy or compliance.</p>

          {record.analysis && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-ink">Declarations read: {read} of {fields.length}</h3>
              <ul className="divide-y divide-rule rounded-lg border border-rule text-sm">
                {record.labelBrand && (
                  <li className="flex items-baseline justify-between gap-3 px-3 py-2">
                    <span className="shrink-0 text-ink-2">Brand</span>
                    <span className="truncate text-right font-medium text-ink">{record.labelBrand}</span>
                  </li>
                )}
                {fields.map((field) => (
                  <li key={field.field} className="flex items-baseline justify-between gap-3 px-3 py-2">
                    <span className="shrink-0 text-ink-2">{fieldLabel(field.field)}</span>
                    <span className={`truncate text-right ${field.value ? "font-medium text-ink" : "text-ink-3"}`}>
                      {field.status === "conflict" ? "Conflicting" : field.value ?? "Not found"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {hasSetupNotes(record) && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-ink">Setup notes</h3>
              <p className="text-xs text-ink-3">Typed at setup, unverified and not read from the label. Older records may hold server placeholders.</p>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Photo source">{record.notes || "Blank"}</Field>
                <Field label="Brand">{record.brand || "Blank"}</Field>
                <Field label="Net quantity">{record.declaredNetQty || "Blank"}</Field>
                <Field label="MRP">{record.declaredMRP !== null ? `₹${record.declaredMRP.toFixed(2)}` : "Blank"}</Field>
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-2 border-t border-rule px-5 py-4">
          <ButtonLink href={action.href}>
            {action.label}
            <Icon name="arrowRight" />
          </ButtonLink>
          {record.analysis && (
            <Link href={`/inspect?id=${encodeURIComponent(record.id)}`} className={buttonClass.secondary}>
              Photos and re-run
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

function History() {
  const router = useRouter();
  const params = useSearchParams();
  const urlFilter = params.get("filter");
  const filter = (FILTERS.some((f) => f.id === urlFilter) ? urlFilter : "all") as (typeof FILTERS)[number]["id"];
  const { records, error, reload } = useInspections();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<"all" | ProductCategory>("all");
  const [open, setOpen] = useState<InspectionRecord | null>(null);
  const close = useCallback(() => setOpen(null), []);

  const setFilter = (id: string) => router.replace(id === "all" ? "/inspections" : `/inspections?filter=${id}`, { scroll: false });

  const visible = useMemo(() => {
    if (!records) return [];
    const needle = query.trim().toLowerCase();
    return records.filter(
      (r) =>
        (filter === "all" || progressOf(r) === filter) &&
        (category === "all" || r.productCategory === category) &&
        (!needle || r.id.toLowerCase().includes(needle) || r.productName.toLowerCase().includes(needle) || r.notes.toLowerCase().includes(needle)),
    );
  }, [records, query, filter, category]);

  return (
    <div className="page-stack">
      <TopBarContent
        title="Inspection history"
        lede="Every inspection stored on the API. Analyzed records open as reports; the rest continue in guided capture."
        actions={
          <ButtonLink href="/inspections/new">
            <Icon name="plus" />
            New inspection
          </ButtonLink>
        }
      />

      {error && <LoadError error={error} onRetry={reload} />}
      {!error && records === null && <Loading label="Loading inspections from the API" />}

      {records && (
        <Card bodyClass="">
          <div className="flex flex-col gap-3 border-b border-rule p-4 lg:flex-row lg:items-center lg:justify-between">
            <div role="group" aria-label="Filter by progress" className="flex flex-wrap gap-1">
              {FILTERS.map((f) => {
                const count = f.id === "all" ? records.length : records.filter((r) => progressOf(r) === f.id).length;
                const active = filter === f.id;
                return (
                  <button
                    key={f.id}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setFilter(f.id)}
                    className={`min-h-9 rounded-lg px-3 text-sm font-medium transition-colors ${active ? "bg-rail text-white" : "text-ink-2 hover:bg-slate-100 hover:text-ink"}`}
                  >
                    {f.label} <span className={`tabular ml-0.5 ${active ? "text-slate-300" : "text-ink-3"}`}>{count}</span>
                  </button>
                );
              })}
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <label className="block sm:w-48">
                <span className="sr-only">Category</span>
                <select value={category} onChange={(e) => setCategory(e.target.value as typeof category)} className={`${inputClass} mt-0`}>
                  <option value="all">All categories</option>
                  {Object.entries(CATEGORY_LABEL).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="relative block sm:w-64">
                <span className="sr-only">Search inspections</span>
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3">
                  <Icon name="search" />
                </span>
                <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="ID, package or photo source" className={`${inputClass} mt-0 pl-9`} />
              </label>
            </div>
          </div>

          {visible.length > 0 ? (
            <InspectionTable records={visible} onQuickLook={setOpen} />
          ) : (
            <div className="p-4">
              <EmptyState title={records.length === 0 ? "No inspections yet" : "Nothing matches"}>
                {records.length === 0 ? "Start one to photograph a package." : "Clear the search or pick another filter."}
              </EmptyState>
            </div>
          )}
        </Card>
      )}

      {open && <QuickLook record={open} onClose={close} />}
    </div>
  );
}

export default function InspectionsPage() {
  return (
    <Suspense fallback={<Loading label="Loading inspections" />}>
      <History />
    </Suspense>
  );
}
