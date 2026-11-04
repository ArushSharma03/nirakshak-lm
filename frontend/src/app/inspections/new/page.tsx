"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ProductCategory } from "@/types";
import { createInspection } from "@/lib/api";
import LegalDisclaimer from "@/components/common/LegalDisclaimer";

export default function NewInspectionPage() {
  const router = useRouter();
  const [productName, setProductName] = useState("");
  const [category, setCategory] = useState<ProductCategory>("food_grocery");
  const [brand, setBrand] = useState("");
  const [declaredNetQty, setDeclaredNetQty] = useState("");
  const [declaredMRP, setDeclaredMRP] = useState("");
  const [location, setLocation] = useState("Retail Store — Sample Bay 1");
  const [inspectorName, setInspectorName] = useState("Mr. Arush Sharma");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleQuickFill = (name: string, cat: ProductCategory, b: string, qty: string, mrp: string) => {
    setProductName(name);
    setCategory(cat);
    setBrand(b);
    setDeclaredNetQty(qty);
    setDeclaredMRP(mrp);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const record = await createInspection({
        productName: productName || "Generic Commodity Sample",
        productCategory: category,
        brand: brand || "Unspecified Brand",
        declaredNetQty: declaredNetQty || "100 g",
        declaredMRP: parseFloat(declaredMRP) || 50.0,
        location: location || "Retail Store — Sample Bay 1",
        inspectorName: inspectorName || "Mr. Arush Sharma",
      });

      // Navigate to guided capture flow with inspection ID
      router.push(`/inspect?id=${encodeURIComponent(record.id)}`);
    } catch (err) {
      console.error("Failed to initialize inspection:", err);
      router.push("/inspect");
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            New Inspection Setup
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Register commodity profile details before initiating multi-view camera capture.
          </p>
        </div>
        <Link
          href="/inspections"
          className="inline-flex items-center text-xs font-medium text-slate-600 hover:text-slate-900"
        >
          &larr; Back to History
        </Link>
      </div>

      <LegalDisclaimer compact />

      {/* Quick Fill Preset Pills */}
      <div className="bg-slate-100/80 border border-slate-200 rounded-xl p-4">
        <span className="text-xs font-semibold text-slate-700 block mb-2">
          Quick-Fill Sample Commodity Preset:
        </span>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => handleQuickFill("Britannia NutriChoice Digestive 100g", "food_grocery", "Britannia Industries Ltd.", "100 g", "25")}
            className="text-xs px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-md font-medium transition-colors"
          >
            Britannia Digestive (100g)
          </button>
          <button
            type="button"
            onClick={() => handleQuickFill("Amul Pasteurized Butter 500g", "food_grocery", "GCMMF (Amul)", "500 g", "285")}
            className="text-xs px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-md font-medium transition-colors"
          >
            Amul Butter (500g)
          </button>
          <button
            type="button"
            onClick={() => handleQuickFill("Dettol Original Bathing Soap 125g", "personal_care", "Reckitt Benckiser", "125 g", "58")}
            className="text-xs px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-md font-medium transition-colors"
          >
            Dettol Soap (125g)
          </button>
          <button
            type="button"
            onClick={() => handleQuickFill("Vim Dishwash Liquid Gel 500ml", "household", "Hindustan Unilever", "500 ml", "115")}
            className="text-xs px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-md font-medium transition-colors"
          >
            Vim Dishwash (500ml)
          </button>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Product Name */}
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Commodity / Product Name *
            </label>
            <input
              type="text"
              required
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="e.g. Britannia NutriChoice Digestive Biscuits 100g"
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
            />
          </div>

          {/* Category */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Commodity Category *
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as ProductCategory)}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
            >
              <option value="food_grocery">Food and Grocery</option>
              <option value="beverage">Beverages</option>
              <option value="personal_care">Personal Care Products</option>
              <option value="household">Household Commodities</option>
            </select>
          </div>

          {/* Brand */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Manufacturer / Brand Name
            </label>
            <input
              type="text"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="e.g. Britannia Industries Ltd."
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
            />
          </div>

          {/* Declared Net Qty */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Declared Net Quantity *
            </label>
            <input
              type="text"
              required
              value={declaredNetQty}
              onChange={(e) => setDeclaredNetQty(e.target.value)}
              placeholder="e.g. 100 g or 500 ml"
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
            />
          </div>

          {/* Declared MRP */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Declared MRP (₹ Inclusive of Taxes) *
            </label>
            <input
              type="number"
              step="0.01"
              required
              value={declaredMRP}
              onChange={(e) => setDeclaredMRP(e.target.value)}
              placeholder="e.g. 25.00"
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
            />
          </div>

          {/* Location */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Inspection Premises / Location
            </label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
            />
          </div>

          {/* Inspector Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Designated Inspector
            </label>
            <input
              type="text"
              value={inspectorName}
              onChange={(e) => setInspectorName(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
            />
          </div>
        </div>

        {/* Submit Bar */}
        <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            Next: Guided Capture of Front, Rear, and Side package panels with ArUco reference marker.
          </span>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg text-sm transition-all shadow-md flex items-center space-x-2"
          >
            <span>Proceed to Guided Capture</span>
            <span>&rarr;</span>
          </button>
        </div>
      </form>
    </div>
  );
}
