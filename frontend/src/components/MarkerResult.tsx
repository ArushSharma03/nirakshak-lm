import type { MarkerDetectionResult } from "@/lib/api";
import { Field, Badge } from "@/components/ui";

export default function MarkerResult({ result }: { result: MarkerDetectionResult | null }) {
  if (!result) return null;
  return (
    <section className="space-y-3 rounded-xl border border-rule bg-sheet p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Reference marker</h3>
        {result.detected ? <Badge tone="ok">Found</Badge> : <Badge tone="neutral">Not found</Badge>}
      </div>
      <p className="text-sm text-ink-2">{result.message}</p>
      {result.detected && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Field label="Marker size in photo" mono>
            {result.pixel_width && result.pixel_height ? `${result.pixel_width} × ${result.pixel_height} px` : "Not reported"}
          </Field>
          <Field label="Preliminary scale" mono>
            {result.estimated_ppm ? `${result.estimated_ppm} px/mm` : "Not reported"}
          </Field>
          <Field label="Detection score" mono>
            {typeof result.score === "number" ? result.score.toFixed(2) : "Not reported"}
          </Field>
        </div>
      )}
    </section>
  );
}
