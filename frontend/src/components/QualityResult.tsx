"use client";

import { useState } from "react";
import type { QualityAssessment, QualityMetricItem } from "@/types";
import { Badge, qualityTone } from "@/components/ui";

interface QualityResultProps {
  assessment: QualityAssessment | null;
  rawPreviewUrl?: string | null;
  processedUrl?: string | null;
}

const METRICS: { key: keyof QualityAssessment["metrics"]; label: string; reading: (m: QualityMetricItem) => string }[] = [
  { key: "sharpness", label: "Sharpness", reading: (m) => (m.value != null ? `Laplacian var ${m.value}` : "No reading") },
  { key: "exposure", label: "Exposure", reading: (m) => (m.value != null ? `Mean ${m.value}` : "No reading") },
  { key: "contrast", label: "Contrast", reading: (m) => (m.value != null ? `Std ${m.value}` : "No reading") },
  { key: "glare", label: "Glare", reading: (m) => (m.value != null ? `${m.value}% hotspots` : "No reading") },
  { key: "resolution", label: "Resolution", reading: (m) => (m.width && m.height ? `${m.width} × ${m.height}` : "No reading") },
];

/** Optical capture quality of the original photo. Not OCR accuracy, not compliance. */
export default function QualityResult({ assessment, rawPreviewUrl, processedUrl }: QualityResultProps) {
  const [showProcessed, setShowProcessed] = useState(false);
  if (!assessment) return null;

  return (
    <section className="space-y-4 rounded-xl border border-rule bg-sheet p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">
          Photo optics <span className="serial ml-1 font-normal text-ink-2">Optical score: {assessment.composite_score}/100</span>
        </h3>
        <Badge tone={qualityTone(assessment.overall_status)}>{assessment.overall_status}</Badge>
      </div>

      <p className="text-sm leading-relaxed text-ink-2">
        This score checks the original photo. It does not measure OCR accuracy.
        Even 100/100 cannot confirm readable small print or complete declarations.
        Enhancement cannot recover text lost to blur, glare or low resolution.
      </p>

      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-rule bg-rule sm:grid-cols-5">
        {METRICS.map(({ key, label, reading }) => {
          const metric = assessment.metrics[key];
          if (!metric) return null;
          const tone = qualityTone(metric.status);
          return (
            <div key={key} className="bg-sheet px-3 py-2.5" title={metric.message}>
              <dt className="field-label">{label}</dt>
              <dd className={`text-sm font-semibold ${tone === "ok" ? "text-ok" : tone === "warn" ? "text-warn" : "text-danger"}`}>{metric.status}</dd>
              <dd className="serial text-xs text-ink-3">{reading(metric)}</dd>
            </div>
          );
        })}
      </dl>

      {assessment.recommendations.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-sm text-ink-2">
          {assessment.recommendations.map((rec) => (
            <li key={rec}>{rec}</li>
          ))}
        </ul>
      )}

      {processedUrl && (
        <div className="space-y-3 border-t border-rule pt-3">
          <button type="button" onClick={() => setShowProcessed(!showProcessed)} aria-expanded={showProcessed} className="text-sm font-semibold text-accent hover:underline">
            {showProcessed ? "Hide enhanced copy" : "Compare with enhanced copy (CLAHE)"}
          </button>
          {showProcessed && (
            <div className="grid grid-cols-2 gap-3">
              {rawPreviewUrl && (
                <figure className="space-y-1">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={rawPreviewUrl} alt="Original photo" className="aspect-[4/3] w-full rounded-md bg-ink object-contain" />
                  <figcaption className="text-xs text-ink-3">Original, kept unchanged as evidence</figcaption>
                </figure>
              )}
              <figure className="space-y-1">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={processedUrl} alt="Enhanced copy" className="aspect-[4/3] w-full rounded-md bg-ink object-contain" />
                <figcaption className="text-xs text-ink-3">Enhanced copy (bilateral denoise + CLAHE)</figcaption>
              </figure>
            </div>
          )}
        </div>
      )}

      {assessment.disclaimer && <p className="text-xs text-ink-3">{assessment.disclaimer}</p>}
    </section>
  );
}
