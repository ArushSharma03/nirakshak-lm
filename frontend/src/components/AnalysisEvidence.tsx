import type { Analysis } from "@/lib/analysis";

export default function AnalysisEvidence({ analysis }: { analysis: Analysis }) {
  return (
    <section className="space-y-4 text-sm">
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
        <h2 className="font-bold">Extracted evidence and compliance profile</h2>
        <p>{analysis.profile.id || analysis.profile.status} {analysis.profile.version}</p>
        <p className="text-xs mt-1">{analysis.profile.reason}</p>
        <p className="text-xs mt-1">{analysis.profile.advisory}</p>
      </div>
      {analysis.warnings.length > 0 && <ul className="list-disc pl-5 text-xs text-amber-800">{analysis.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead><tr><th className="p-2">Declaration</th><th className="p-2">Reading</th><th className="p-2">Evidence</th></tr></thead>
          <tbody>{analysis.fields.map((field) => (
            <tr key={field.field} className="border-t align-top">
              <td className="p-2">{field.field.replaceAll("_", " ")}<br /><strong>{field.status}</strong></td>
              <td className="p-2">{field.value || "Inspector review required"}<p className="mt-1 text-slate-500">{field.reason}</p></td>
              <td className="p-2 space-y-2">{field.evidence.map((item, index) => (
                <div key={index}>
                  <p>{item.view} / {item.provider}: {item.value}</p>
                  <p className="text-slate-500">{item.confidence === null ? "Confidence unavailable" : `OCR confidence ${(item.confidence * 100).toFixed(0)}%`}{item.height_mm === null ? "" : ` · Line box height ≈ ${item.height_mm} mm`}</p>
                  <details><summary className="cursor-pointer">Source text and coordinates</summary><p>{item.source_text}</p>{item.box && <p>Original image pixels: {item.box.x0}, {item.box.y0} to {item.box.x1}, {item.box.y1}</p>}</details>
                </div>
              ))}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <div className="rounded border p-3 text-xs space-y-1">
        <h3 className="font-bold">Jev evidence recommendations · {analysis.decision.status}</h3>
        <p>{analysis.decision.model}: {analysis.decision.message}</p>
        {Object.entries(analysis.decision.answers).map(([field, answer]) => {
          const evidence = analysis.fields.find((item) => item.field === field)?.evidence;
          const index = Number(answer.choice.replace("candidate_", ""));
          const chosen = answer.choice === "none" ? "No reliable candidate" : evidence?.[index]?.value || "Review candidate";
          return <p key={field}>{field}: {chosen} · model confidence {(answer.confidence * 100).toFixed(0)}%</p>;
        })}
      </div>
      <details className="text-xs"><summary className="cursor-pointer font-semibold">OCR transcripts and per-view calibration</summary>
        {Object.entries(analysis.views).map(([view, result]) => <div className="py-3 space-y-2" key={view}>
          <h3 className="font-bold">{view} · {result.calibration.status}</h3><p>{result.calibration.reason}</p>
          {result.ocr.map((ocr) => <div key={ocr.provider}><p>{ocr.model} · {ocr.status}</p><p>{ocr.message}</p><pre className="whitespace-pre-wrap">{ocr.lines.map((line) => line.text).join("\n")}</pre></div>)}
        </div>)}
      </details>
      <p className="text-xs text-slate-500">Physical values estimate text-line box height in a confirmed marker plane. Glyph height, legal thresholds and compliance checks are not implemented in this milestone.</p>
    </section>
  );
}
