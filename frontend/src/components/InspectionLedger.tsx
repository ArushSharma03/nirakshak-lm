"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { getInspections, ApiUnavailableError } from "@/lib/api";
import { CATEGORY_LABEL, VIEWS, VIEW_LABEL, capturedViews, errorText, formatDate } from "@/lib/format";
import type { ComplianceOutcome, InspectionRecord } from "@/types";
import { Badge, Icon, Notice, buttonClass, type Tone } from "@/components/ui";

export function useInspections() {
  const [records, setRecords] = useState<InspectionRecord[] | null>(null);
  const [error, setError] = useState<{ message: string; offline: boolean } | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const list = await getInspections();
      setRecords([...list].sort((a, b) => b.timestamp.localeCompare(a.timestamp)));
    } catch (cause) {
      setRecords(null);
      setError({ message: errorText(cause, "Could not load inspections."), offline: cause instanceof ApiUnavailableError });
    }
  }, []);

  useEffect(() => {
    // Initial fetch from the API; state is set after the request settles.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  return { records, error, reload: load };
}

export function LoadError({ error, onRetry }: { error: { message: string; offline: boolean }; onRetry: () => void }) {
  return (
    <Notice
      tone="danger"
      title={error.offline ? "The inspection API is offline" : "Inspections could not be loaded"}
      action={
        <button type="button" onClick={onRetry} className={buttonClass.secondary}>
          Try again
        </button>
      }
    >
      {error.offline ? "Start the backend on port 8000, then try again. Nothing is shown from cache or sample data." : error.message}
    </Notice>
  );
}

export type Progress = "analyzed" | "awaiting" | "empty";

export function progressOf(record: InspectionRecord): Progress {
  if (record.analysis) return "analyzed";
  return capturedViews(record).length > 0 ? "awaiting" : "empty";
}

export const OUTCOME_TONE: Record<ComplianceOutcome, Tone> = {
  "Manual Review Required": "warn",
  "Potential Non-Compliance": "danger",
  "Compliant within Implemented Checks": "ok",
};

const OUTCOME_SHORT: Record<ComplianceOutcome, string> = {
  "Manual Review Required": "Manual review",
  "Potential Non-Compliance": "Potential non-compliance",
  "Compliant within Implemented Checks": "Within implemented checks",
};

export function ProgressBadge({ record, full = false }: { record: InspectionRecord; full?: boolean }) {
  const progress = progressOf(record);
  if (progress === "analyzed")
    return (
      <span title={record.outcome}>
        <Badge tone={OUTCOME_TONE[record.outcome] ?? "warn"}>{full ? record.outcome : OUTCOME_SHORT[record.outcome] ?? record.outcome}</Badge>
      </span>
    );
  if (progress === "awaiting") return <Badge tone="accent">Awaiting analysis</Badge>;
  return <Badge tone="neutral">No photos yet</Badge>;
}

export function CategoryTag({ category }: { category: InspectionRecord["productCategory"] }) {
  return <span className="inline-flex whitespace-nowrap rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-ink-2">{CATEGORY_LABEL[category] ?? category}</span>;
}

export function nextAction(record: InspectionRecord): { href: string; label: string } {
  if (record.analysis) return { href: `/reports?id=${encodeURIComponent(record.id)}`, label: "Open report" };
  if (capturedViews(record).length > 0) return { href: `/inspect?id=${encodeURIComponent(record.id)}`, label: "Analyze" };
  return { href: `/inspect?id=${encodeURIComponent(record.id)}`, label: "Add photos" };
}

export function ViewMarks({ record }: { record: InspectionRecord }) {
  const captured = capturedViews(record);
  return (
    <span className="inline-flex gap-1" aria-label={captured.length ? `Photos: ${captured.join(", ")}` : "No photos"}>
      {VIEWS.map((view) => {
        const has = captured.includes(view);
        return (
          <span
            key={view}
            title={`${VIEW_LABEL[view]} ${has ? "captured" : "missing"}`}
            className={`grid size-6 place-items-center rounded-md border text-[0.7rem] font-semibold ${
              has ? "border-teal-200 bg-accent-wash text-accent" : "border-rule text-slate-300"
            }`}
          >
            {VIEW_LABEL[view][0]}
          </span>
        );
      })}
    </span>
  );
}

function MarkerCell({ record }: { record: InspectionRecord }) {
  if (!record.markerDetected) return <span className="text-xs text-ink-3">No marker</span>;
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-ok">
      <Icon name="check" className="size-3.5" />
      {record.scalePpm ? <span className="tabular">{record.scalePpm} px/mm</span> : "Marker found"}
    </span>
  );
}

/** The inspection table used by the dashboard and history. Rows become stacked cards on phones. */
export function InspectionTable({ records, compact = false, onQuickLook }: { records: InspectionRecord[]; compact?: boolean; onQuickLook?: (record: InspectionRecord) => void }) {
  return (
    <div>
      <div className="hidden overflow-x-auto md:block">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-rule bg-ground/70 text-xs text-ink-3">
          <tr>
            <th scope="col" className="px-5 py-2.5 font-medium">Inspection</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Package</th>
            {!compact && <th scope="col" className="hidden px-3 py-2.5 font-medium lg:table-cell">Category</th>}
            {!compact && <th scope="col" className="hidden px-3 py-2.5 font-medium xl:table-cell">Scale</th>}
            <th scope="col" className="px-3 py-2.5 font-medium">Photos</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Status</th>
            <th scope="col" className="px-5 py-2.5 text-right font-medium">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {records.map((record) => {
            const action = nextAction(record);
            return (
              <tr key={record.id} className="transition-colors hover:bg-ground/70">
                <td className="whitespace-nowrap px-5 py-3 align-middle">
                  <span className="serial block text-[0.8rem] text-ink">{record.id}</span>
                  <span className="block text-xs text-ink-3">{formatDate(record.timestamp, true)}</span>
                </td>
                <td className="max-w-[15rem] px-3 py-3 align-middle">
                  <span className="block truncate font-medium text-ink">{record.productName}</span>
                  {record.notes && <span className="block truncate text-xs text-ink-3">{record.notes}</span>}
                </td>
                {!compact && (
                  <td className="hidden px-3 py-3 align-middle lg:table-cell">
                    <CategoryTag category={record.productCategory} />
                  </td>
                )}
                {!compact && (
                  <td className="hidden whitespace-nowrap px-3 py-3 align-middle xl:table-cell">
                    <MarkerCell record={record} />
                  </td>
                )}
                <td className="px-3 py-3 align-middle">
                  <ViewMarks record={record} />
                </td>
                <td className="px-3 py-3 align-middle">
                  <ProgressBadge record={record} />
                </td>
                <td className="whitespace-nowrap py-3 pl-3 pr-5 text-right align-middle">
                  <span className="inline-flex items-center gap-1">
                    {onQuickLook && (
                      <button type="button" onClick={() => onQuickLook(record)} className="min-h-8 whitespace-nowrap rounded-md px-2 text-xs font-medium text-ink-2 hover:bg-slate-100 hover:text-ink">
                        Quick look
                      </button>
                    )}
                    <Link href={action.href} className="inline-flex min-h-8 items-center gap-1 rounded-md bg-slate-100 px-2.5 text-xs font-semibold text-ink hover:bg-slate-200">
                      {action.label}
                      <Icon name="arrowRight" className="size-3" />
                    </Link>
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>

      <ul className="divide-y divide-rule md:hidden">
        {records.map((record) => {
          const action = nextAction(record);
          return (
            <li key={record.id} className="space-y-2.5 px-4 py-3.5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-medium text-ink">{record.productName}</p>
                  <p className="text-xs text-ink-3">
                    <span className="serial">{record.id}</span> · {formatDate(record.timestamp)}
                  </p>
                </div>
                <ViewMarks record={record} />
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <ProgressBadge record={record} />
                <span className="flex items-center gap-1">
                  {onQuickLook && (
                    <button type="button" onClick={() => onQuickLook(record)} className="min-h-9 rounded-md px-2.5 text-xs font-medium text-ink-2 hover:bg-slate-100">
                      Quick look
                    </button>
                  )}
                  <Link href={action.href} className="inline-flex min-h-9 items-center gap-1 rounded-md bg-slate-100 px-3 text-xs font-semibold text-ink hover:bg-slate-200">
                    {action.label}
                    <Icon name="arrowRight" className="size-3" />
                  </Link>
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
