"use client";

import { useState } from "react";
import { checkInspection, type Analysis } from "@/lib/analysis";
import { errorText, fieldLabel, VIEW_LABEL } from "@/lib/format";
import { Badge, Notice, buttonClass, inputClass, type Tone } from "@/components/ui";

type Result = NonNullable<Analysis["checks"]>["results"][number];
const STATUS: Record<Result["status"], { label: string; tone: Tone }> = {
  pass: { label: "Pass", tone: "ok" }, fail: { label: "Fail", tone: "danger" },
  insufficient_evidence: { label: "Insufficient evidence", tone: "warn" },
  not_applicable: { label: "Not applicable", tone: "neutral" },
};

export default function DeclarationChecks({ id, analysis, onUpdate }: { id: string; analysis: Analysis; onUpdate: (next: Analysis) => void }) {
  const [origin, setOrigin] = useState(analysis.profile.inputs.origin);
  const [asOf, setAsOf] = useState(analysis.profile.inputs.as_of);
  const [filter, setFilter] = useState<Result["status"] | "all">("all");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [measureGlyph, setMeasureGlyph] = useState(false);
  const [clearGlyphs, setClearGlyphs] = useState(false);
  const [glyphField, setGlyphField] = useState<Result["field"]>("net_quantity");
  const [glyphView, setGlyphView] = useState<"front" | "rear" | "side">("rear");
  const [coordinates, setCoordinates] = useState({ x0: "", y0: "", x1: "", y1: "" });
  const report = analysis.checks;
  const results = report?.results ?? [];
  async function run() {
    setBusy(true);
    setError(null);
    try {
      const box = { x0: Number(coordinates.x0), y0: Number(coordinates.y0), x1: Number(coordinates.x1), y1: Number(coordinates.y1) };
      if (measureGlyph && (Object.values(coordinates).some((v) => !v.trim()) || !Object.values(box).every(Number.isFinite) || box.x0 < 0 || box.y0 < 0 || box.x1 <= box.x0 || box.y1 <= box.y0)) {
        throw new Error("Enter a positive single-glyph box in original-image pixels.");
      }
      onUpdate(await checkInspection(id, { origin, as_of: asOf, glyph_measurements: measureGlyph ? [{ field: glyphField, view: glyphView, box }] : [], clear_glyph_measurements: clearGlyphs }));
      setClearGlyphs(false);
    }
    catch (cause) { setError(errorText(cause, "Declaration checks could not be saved.")); }
    finally { setBusy(false); }
  }
  return (
    <section className="space-y-4" aria-labelledby="checks">
      <div className="space-y-1">
        <h2 id="checks" className="text-base font-semibold">Declaration checks</h2>
        <p className="text-sm text-ink-2">{report?.scope ?? "This older analysis has no saved checks. Run checks using its existing OCR evidence."}</p>
      </div>
      <form className="grid gap-4 rounded-md border border-rule bg-sheet p-5 sm:grid-cols-2 xl:grid-cols-[1fr_1fr_auto] xl:items-end" onSubmit={(event) => { event.preventDefault(); void run(); }}>
        <label className="text-sm">Package origin
          <select aria-label="Check package origin" className={inputClass} value={origin} disabled={busy} onChange={(event) => {
            const value = event.target.value;
            if (value === "unknown" || value === "domestic" || value === "imported") setOrigin(value);
          }}>
            <option value="unknown">Unknown</option><option value="domestic">Domestic</option><option value="imported">Imported</option>
          </select>
        </label>
        <label className="text-sm">Rules as of
          <input type="date" required className={inputClass} value={asOf} disabled={busy} onChange={(event) => setAsOf(event.target.value)} />
        </label>
        <button className={buttonClass.secondary} type="submit" disabled={busy}>{busy ? "Checking…" : "Run declaration checks"}</button>
        <p className="text-xs text-ink-3 sm:col-span-2 xl:col-span-3">Confirm origin from the package. Uses saved OCR; no OCR rerun or Jev charge. Setup notes are excluded.</p>
        <details className="min-w-0 text-sm sm:col-span-2 xl:col-span-3">
          <summary className="cursor-pointer text-accent">Inspector glyph measurement</summary>
          <div className="mt-3 space-y-3">
            <p className="text-xs text-ink-2">Open the original photo and select the pixel bounds of one printed letter or numeral within a located declaration. This is an inspector annotation. It requires a detected 50 mm marker and confirmed coplanarity from capture. A whole text line is not a glyph.</p>
            <label className="flex gap-2"><input type="checkbox" checked={measureGlyph} disabled={busy} onChange={(e) => setMeasureGlyph(e.target.checked)} />Include this glyph annotation</label>
            <label className="flex gap-2"><input type="checkbox" checked={clearGlyphs} disabled={busy} onChange={(e) => setClearGlyphs(e.target.checked)} />Clear saved glyph annotations when running checks</label>
            {measureGlyph && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <label>Declaration<select className={inputClass} value={glyphField} disabled={busy} onChange={(e) => {
                const field = analysis.fields.find((f) => f.field === e.target.value);
                if (field) setGlyphField(field.field);
              }}>{analysis.fields.map((f) => <option key={f.field} value={f.field}>{fieldLabel(f.field)}</option>)}</select></label>
              <label>Photo<select className={inputClass} value={glyphView} disabled={busy} onChange={(e) => {
                const v = e.target.value;
                if (v === "front" || v === "rear" || v === "side") setGlyphView(v);
              }}><option value="front">Front</option><option value="rear">Rear</option><option value="side">Side</option></select></label>
              {(["x0", "y0", "x1", "y1"] as const).map((key) => <label key={key}>{key} in pixels<input className={inputClass} type="number" min="0" step="any" required disabled={busy} value={coordinates[key]} onChange={(e) => setCoordinates((prev) => ({ ...prev, [key]: e.target.value }))} /></label>)}
            </div>}
          </div>
        </details>
      </form>
      {error && <Notice tone="danger" title="Checks were not updated">{error}</Notice>}
      {report && <>
        <label className="block text-sm">Show results
          <select aria-label="Filter declaration checks" className={`${inputClass} sm:max-w-xs`} value={filter} onChange={(event) => {
            const value = event.target.value;
            if (value === "all" || value === "pass" || value === "fail" || value === "insufficient_evidence" || value === "not_applicable") setFilter(value);
          }}>
            <option value="all">All {results.length} checks</option>
            {Object.entries(STATUS).map(([status, info]) => <option key={status} value={status}>{info.label} · {results.filter((r) => r.status === status).length}</option>)}
          </select>
        </label>
        <ol className="divide-y divide-rule rounded-md border border-rule bg-sheet">
          {results.filter((r) => filter === "all" || r.status === filter).map((result) => (
            <li key={`${result.rule_id}-${result.field}-${result.kind}`} className="grid min-w-0 gap-3 p-5 lg:grid-cols-[13rem_minmax(0,1fr)]">
              <div className="space-y-1">
                <h3 className="text-sm font-semibold">{fieldLabel(result.field)} · {result.kind.replaceAll("_", " ")}</h3>
                <Badge tone={STATUS[result.status].tone}>{STATUS[result.status].label}</Badge>
              </div>
              <div className="min-w-0 space-y-2 text-sm">
                <p>{result.reason}</p>
                <p className="text-xs text-ink-3">{result.citation} {result.source_url && <a className="text-accent underline" href={result.source_url} target="_blank" rel="noreferrer">Source</a>}</p>
                {result.measured_mm !== null && <p>Inspector-selected glyph height {result.measured_mm} mm{result.required_mm !== null ? `; required ${result.required_mm} mm.` : "; applicable threshold not established."}</p>}
                {result.evidence.length > 0 && <details><summary className="cursor-pointer text-xs text-accent">Source evidence · {result.evidence.length}</summary>
                  <ul className="mt-2 space-y-2">{result.evidence.map((e, index) => <li key={index} className="rounded border border-rule bg-ground p-3 text-xs">
                    <p>{VIEW_LABEL[e.view]} · {e.provider}{e.box && ` · box ${e.box.x0}, ${e.box.y0}, ${e.box.x1}, ${e.box.y1}`}</p>
                    {e.glyph_box && <p>Inspector glyph box: {e.glyph_box.x0}, {e.glyph_box.y0}, {e.glyph_box.x1}, {e.glyph_box.y1}</p>}
                    <blockquote className="mt-1 whitespace-pre-wrap break-words">{e.source_text}</blockquote>
                  </li>)}</ul>
                </details>}
              </div>
            </li>
          ))}
        </ol>
        {results.filter((r) => filter === "all" || r.status === filter).length === 0 && <p className="text-sm text-ink-2">No checks match this filter.</p>}
      </>}
    </section>
  );
}
