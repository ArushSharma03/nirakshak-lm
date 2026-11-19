"use client";

import { TopBarContent } from "@/components/layout/TopBarContent";

import { useState } from "react";
import { useRouter } from "next/navigation";
import CameraCapture from "@/components/CameraCapture";
import { createInspection, uploadInspectionView } from "@/lib/api";
import { analyzeInspection } from "@/lib/analysis";
import { VIEWS, VIEW_LABEL, errorText } from "@/lib/format";
import { ButtonLink, Notice, buttonClass } from "@/components/ui";

type Run =
  | { kind: "idle" }
  | { kind: "running"; stage: string; previews: string[] }
  | { kind: "failed"; message: string; previews: string[]; inspectionId: string | null };

export default function NewInspectionPage() {
  const router = useRouter();
  const [run, setRun] = useState<Run>({ kind: "idle" });

  async function start(photos: Blob[]) {
    if (photos.length > VIEWS.length) {
      setRun({ kind: "failed", message: `Choose up to ${VIEWS.length} photos: front, rear and side.`, previews: [], inspectionId: null });
      return;
    }
    const previews = photos.map((photo) => URL.createObjectURL(photo));
    const stage = (label: string) => setRun({ kind: "running", stage: label, previews });
    let inspectionId: string | null = null;
    try {
      stage("Creating the inspection");
      inspectionId = (await createInspection()).id;
      for (const [index, photo] of photos.entries()) {
        stage(`Uploading the ${VIEW_LABEL[VIEWS[index]].toLowerCase()} photo`);
        await uploadInspectionView(inspectionId, VIEWS[index], photo);
      }
      stage("Reading the label");
      await analyzeInspection(inspectionId, {});
      router.push(`/reports?id=${encodeURIComponent(inspectionId)}`);
    } catch (cause) {
      setRun({ kind: "failed", message: errorText(cause, "Check that the API is online."), previews, inspectionId });
    }
  }

  const previews = run.kind === "idle" ? [] : run.previews;

  return (
    <div className="page-stack">
      <TopBarContent
        title="New inspection"
        lede="Add photos of the package. The name, origin and every declaration are read from the label."
      />

      {run.kind !== "running" && (
        <CameraCapture
          multiple
          onCapture={(photos) => void start(photos)}
          hint="Take or upload up to three photos. They are filed as front, rear and side in that order. One clear photo of the declaration panel is enough."
        />
      )}

      {previews.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-3">
          {previews.map((url, index) => (
            <li key={url} className="overflow-hidden rounded-xl border border-rule bg-sheet">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={url} alt={`${VIEW_LABEL[VIEWS[index]]} panel`} className="aspect-[4/3] w-full bg-ground object-contain" />
              <p className="px-3 py-2 text-sm font-semibold">{VIEW_LABEL[VIEWS[index]]}</p>
            </li>
          ))}
        </ul>
      )}

      {run.kind === "running" && (
        <p role="status" className="rounded-xl border border-rule bg-sheet p-5 text-sm text-ink-2">
          <span className="block font-semibold text-ink">{run.stage}…</span>
          OCR runs on the server. On CPU, or on the first run while model weights download, this can take several minutes. Keep this tab open.
        </p>
      )}

      {run.kind === "failed" && (
        <Notice
          tone="danger"
          title="The inspection did not finish"
          action={
            run.inspectionId ? (
              <ButtonLink href={`/inspect?id=${encodeURIComponent(run.inspectionId)}`} variant="secondary">Continue in guided capture</ButtonLink>
            ) : (
              <button type="button" onClick={() => setRun({ kind: "idle" })} className={buttonClass.secondary}>Try again</button>
            )
          }
        >
          {run.message} {run.inspectionId ? "Photos that uploaded are stored; continue to retry analysis." : "Nothing was saved."}
        </Notice>
      )}
    </div>
  );
}
