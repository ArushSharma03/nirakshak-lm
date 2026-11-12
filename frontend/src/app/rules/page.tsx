"use client";

import { useState } from "react";
import { selectProfile, type Profile, type ProfileInputs } from "@/lib/analysis";
import LegalDisclaimer from "@/components/common/LegalDisclaimer";

export default function RulesExplorerPage() {
  const [origin, setOrigin] = useState<ProfileInputs["origin"]>("unknown");
  const [category, setCategory] = useState<ProfileInputs["category"]>("food_grocery");
  const [asOf, setAsOf] = useState(new Date().toISOString().slice(0, 10));
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function select() {
    setLoading(true);
    setError(null);
    setProfile(null);
    try {
      setProfile(await selectProfile({ category, origin, as_of: asOf }));
    } catch (error) {
      setError(error instanceof Error ? error.message : "Profile service unavailable.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Compliance profile selection</h1>
        <p className="text-sm text-slate-600 mt-1">Select versioned rule data by category, origin and effective date. The MVP inventory covers food and grocery packages.</p>
      </div>
      <LegalDisclaimer compact />
      <form onSubmit={(event) => { event.preventDefault(); void select(); }} className="bg-white border rounded-xl p-5 flex flex-wrap gap-4 items-end text-sm">
        <label>Category<select className="block border rounded p-2 mt-1" value={category} onChange={(event) => {
          const value = event.target.value;
          if (value === "food_grocery" || value === "beverage" || value === "personal_care" || value === "household") { setCategory(value); setProfile(null); }
        }}>
          <option value="food_grocery">Food / grocery</option><option value="beverage">Beverage</option>
          <option value="personal_care">Personal care</option><option value="household">Household</option>
        </select></label>
        <label>Origin<select className="block border rounded p-2 mt-1" value={origin} onChange={(event) => {
          const value = event.target.value;
          if (value === "domestic" || value === "imported" || value === "unknown") { setOrigin(value); setProfile(null); }
        }}><option value="unknown">Unknown</option><option value="domestic">Domestic</option><option value="imported">Imported</option></select></label>
        <label>Effective date<input required type="date" className="block border rounded p-2 mt-1" value={asOf} onChange={(event) => { setAsOf(event.target.value); setProfile(null); }} /></label>
        <button disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50">{loading ? "Selecting…" : "Select profile"}</button>
      </form>
      {error && <p role="alert" className="text-red-800">{error}</p>}
      {profile && <section className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="font-bold">{profile.id || profile.status} {profile.version}</h2>
        <p className="text-sm">{profile.reason}</p><p className="text-sm text-amber-800">{profile.advisory}</p>
        {profile.rules.map((rule) => <article className="border-t pt-3 text-sm" key={rule.id}>
          <h3 className="font-semibold">{rule.citation} · {rule.field.replaceAll("_", " ")}</h3>
          <p>{rule.requirement}</p>
          <p className="text-xs text-slate-500 mt-1">{rule.version} · Effective {rule.effective_from} to {rule.effective_to || "open"}</p>
          <a className="text-xs text-blue-700 underline" href={rule.source_url} target="_blank" rel="noreferrer">Source register</a>
        </article>)}
      </section>}
    </div>
  );
}
