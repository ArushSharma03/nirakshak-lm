"use client";

import { TopBarContent } from "@/components/layout/TopBarContent";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type { ProductCategory } from "@/types";
import { createInspection } from "@/lib/api";
import { CATEGORY_LABEL, errorText } from "@/lib/format";
import { Icon, Notice, buttonClass, inputClass } from "@/components/ui";

export default function NewInspectionPage() {
  const router = useRouter();
  const [productName, setProductName] = useState("");
  const [category, setCategory] = useState<ProductCategory>("food_grocery");
  const [notes, setNotes] = useState("");
  const [brand, setBrand] = useState("");
  const [declaredNetQty, setDeclaredNetQty] = useState("");
  const [declaredMRP, setDeclaredMRP] = useState("");
  const [location, setLocation] = useState("");
  const [inspectorName, setInspectorName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const mrp = declaredMRP.trim() ? Number(declaredMRP) : null;
      const record = await createInspection({
        productName,
        productCategory: category,
        notes,
        brand,
        declaredNetQty,
        declaredMRP: mrp !== null && Number.isFinite(mrp) ? mrp : null,
        location,
        inspectorName,
      });
      router.push(`/inspect?id=${encodeURIComponent(record.id)}`);
    } catch (cause) {
      setError(errorText(cause, "Could not create the inspection."));
      setSubmitting(false);
    }
  }

  return (
    <div className="page-stack">
            <TopBarContent
        title="New inspection"
        lede="Name the package so you can find it later. Nothing typed here counts as label evidence; declarations are read from the photos."
      />

      <form onSubmit={handleSubmit} className="overflow-hidden rounded-xl border border-rule bg-sheet shadow-[0_1px_2px_rgb(15_23_42/0.04)]">
        <fieldset className="grid gap-5 p-5 sm:grid-cols-2">
          <legend className="float-left mb-1 w-full text-sm font-semibold text-ink">Package</legend>
          <label className="block text-sm font-medium sm:col-span-2">
            Package name
            <input required value={productName} onChange={(e) => setProductName(e.target.value)} placeholder="e.g. Parle-G biscuits 70 g, shelf sample 2" className={inputClass} />
          </label>
          <label className="block text-sm font-medium">
            Category
            <select value={category} onChange={(e) => setCategory(e.target.value as ProductCategory)} className={inputClass}>
              {Object.entries(CATEGORY_LABEL).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-xs font-normal text-ink-3">Picks the rule profile. Only food and grocery has rule data so far.</span>
          </label>
          <label className="block text-sm font-medium">
            Photo source
            <input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. Shelf photos, phone camera" className={inputClass} />
            <span className="mt-1 block text-xs font-normal text-ink-3">Shown on the report as provenance. Say if images are catalog or web copies.</span>
          </label>
        </fieldset>

        <hr className="border-rule" />

        <fieldset className="grid gap-5 p-5 sm:grid-cols-2">
          <legend className="float-left mb-1 w-full text-sm">
            <span className="font-semibold text-ink">Optional setup notes</span>
            <span className="block text-ink-3">
              For your reference only. Leave anything you have not checked blank. These values are separate from photo evidence.
            </span>
          </legend>
          <label className="block text-sm font-medium">
            Brand or manufacturer
            <input value={brand} onChange={(e) => setBrand(e.target.value)} className={inputClass} />
          </label>
          <label className="block text-sm font-medium">
            Net quantity on the pack
            <input value={declaredNetQty} onChange={(e) => setDeclaredNetQty(e.target.value)} placeholder="e.g. 70 g" className={inputClass} />
          </label>
          <label className="block text-sm font-medium">
            MRP on the pack (₹)
            <input type="number" inputMode="decimal" step="0.01" min="0" value={declaredMRP} onChange={(e) => setDeclaredMRP(e.target.value)} className={inputClass} />
          </label>
          <label className="block text-sm font-medium">
            Location
            <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Store, shelf or lab desk" className={inputClass} />
          </label>
          <label className="block text-sm font-medium sm:col-span-2">
            Inspector
            <input value={inspectorName} onChange={(e) => setInspectorName(e.target.value)} className={inputClass} />
          </label>
        </fieldset>

        <div className="flex flex-col gap-3 border-t border-rule bg-ground/50 p-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-ink-2">Next: photograph the front, rear and side panels.</p>
          <button type="submit" disabled={submitting} className={buttonClass.primary}>
            {submitting ? "Creating…" : "Create and start photos"}
            {!submitting && <Icon name="arrowRight" />}
          </button>
        </div>
      </form>

      {error && (
        <div>
          <Notice tone="danger" title="The inspection was not created">
            {error} Nothing was saved. Check that the API is online and try again.
          </Notice>
        </div>
      )}
    </div>
  );
}
