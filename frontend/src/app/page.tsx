"use client";

import { TopBarContent } from "@/components/layout/TopBarContent";

import Link from "next/link";
import { useEffect, useState } from "react";
import { InspectionTable, LoadError, progressOf, useInspections } from "@/components/InspectionLedger";
import { Card, EmptyState, Icon, Loading, Meter } from "@/components/ui";
import { getRuleSet, type RuleSet } from "@/lib/analysis";
import { CATEGORY_LABEL, errorText, fieldLabel } from "@/lib/format";
import type { ProductCategory } from "@/types";

function useRuleSet() {
  const [ruleSet, setRuleSet] = useState<RuleSet | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    getRuleSet()
      .then((data) => alive && setRuleSet(data))
      .catch((cause) => alive && setError(errorText(cause, "Rule data unavailable.")));
    return () => {
      alive = false;
    };
  }, []);
  return { ruleSet, error };
}

function Stat({ label, value, detail, href }: { label: string; value: number | null; detail: string; href: string }) {
  return (
    <Link href={href} className="group rounded-md border border-rule bg-sheet px-5 py-4 transition-colors hover:border-rule-strong">
      <span className="flex items-center justify-between text-sm font-medium text-ink-2">
        {label}
        <Icon name="arrowRight" className="size-3.5 text-ink-3 opacity-0 transition-opacity group-hover:opacity-100" />
      </span>
      <span className="tabular mt-1 block text-xl font-semibold text-ink">{value ?? "—"}</span>
      <span className="mt-0.5 block text-xs text-ink-3">{detail}</span>
    </Link>
  );
}

export default function DashboardPage() {
  const { records, error, reload } = useInspections();
  const { ruleSet, error: ruleError } = useRuleSet();

  const count = (test: (p: ReturnType<typeof progressOf>) => boolean) => (records ? records.filter((r) => test(progressOf(r))).length : null);
  const categories = records
    ? (Object.keys(CATEGORY_LABEL) as ProductCategory[]).map((key) => ({ key, n: records.filter((r) => r.productCategory === key).length }))
    : [];
  const maxCategory = Math.max(1, ...categories.map((c) => c.n));

  return (
    <div className="page-stack">
      <TopBarContent
        title="Package inspections"
        lede="Capture package labels and review the extracted declarations against their source photos."
        actions={<>
          <Link href="/inspections/new" className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-white hover:bg-accent-deep"><Icon name="camera" />Start an inspection</Link>
          <Link href="/inspect" className="inline-flex min-h-10 items-center rounded-lg border border-rule-strong bg-sheet px-4 text-sm font-semibold text-ink hover:bg-ground">Continue capture</Link>
        </>}
      />

      {error && <LoadError error={error} onRetry={reload} />}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <Stat label="Inspections stored" value={records?.length ?? null} detail="On the API, newest first" href="/inspections" />
        <Stat label="Analyzed" value={count((p) => p === "analyzed")} detail="Each one awaits your review" href="/inspections?filter=analyzed" />
        <Stat label="Awaiting analysis" value={count((p) => p === "awaiting")} detail="Photos stored, not yet read" href="/inspections?filter=awaiting" />
        <Stat label="No photos yet" value={count((p) => p === "empty")} detail="Set up, nothing captured" href="/inspections?filter=empty" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card
          className="lg:col-span-2"
          bodyClass=""
          title="Recent inspections"
          aside={
            records && records.length > 0 ? (
              <Link href="/inspections" className="inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline">
                All {records.length} inspections
                <Icon name="arrowRight" className="size-3" />
              </Link>
            ) : null
          }
        >
          {!error && records === null && (
            <div className="px-5">
              <Loading label="Loading inspections from the API" />
            </div>
          )}
          {records && records.length === 0 && (
            <div className="p-5">
              <EmptyState title="No inspections yet" action={<Link href="/inspections/new" className="text-sm font-semibold text-accent hover:underline">Start the first one</Link>}>
                Set up an inspection, then photograph the package panels.
              </EmptyState>
            </div>
          )}
          {records && records.length > 0 && <InspectionTable records={records.slice(0, 6)} compact />}
          {error && <p className="px-5 py-6 text-sm text-ink-3">Unavailable while the API is offline.</p>}
        </Card>

        <div className="page-stack">
          <Card title="Inspections by category" aside={records ? <span className="text-xs text-ink-3">{records.length} total</span> : null}>
            {records ? (
              <ul className="space-y-3.5">
                {categories.map(({ key, n }) => (
                  <li key={key} className="space-y-1.5">
                    <span className="flex justify-between text-sm">
                      <span className="text-ink">{CATEGORY_LABEL[key]}</span>
                      <span className="tabular text-ink-2">{n}</span>
                    </span>
                    <Meter value={n} max={maxCategory} tone={n ? "accent" : "neutral"} />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-ink-3">{error ? "Unavailable while the API is offline." : "Loading…"}</p>
            )}
          </Card>

          <Card
            title="Declarations checked"
            aside={
              <Link href="/rules" className="inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline">
                Rules and sources
                <Icon name="arrowRight" className="size-3" />
              </Link>
            }
          >
            {ruleSet ? (
              <div className="space-y-3">
                <p className="text-xs text-ink-3">
                  Profile <span className="serial">{ruleSet.id}</span> {ruleSet.version}, {CATEGORY_LABEL[ruleSet.category as ProductCategory] ?? ruleSet.category}
                </p>
                <ul className="divide-y divide-rule text-sm">
                  {ruleSet.rules.map((rule) => (
                    <li key={rule.id} className="flex items-baseline justify-between gap-3 py-2 first:pt-0 last:pb-0">
                      <span className="text-ink">{fieldLabel(rule.field)}</span>
                      <span className="shrink-0 text-xs text-ink-3">{rule.citation}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-sm text-ink-3">{ruleError ? `Rule data unavailable: ${ruleError}` : "Loading…"}</p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
