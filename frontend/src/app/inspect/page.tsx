"use client";

import { TopBarContent } from "@/components/layout/TopBarContent";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import CameraCapture from "@/components/CameraCapture";
import QualityResult from "@/components/QualityResult";
import { InspectionTable, LoadError, progressOf, useInspections } from "@/components/InspectionLedger";
import { Badge, ButtonLink, Card, EmptyState, Icon, Loading, Notice, buttonClass, inputClass, qualityTone } from "@/components/ui";
import { ApiUnavailableError, getInspectionById, removeInspectionView, uploadInspectionView } from "@/lib/api";
import { analyzeInspection, type ProfileInputs } from "@/lib/analysis";
import { VIEWS, VIEW_LABEL, errorText, type ViewName } from "@/lib/format";
import type { InspectionRecord, QualityAssessment } from "@/types";

type Phase = "empty" | "uploading" | "stored" | "failed";

interface ViewState {
  phase: Phase;
  blob: Blob | null;
  previewUrl: string | null;
  processedUrl: string | null;
  quality: QualityAssessment | null;
  error: string | null;
}

const EMPTY: ViewState = { phase: "empty", blob: null, previewUrl: null, processedUrl: null, quality: null, error: null };

const GUIDANCE: Record<ViewName, string> = {
  front: "The principal display panel: brand, product name and usually the net quantity.",
  rear: "The declaration panel: manufacturer or packer address, MRP, dates, consumer care. Get all small print in focus.",
  side: "Any side panel with batch codes, dates or remaining declarations.",
};

function viewsFromRecord(record: InspectionRecord): Record<ViewName, ViewState> {
  const out = { front: EMPTY, rear: EMPTY, side: EMPTY };
  for (const view of VIEWS) {
    const img = record.images[view];
    if (!img) continue;
    out[view] = {
      phase: "stored",
      blob: null,
      previewUrl: img.previewUrl ?? null,
      processedUrl: img.processedUrl ?? null,
      quality: img.quality_assessment ?? null,
      error: null,
    };
  }
  return out;
}

type Tab = ViewName | "analyze";

function InspectFlow({ inspectionId }: { inspectionId: string }) {
  const router = useRouter();
  const [record, setRecord] = useState<InspectionRecord | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "missing" | "error">("loading");
  const [loadError, setLoadError] = useState("");
  const [views, setViews] = useState<Record<ViewName, ViewState>>({ front: EMPTY, rear: EMPTY, side: EMPTY });
  const [tab, setTab] = useState<Tab>("front");
  const [actionError, setActionError] = useState<string | null>(null);

  const [origin, setOrigin] = useState<ProfileInputs["origin"] | "label">("label");
  const [asOf, setAsOf] = useState(() => new Date().toISOString().slice(0, 10));
  const [useJev, setUseJev] = useState(true);
  const [reuseOcr, setReuseOcr] = useState(false);
  const [processing, setProcessing] = useState(false);

  const load = useCallback(async () => {
    setLoadState("loading");
    try {
      const found = await getInspectionById(inspectionId);
      if (!found) {
        setLoadState("missing");
        return;
      }
      setRecord(found);
      if (found.analysis) {
        setOrigin(found.analysis.profile.inputs.origin);
        setAsOf(found.analysis.profile.inputs.as_of);
      }
      const initial = viewsFromRecord(found);
      setViews(initial);
      const firstMissing = VIEWS.find((v) => initial[v].phase === "empty");
      setTab(found.analysis ? "analyze" : (firstMissing ?? "analyze"));
      setLoadState("ready");
    } catch (cause) {
      setLoadError(cause instanceof ApiUnavailableError ? "The inspection API is offline. Start the backend on port 8000 and try again." : errorText(cause, "Could not load the inspection."));
      setLoadState("error");
    }
  }, [inspectionId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const patch = (view: ViewName, next: Partial<ViewState>) => setViews((prev) => ({ ...prev, [view]: { ...prev[view], ...next } }));

  async function upload(view: ViewName, blob: Blob, previewUrl: string) {
    setActionError(null);
    patch(view, { ...EMPTY, phase: "uploading", blob, previewUrl });
    try {
      const result = await uploadInspectionView(inspectionId, view, blob);
      setRecord(result.record);
      patch(view, { phase: "stored", quality: result.qualityAssessment, processedUrl: result.processedUrl, error: null });
    } catch (cause) {
      patch(view, { phase: "failed", error: errorText(cause, "Upload failed.") });
    }
  }

  async function discard(view: ViewName) {
    setActionError(null);
    if (views[view].phase === "stored") {
      try {
        setRecord(await removeInspectionView(inspectionId, view));
      } catch (cause) {
        setActionError(`The stored ${view} photo was not removed: ${errorText(cause, "the API did not respond")}.`);
        return;
      }
    }
    patch(view, EMPTY);
  }

  async function analyze() {
    setProcessing(true);
    setActionError(null);
    try {
      await analyzeInspection(inspectionId, { origin: origin === "label" ? undefined : origin, as_of: asOf, use_jev: useJev, reuse_ocr: reuseOcr && Boolean(record?.analysis) });
      router.push(`/reports?id=${encodeURIComponent(inspectionId)}`);
    } catch (cause) {
      setActionError(`Analysis did not complete: ${errorText(cause, "check that the API is online")}. Your photos are still stored; try again.`);
      setProcessing(false);
    }
  }

  if (loadState === "loading") return <Loading label={`Loading ${inspectionId}`} />;
  if (loadState === "missing")
    return (
      <Notice tone="danger" title={`No inspection ${inspectionId} on the API`} action={<ButtonLink href="/inspections/new">New inspection</ButtonLink>}>
        It may have been created against another backend. Start a new inspection instead.
      </Notice>
    );
  if (loadState === "error" || !record)
    return (
      <Notice tone="danger" title="The inspection could not be loaded" action={<button type="button" onClick={load} className={buttonClass.secondary}>Try again</button>}>
        {loadError}
      </Notice>
    );

  const stored = VIEWS.filter((v) => views[v].phase === "stored");
  const busy = VIEWS.some((v) => views[v].phase === "uploading") || processing;

  return (
    <div className="page-stack">
      <TopBarContent
        title={`Guided capture · ${record.productName}`}
        lede={<><span className="serial">{record.id}</span>{record.notes && <> · Photo source: {record.notes}</>}</>}
        actions={<>
          <ButtonLink href="/inspections" variant="secondary">Inspection history</ButtonLink>
          {record.analysis && <ButtonLink href={`/reports?id=${encodeURIComponent(record.id)}`} variant="secondary">Open report</ButtonLink>}
        </>}
      />

      <nav aria-label="Capture steps" className="grid grid-cols-4 overflow-hidden rounded-xl border border-rule bg-sheet shadow-[0_1px_2px_rgb(15_23_42/0.04)]">
        {[...VIEWS, "analyze" as const].map((key) => {
          const active = tab === key;
          const state = key === "analyze" ? null : views[key];
          return (
            <button
              key={key}
              type="button"
              aria-current={active ? "step" : undefined}
              onClick={() => setTab(key)}
              disabled={processing}
              className={`relative flex min-h-14 flex-col items-start justify-center gap-0.5 border-r border-rule px-3 text-left last:border-r-0 sm:px-4 transition-colors ${active ? "bg-accent-wash" : "hover:bg-ground"}`}
            >
              <span className={`text-sm font-semibold ${active ? "text-accent" : "text-ink"}`}>{key === "analyze" ? "Analyze" : VIEW_LABEL[key]}</span>
              <span className="hidden text-xs text-ink-3 sm:block">
                {state === null
                  ? `${stored.length} of 3 photos`
                  : state.phase === "stored"
                    ? "Stored"
                    : state.phase === "uploading"
                      ? "Uploading…"
                      : state.phase === "failed"
                        ? "Upload failed"
                        : "No photo"}
              </span>
              {state?.phase === "stored" && <Icon name="check" className="absolute right-2 top-2 size-3.5 text-ok sm:right-3 sm:top-3" />}
              {active && <span className="absolute inset-x-0 bottom-0 h-0.5 bg-accent" />}
            </button>
          );
        })}
      </nav>

      {actionError && <Notice tone="danger" title="Something did not work">{actionError}</Notice>}

      {tab !== "analyze" ? (
        <ViewPanel
          view={tab}
          state={views[tab]}
          onCapture={([blob]) => upload(tab, blob, URL.createObjectURL(blob))}
          onRetry={() => views[tab].blob && views[tab].previewUrl && upload(tab, views[tab].blob!, views[tab].previewUrl!)}
          onDiscard={() => discard(tab)}
          onNext={() => setTab(tab === "front" ? "rear" : tab === "rear" ? "side" : "analyze")}
        />
      ) : (
        <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="space-y-4">
            <h2 className="text-base font-semibold">Photos going into analysis</h2>
            <ul className="grid gap-3 sm:grid-cols-3">
              {VIEWS.map((view) => {
                const state = views[view];
                return (
                  <li key={view} className="overflow-hidden rounded-xl border border-rule bg-sheet shadow-[0_1px_2px_rgb(15_23_42/0.04)]">
                    <div className="aspect-[4/3] bg-ground">
                      {state.phase === "stored" && state.previewUrl ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={state.previewUrl} alt={`${VIEW_LABEL[view]} panel`} className="size-full object-contain" />
                      ) : (
                        <span className="grid size-full place-items-center text-sm text-ink-3">No photo</span>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2.5">
                      <span className="text-sm font-semibold">{VIEW_LABEL[view]}</span>
                      {state.quality ? (
                        <Badge tone={qualityTone(state.quality.overall_status)}>Optics {state.quality.composite_score}</Badge>
                      ) : (
                        <button type="button" onClick={() => setTab(view)} className="text-xs font-semibold text-accent hover:underline">
                          Add photo
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
            {stored.length > 0 && stored.length < 3 && (
              <p className="text-sm text-ink-2">
                Missing panels are recorded as &ldquo;no captured evidence&rdquo;. Declarations printed only on those panels will show as missing.
              </p>
            )}
            {stored.some((v) => views[v].quality?.overall_status === "Retake Recommended") && (
              <Notice tone="warn" title="Retake recommended for some photos">
                OCR may miss small print on {stored.filter((v) => views[v].quality?.overall_status === "Retake Recommended").map((v) => VIEW_LABEL[v].toLowerCase()).join(", ")}. You can still analyze.
              </Notice>
            )}
            {record.analysis && (
              <p className="text-sm text-ink-2">
                This inspection already has an analysis.{" "}
                <Link href={`/reports?id=${encodeURIComponent(record.id)}`} className="font-semibold text-accent hover:underline">
                  Open the report
                </Link>{" "}
                or run it again to replace it.
              </p>
            )}
          </div>

          <form
            className="h-fit space-y-5 rounded-xl border border-rule bg-sheet p-5 shadow-[0_1px_2px_rgb(15_23_42/0.04)] lg:sticky lg:top-6"
            onSubmit={(e) => {
              e.preventDefault();
              void analyze();
            }}
          >
            <h2 className="text-base font-bold">Analysis settings</h2>
            {record.analysis && (
              <label className="flex items-start gap-2 text-sm">
                <input type="checkbox" checked={reuseOcr} onChange={(e) => setReuseOcr(e.target.checked)} className="mt-1" />
                <span>Use stored transcripts<span className="mt-1 block text-xs text-ink-3">Rebuild extraction and checks without running OCR. Incomplete or misread text still needs a fresh photo analysis.</span></span>
              </label>
            )}
            <label className="block text-sm font-medium">
              Package origin
              <select value={origin} onChange={(e) => setOrigin(e.target.value as ProfileInputs["origin"] | "label")} className={inputClass}>
                <option value="label">Read from the label</option>
                <option value="unknown">Unknown (profile needs review)</option>
                <option value="domestic">Domestic</option>
                <option value="imported">Imported</option>
              </select>
            </label>
            <label className="block text-sm font-medium">
              Rules in force on
              <input type="date" required value={asOf} onChange={(e) => setAsOf(e.target.value)} className={inputClass} />
            </label>
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" checked={useJev} onChange={(e) => setUseJev(e.target.checked)} className="mt-0.5 size-4 accent-accent" />
              <span>
                Use Jev to rank readings and place unmatched lines
                <span className="block text-xs text-ink-3">Sends OCR text (not photos) to TypeSafe and uses paid credits. Skipped when the server has no key.</span>
              </span>
            </label>
            <button type="submit" disabled={stored.length === 0 || busy} className={`${buttonClass.primary} w-full`}>
              {processing ? "Analyzing…" : stored.length === 0 ? "Add a photo first" : reuseOcr && record.analysis ? "Rebuild from stored text" : `Analyze ${stored.length} photo${stored.length > 1 ? "s" : ""}`}
            </button>
            {processing && (
              <p role="status" className="text-xs leading-relaxed text-ink-2">
                {reuseOcr && record.analysis ? "Rebuilding extraction and checks from the stored transcripts. No OCR model is running." : "Running OCR, extraction and profile selection on the server. On CPU, or on the first run while model weights download, this can take several minutes. Keep this tab open."}
              </p>
            )}
          </form>
        </section>
      )}

    </div>
  );
}

function ViewPanel({
  view,
  state,
  onCapture,
  onRetry,
  onDiscard,
  onNext,
}: {
  view: ViewName;
  state: ViewState;
  onCapture: (photos: Blob[]) => void;
  onRetry: () => void;
  onDiscard: () => void;
  onNext: () => void;
}) {
  const nextLabel = view === "front" ? "Rear" : view === "rear" ? "Side" : "Analyze";
  return (
    <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-start">
      <div className="space-y-3">
        <div>
          <h2 className="text-base font-semibold">{VIEW_LABEL[view]} panel</h2>
          <p className="text-sm text-ink-2">{GUIDANCE[view]}</p>
        </div>
        {state.phase === "empty" ? (
          <CameraCapture onCapture={onCapture} />
        ) : (
          <div className="space-y-3">
            <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-slate-900">
              {state.previewUrl && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={state.previewUrl} alt={`${VIEW_LABEL[view]} panel photo`} className="size-full object-contain" />
              )}
              {state.phase === "uploading" && (
                <p role="status" className="absolute inset-x-0 bottom-0 bg-slate-900/85 px-3 py-2 text-sm text-white">
                  Uploading and checking optics…
                </p>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {state.phase === "failed" && (
                <button type="button" onClick={onRetry} className={buttonClass.primary}>
                  Retry upload
                </button>
              )}
              <button type="button" onClick={onDiscard} disabled={state.phase === "uploading"} className={buttonClass.secondary}>
                <Icon name="retake" />
                {state.phase === "stored" ? "Remove and retake" : "Discard"}
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {state.phase === "failed" && (
          <Notice tone="danger" title="This photo is not stored">
            {state.error} Retry, or discard and take it again.
          </Notice>
        )}
        {state.phase === "empty" && (
          <div className="hidden rounded-xl border border-dashed border-rule-strong px-4 py-6 text-sm text-ink-2 lg:block">
            After upload you will see the photo&rsquo;s optical check. Panels are optional; skip any that carry no declarations.
          </div>
        )}
        {state.phase === "stored" && (
          <>
            <QualityResult assessment={state.quality} rawPreviewUrl={state.previewUrl} processedUrl={state.processedUrl} />
          </>
        )}
        <div className="flex justify-end pt-1">
          <button type="button" onClick={onNext} disabled={state.phase === "uploading"} className={state.phase === "stored" ? buttonClass.primary : buttonClass.secondary}>
            {state.phase === "stored" ? "Next" : "Skip"}: {nextLabel}
            <Icon name="arrowRight" />
          </button>
        </div>
      </div>
    </section>
  );
}

function ContinueList() {
  const { records, error, reload } = useInspections();
  const open = records?.filter((r) => progressOf(r) !== "analyzed") ?? [];
  return (
    <div className="page-stack">
      <TopBarContent
        title="Guided capture"
        lede="Photos are stored against an inspection. Continue one that still needs photos or analysis, or set up a new package."
        actions={
          <ButtonLink href="/inspections/new">
            <Icon name="plus" />
            New inspection
          </ButtonLink>
        }
      />
      {error && <LoadError error={error} onRetry={reload} />}
      {!error && records === null && <Loading label="Loading inspections from the API" />}
      {records && (
        <Card title="Waiting for photos or analysis" aside={<span className="text-xs text-ink-3">{open.length} of {records.length}</span>} bodyClass="">
          {open.length > 0 ? (
            <InspectionTable records={open} compact />
          ) : (
            <div className="p-5">
              <EmptyState title="Nothing in progress">Every stored inspection has been analyzed. Start a new one to photograph another package.</EmptyState>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function InspectRoute() {
  const id = useSearchParams().get("id");
  if (!id) return <ContinueList />;
  return <InspectFlow key={id} inspectionId={id} />;
}

export default function InspectPage() {
  return (
    <Suspense fallback={<Loading label="Loading capture" />}>
      <InspectRoute />
    </Suspense>
  );
}
