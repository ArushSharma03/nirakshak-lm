"use client";

import { TopBarContent } from "@/components/layout/TopBarContent";

import { useEffect, useState } from "react";
import { getRegulationIndex, selectProfile, type Profile, type ProfileInputs, type RegulationIndex } from "@/lib/analysis";
import { CATEGORY_LABEL, errorText, fieldLabel } from "@/lib/format";
import { Icon, Loading, Notice, Badge, buttonClass, inputClass } from "@/components/ui";

function SourceIndex() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [index, setIndex] = useState<RegulationIndex | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searching, setSearching] = useState(true);

  useEffect(() => {
    let alive = true;
    const timer = setTimeout(async () => {
      setSearching(true);
      setError(null);
      try {
        const result = await getRegulationIndex(submitted);
        if (alive) setIndex(result);
      } catch (cause) {
        if (alive) {
          setIndex(null);
          setError(errorText(cause, "Source index unavailable."));
        }
      } finally {
        if (alive) setSearching(false);
      }
    }, 0);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [submitted]);

  // Search as you type, after a short pause.
  useEffect(() => {
    const timer = setTimeout(() => setSubmitted(query.trim()), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const titleOf = (sourceId?: string) => index?.sources.find((s) => s.id === sourceId)?.title;
  const groups = index
    ? Array.from(new Set(index.documents.map((d) => d.source_id ?? ""))).map((id) => ({
        id,
        title: titleOf(id) ?? (id ? id : "Other documents"),
        documents: index.documents.filter((d) => (d.source_id ?? "") === id),
      }))
    : [];

  return (
    <section className="space-y-5" aria-labelledby="sources">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-2xl space-y-1">
          <h2 id="sources" className="text-base font-semibold">Official source index</h2>
          <p className="text-sm text-ink-2">
            Links to LMPC and FSSAI documents on official government indexes. Being listed does not mean a notification is in force for your date.
          </p>
        </div>
        <form
          role="search"
          className="relative sm:w-80"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(query.trim());
          }}
        >
          <label>
            <span className="sr-only">Search documents</span>
            <span className="pointer-events-none absolute left-3 top-1/2 mt-[3px] -translate-y-1/2 text-ink-3">
              <Icon name="search" />
            </span>
            <input
              type="search"
              maxLength={200}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. 2026, imported, consumer"
              className={`${inputClass} pl-9`}
            />
          </label>
        </form>
      </div>

      {error && <Notice tone="danger" title="The source index could not be loaded">{error} The index is served by the API on port 8000.</Notice>}
      {!index && !error && searching && <Loading label="Loading source index" />}

      {index && (
        <div className={`space-y-6 transition-opacity ${searching ? "opacity-60" : ""}`} aria-live="polite" aria-busy={searching}>
          <p className="text-sm text-ink-2">
            <span className="serial text-ink">{index.documents.length}</span> document{index.documents.length === 1 ? "" : "s"}
            {submitted ? ` matching “${submitted}”` : ""} · index retrieved {index.retrieved_on}. {index.purpose} Each document is listed on an official index; its operative effect has not been verified.
          </p>

          {index.sources.length > 0 && (
            <ul className="grid gap-3 md:grid-cols-2">
              {index.sources.map((source) => (
                <li key={source.id} className="space-y-2 rounded-xl border border-rule bg-sheet p-4">
                  <h3 className="font-semibold leading-snug">{source.title}</h3>
                  {source.publisher && <p className="text-xs text-ink-3">{source.publisher}</p>}
                  <p className="text-sm text-warn">{source.consolidation_status}</p>
                  <p className="text-xs text-ink-2">Sections reviewed: {source.sections_reviewed.join(", ")}</p>
                  <p className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
                    <a className="inline-flex items-center gap-1 font-semibold text-accent hover:underline" href={source.reference_text_url} target="_blank" rel="noreferrer">
                      Reference text <Icon name="external" className="size-3.5" />
                    </a>
                    <a className="inline-flex items-center gap-1 font-semibold text-accent hover:underline" href={source.official_index_url} target="_blank" rel="noreferrer">
                      Official register <Icon name="external" className="size-3.5" />
                    </a>
                  </p>
                </li>
              ))}
            </ul>
          )}

          {groups.map((group) => (
            <div key={group.id} className="space-y-2">
              <h3 className="text-sm font-semibold">
                {group.title} <span className="serial font-normal text-ink-3">{group.documents.length}</span>
              </h3>
              <ul className="divide-y divide-rule overflow-hidden rounded-xl border border-rule bg-sheet">
                {group.documents.map((doc) => (
                  <li key={doc.url}>
                    <a href={doc.url} target="_blank" rel="noreferrer" className="flex items-start gap-3 px-4 py-2.5 text-sm hover:bg-ground">
                      <span className="min-w-0 flex-1">
                        <span className="block font-medium text-ink">{doc.title}</span>
                      </span>
                      <Icon name="external" className="mt-1 size-3.5 text-accent" />
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          {index.sources.length === 0 && index.documents.length === 0 && (
            <div className="rounded-xl border border-dashed border-rule-strong bg-sheet px-6 py-8 text-center text-sm">
              <p className="font-semibold">No matching documents</p>
              <p className="mt-1 text-ink-2">Try a broader term, or clear the search to see all of them.</p>
            </div>
          )}

          {index.unknowns.length > 0 && (
            <details className="rounded-xl border border-warn/40 bg-warn-wash px-4 py-3 text-sm">
              <summary className="cursor-pointer font-semibold text-warn">What this index cannot tell you ({index.unknowns.length})</summary>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-2">
                {index.unknowns.map((unknown) => (
                  <li key={unknown}>{unknown}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </section>
  );
}

function ProfileLookup() {
  const [origin, setOrigin] = useState<ProfileInputs["origin"]>("unknown");
  const [category, setCategory] = useState<ProfileInputs["category"]>("food_grocery");
  const [asOf, setAsOf] = useState(() => new Date().toISOString().slice(0, 10));
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function select() {
    setLoading(true);
    setError(null);
    setProfile(null);
    try {
      setProfile(await selectProfile({ category, origin, as_of: asOf }));
    } catch (cause) {
      setError(errorText(cause, "Profile service unavailable."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-4" aria-labelledby="profile-lookup">
      <div className="max-w-2xl space-y-1">
        <h2 id="profile-lookup" className="text-base font-semibold">Which rules apply</h2>
        <p className="text-sm text-ink-2">The versioned rule data an analysis would use for a category, origin and date. Only food and grocery has rule data so far.</p>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void select();
        }}
        className="grid gap-4 rounded-xl border border-rule bg-sheet p-4 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end"
      >
        <label className="block text-sm font-medium">
          Category
          <select
            className={inputClass}
            value={category}
            onChange={(e) => {
              setCategory(e.target.value as ProfileInputs["category"]);
              setProfile(null);
            }}
          >
            {Object.entries(CATEGORY_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-medium">
          Origin
          <select
            className={inputClass}
            value={origin}
            onChange={(e) => {
              setOrigin(e.target.value as ProfileInputs["origin"]);
              setProfile(null);
            }}
          >
            <option value="unknown">Unknown</option>
            <option value="domestic">Domestic</option>
            <option value="imported">Imported</option>
          </select>
        </label>
        <label className="block text-sm font-medium">
          In force on
          <input
            required
            type="date"
            className={inputClass}
            value={asOf}
            onChange={(e) => {
              setAsOf(e.target.value);
              setProfile(null);
            }}
          />
        </label>
        <button disabled={loading} className={buttonClass.primary}>
          {loading ? "Looking up…" : "Show rules"}
        </button>
      </form>

      {error && <Notice tone="danger" title="No profile returned">{error}</Notice>}
      {profile && (
        <div className="space-y-3 rounded-xl border border-rule bg-sheet p-4" aria-live="polite">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold">
              {profile.id ?? "No profile"} <span className="serial text-sm font-normal text-ink-2">{profile.version}</span>
            </h3>
            <Badge tone={profile.status === "selected" ? "accent" : profile.status === "review_required" ? "warn" : "danger"}>{profile.status.replaceAll("_", " ")}</Badge>
          </div>
          <p className="text-sm text-ink-2">{profile.reason}</p>
          <p className="text-sm text-warn">{profile.advisory}</p>
          {profile.rules.length > 0 && (
            <ul className="divide-y divide-rule border-t border-rule">
              {profile.rules.map((rule) => (
                <li key={rule.id} className="grid gap-1 py-3 text-sm sm:grid-cols-[12rem_minmax(0,1fr)] sm:gap-4">
                  <span>
                    <span className="block font-semibold">{rule.citation}</span>
                    <span className="block text-xs text-ink-3">{fieldLabel(rule.field)}</span>
                  </span>
                  <span className="space-y-1">
                    <span className="block">{rule.requirement}</span>
                    <span className="block text-xs text-ink-3">
                      {rule.version} · effective {rule.effective_from} to {rule.effective_to ?? "open"} ·{" "}
                      <a className="text-accent hover:underline" href={rule.source_url} target="_blank" rel="noreferrer">
                        source register
                      </a>
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

export default function RulesPage() {
  return (
    <div className="page-stack">
      <TopBarContent
        title="Rules and sources"
        lede="The rule data behind each analysis, and where it comes from. These are research aids, not a consolidated legal text."
      />
      <ProfileLookup />
      <SourceIndex />
    </div>
  );
}
