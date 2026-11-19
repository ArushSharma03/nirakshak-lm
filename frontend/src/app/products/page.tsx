"use client";

import { TopBarContent } from "@/components/layout/TopBarContent";

import Link from "next/link";
import { useMemo, useState } from "react";
import { CategoryTag, LoadError, ProgressBadge, nextAction, progressOf, useInspections } from "@/components/InspectionLedger";
import { ButtonLink, EmptyState, Icon, Loading, inputClass } from "@/components/ui";
import { formatDate } from "@/lib/format";
import type { InspectionRecord } from "@/types";

interface Product {
  key: string;
  name: string;
  records: InspectionRecord[];
}

export default function ProductsPage() {
  const { records, error, reload } = useInspections();
  const [query, setQuery] = useState("");

  const products = useMemo<Product[]>(() => {
    if (!records) return [];
    const groups = new Map<string, Product>();
    for (const record of records) {
      const key = `${record.productCategory}|${record.productName.trim().toLowerCase()}`;
      const group = groups.get(key) ?? { key, name: record.productName, records: [] };
      group.records.push(record);
      groups.set(key, group);
    }
    return [...groups.values()];
  }, [records]);

  const needle = query.trim().toLowerCase();
  const visible = products.filter((p) => !needle || p.name.toLowerCase().includes(needle) || p.records.some((r) => r.id.toLowerCase().includes(needle)));

  return (
    <div className="page-stack">
      <TopBarContent
        title="Product catalog"
        lede="Packages you have inspected, grouped by the name read from the label (or typed on older records). Built from the inspections stored on the API; it is not a product registry."
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
        <>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-ink-2">
              <span className="tabular font-semibold text-ink">{products.length}</span> package name{products.length === 1 ? "" : "s"} across{" "}
              <span className="tabular font-semibold text-ink">{records.length}</span> inspections
            </p>
            <label className="relative block sm:w-72">
              <span className="sr-only">Search packages</span>
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3">
                <Icon name="search" />
              </span>
              <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Package name or inspection ID" className={`${inputClass} mt-0 pl-9`} />
            </label>
          </div>

          {visible.length === 0 ? (
            <EmptyState title={records.length === 0 ? "No packages yet" : "Nothing matches"}>
              {records.length === 0 ? "Packages appear here once you set up an inspection." : "Try another name or clear the search."}
            </EmptyState>
          ) : (
            <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {visible.map((product) => {
                const latest = product.records[0];
                const analyzed = product.records.filter((r) => progressOf(r) === "analyzed").length;
                const thumb = ["front", "rear", "side"].map((v) => latest.images[v]?.previewUrl).find(Boolean);
                const action = nextAction(latest);
                return (
                  <li key={product.key} className="flex flex-col overflow-hidden rounded-xl border border-rule bg-sheet shadow-[0_1px_2px_rgb(15_23_42/0.04)]">
                    <div className="flex gap-4 p-4">
                      <div className="size-20 shrink-0 overflow-hidden rounded-lg border border-rule bg-ground">
                        {thumb ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={thumb} alt="" className="size-full object-cover" />
                        ) : (
                          <span className="grid size-full place-items-center text-ink-3">
                            <Icon name="box" className="size-6" />
                          </span>
                        )}
                      </div>
                      <div className="min-w-0 space-y-1.5">
                        <h2 className="font-semibold leading-snug text-ink">{product.name}</h2>
                        <CategoryTag category={latest.productCategory} />
                        <p className="text-xs text-ink-3">
                          {product.records.length} inspection{product.records.length === 1 ? "" : "s"}, {analyzed} analyzed
                        </p>
                      </div>
                    </div>
                    <div className="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-rule bg-ground/60 px-4 py-3">
                      <span className="min-w-0 space-y-1">
                        <span className="block text-xs text-ink-3">
                          Latest <span className="serial">{latest.id}</span>, {formatDate(latest.timestamp)}
                        </span>
                        <ProgressBadge record={latest} />
                      </span>
                      <Link href={action.href} className="inline-flex min-h-9 items-center gap-1 rounded-md bg-sheet px-3 text-xs font-semibold text-ink ring-1 ring-rule hover:bg-slate-100">
                        {action.label}
                        <Icon name="arrowRight" className="size-3" />
                      </Link>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
