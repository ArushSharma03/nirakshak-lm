"use client";

import React, { useEffect, useState } from "react";
import { getComplianceRules } from "@/lib/api";
import { ComplianceRule } from "@/types";
import LegalDisclaimer from "@/components/common/LegalDisclaimer";

export default function RulesExplorerPage() {
  const [rules, setRules] = useState<ComplianceRule[]>([]);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("ALL");

  useEffect(() => {
    async function load() {
      const data = await getComplianceRules();
      setRules(data);
    }
    load();
  }, []);

  const filteredRules = rules.filter((r) => {
    const matchesSearch =
      r.ruleCode.toLowerCase().includes(search.toLowerCase()) ||
      r.title.toLowerCase().includes(search.toLowerCase()) ||
      r.description.toLowerCase().includes(search.toLowerCase());

    const matchesCategory =
      selectedCategory === "ALL" || r.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Legal Metrology Compliance Rules Explorer
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Statutory clauses implemented in Nirikshak-LM under the Legal Metrology (Packaged Commodities) Rules, 2011 and amendments.
          </p>
        </div>

        <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-teal-50 border border-teal-200 text-teal-800 rounded-lg text-xs font-semibold">
          <span>Active Ruleset:</span>
          <span className="font-mono">v2026.1 (LMPC 2011)</span>
        </div>
      </div>

      <LegalDisclaimer compact />

      {/* Filter and Search */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
        <div className="flex-1 relative">
          <svg className="w-4 h-4 text-slate-400 absolute left-3 top-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search rules by clause or keyword (e.g. MRP, Net Quantity, Character Height)..."
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs sm:text-sm text-slate-900 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20"
          />
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <span className="text-xs font-semibold text-slate-500">Category:</span>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs font-medium text-slate-800"
          >
            <option value="ALL">All Categories</option>
            <option value="declaration">Mandatory Declarations</option>
            <option value="pricing">Retail Pricing (MRP)</option>
            <option value="dimension">Dimensions & Scale</option>
            <option value="consumer_care">Consumer Care</option>
          </select>
        </div>
      </div>

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredRules.map((rule) => (
          <div
            key={rule.id}
            className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs hover:border-slate-300 transition-all flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-1 rounded-md bg-slate-900 text-teal-300 font-mono text-xs font-bold tracking-tight">
                  {rule.ruleCode}
                </span>
                <span className="text-[10px] uppercase font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  {rule.category}
                </span>
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-900">
                  {rule.title}
                </h3>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  {rule.description}
                </p>
              </div>

              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
                <span className="font-semibold text-slate-700 block mb-0.5">Verification Criteria:</span>
                <span className="text-slate-600 leading-normal">{rule.summaryRequirement}</span>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
              <span>{rule.statutoryCitation}</span>
              {rule.mandatory && (
                <span className="text-rose-600 font-bold uppercase text-[10px]">
                  Mandatory
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Second Schedule Character Height Table */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="border-b border-slate-200 pb-3">
          <h2 className="text-lg font-bold text-slate-900">
            Second Schedule: Minimum Height of Numerals and Letters
          </h2>
          <p className="text-xs text-slate-500">
            Mandatory font height thresholds under Rule 5 based on the Principal Display Panel (PDP) area.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[11px]">
              <tr>
                <th className="py-2.5 px-4">Area of Principal Display Panel (A)</th>
                <th className="py-2.5 px-4">Min. Height (Normal Case)</th>
                <th className="py-2.5 px-4">Min. Height (Blown / Moulded / Perforated)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              <tr>
                <td className="py-2.5 px-4 font-medium">A ≤ 50 cm²</td>
                <td className="py-2.5 px-4 text-teal-700 font-semibold">1.0 mm (weight) / 1.5 mm (other)</td>
                <td className="py-2.5 px-4">2.0 mm</td>
              </tr>
              <tr>
                <td className="py-2.5 px-4 font-medium">50 cm² &lt; A ≤ 100 cm²</td>
                <td className="py-2.5 px-4 text-teal-700 font-semibold">1.5 mm (weight) / 2.0 mm (other)</td>
                <td className="py-2.5 px-4">3.0 mm</td>
              </tr>
              <tr>
                <td className="py-2.5 px-4 font-medium">100 cm² &lt; A ≤ 500 cm²</td>
                <td className="py-2.5 px-4 text-teal-700 font-semibold">2.5 mm</td>
                <td className="py-2.5 px-4">4.0 mm</td>
              </tr>
              <tr>
                <td className="py-2.5 px-4 font-medium">500 cm² &lt; A ≤ 2500 cm²</td>
                <td className="py-2.5 px-4 text-teal-700 font-semibold">4.0 mm</td>
                <td className="py-2.5 px-4">6.0 mm</td>
              </tr>
              <tr>
                <td className="py-2.5 px-4 font-medium">A &gt; 2500 cm²</td>
                <td className="py-2.5 px-4 text-teal-700 font-semibold">6.0 mm</td>
                <td className="py-2.5 px-4">8.0 mm</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
