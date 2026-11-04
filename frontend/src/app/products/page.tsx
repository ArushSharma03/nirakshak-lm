"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { getProducts } from "@/lib/api";
import { ProductRecord } from "@/types";
import CategoryBadge from "@/components/common/CategoryBadge";
import LegalDisclaimer from "@/components/common/LegalDisclaimer";

export default function ProductsPage() {
  const [products, setProducts] = useState<ProductRecord[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    async function load() {
      const data = await getProducts();
      setProducts(data);
    }
    load();
  }, []);

  const filtered = products.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.brand.toLowerCase().includes(search.toLowerCase()) ||
      p.sampleBarcode.includes(search)
  );

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Packaged Product & Commodity Catalog
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Registered baseline commodities across the four approved Legal Metrology categories.
          </p>
        </div>

        <Link
          href="/inspections/new"
          className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg text-xs transition-colors shadow-xs"
        >
          <span>Register New Commodity</span>
        </Link>
      </div>

      <LegalDisclaimer compact />

      {/* Search Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
        <div className="relative">
          <svg className="w-4 h-4 text-slate-400 absolute left-3 top-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search catalog by commodity name, manufacturer, or barcode (e.g. Britannia, Amul, 8901)..."
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs sm:text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20"
          />
        </div>
      </div>

      {/* Product Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map((item) => (
          <div
            key={item.id}
            className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-all"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <CategoryBadge category={item.category} />
                <span className="font-mono text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                  {item.sampleBarcode}
                </span>
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-900 leading-snug">
                  {item.name}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5 font-medium">{item.brand}</p>
              </div>

              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Declared Net Qty:</span>
                  <span className="font-semibold text-slate-800">{item.declaredNetQty}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Packaging Size:</span>
                  <span className="text-slate-700">{item.dimensions}</span>
                </div>
                <div className="flex justify-between pt-1 border-t border-slate-200/60">
                  <span className="text-slate-500">Standards Ref:</span>
                  <span className="text-[11px] text-teal-800 font-mono">{item.verifiedStandard.split("/")[0]}</span>
                </div>
              </div>
            </div>

            <div className="pt-4 mt-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-[11px] text-slate-500 font-medium">
                {item.activeInspectionsCount} screenings recorded
              </span>
              <Link
                href="/inspections/new"
                className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-teal-300 text-xs font-semibold rounded-md transition-colors"
              >
                Inspect Now &rarr;
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
