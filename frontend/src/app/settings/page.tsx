"use client";

import { TopBarContent } from "@/components/layout/TopBarContent";

import { useCallback, useEffect, useState } from "react";
import { useInspections } from "@/components/InspectionLedger";
import { Badge, Card, Field, buttonClass } from "@/components/ui";
import { API_BASE, checkBackendStatus } from "@/lib/api";
import type { SystemStatus } from "@/types";

const PIPELINE: [string, string][] = [
  ["Photo optics", "Sharpness, exposure, contrast, glare and resolution of each original photo, scored 0–100. Advisory only."],
  ["Enhanced copy", "Bilateral denoise and CLAHE produce a second image for viewing. The original is kept unchanged as evidence."],
  ["Transcription", "Xiaomi-OCR reads each panel, with enlarged detail scans, and reads the photo turned when a coding print runs sideways. Tesseract adds line geometry only where its text matches."],
  ["Extraction", "Declarations are matched to the selected rule profile and marked read, conflicting or not found, with source text for each."],
  ["Jev", "When a TypeSafe key is set, Jev ranks readings, places OCR lines no pattern matched, and picks the brand and product name. It only chooses existing text."],
];

export default function SystemPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);
  const { records } = useInspections();

  const check = useCallback(async () => {
    setStatus(null);
    setStatus(await checkBackendStatus());
    setCheckedAt(new Date());
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void check();
  }, [check]);

  const postgres = records?.filter((r) => r.databaseSaved).length ?? 0;
  const fileStore = records ? records.length - postgres : 0;

  return (
    <div className="page-stack">
      <TopBarContent title="System" lede="Backend connection, where records are stored, and how each photo is processed. Nothing here is configurable from the browser." actions={<button type="button" onClick={() => void check()} className={buttonClass.secondary}>Check again</button>} />

      <Card title="Backend">
        <div className="grid gap-5 sm:grid-cols-3">
          <Field label="API endpoint" mono>
            {API_BASE}
          </Field>
          <div className="min-w-0">
            <span className="field-label">Status</span>
            <span className="mt-1 block">
              {status === null ? <Badge tone="neutral">Checking</Badge> : status.isLive ? <Badge tone="ok">Online</Badge> : <Badge tone="danger">Offline</Badge>}
            </span>
            {checkedAt && <span className="mt-1 block text-xs text-ink-3">Checked {checkedAt.toLocaleTimeString("en-IN")}</span>}
          </div>
          <Field label="Backend version" mono>
            {status?.backendVersion ?? "Not reported"}
          </Field>
        </div>
        {status && !status.isLive && (
          <p className="mt-4 text-sm text-danger">Start the FastAPI backend on port 8000. Inspections cannot be created, loaded or analyzed until it responds.</p>
        )}
      </Card>

      <Card title="Record storage">
        {records ? (
          <div className="grid gap-5 sm:grid-cols-3">
            <Field label="Inspections stored">
              <span className="tabular">{records.length}</span>
            </Field>
            <Field label="In PostgreSQL">
              <span className="tabular">{postgres}</span>
            </Field>
            <Field label="In the API file store">
              <span className="tabular">{fileStore}</span>
            </Field>
          </div>
        ) : (
          <p className="text-sm text-ink-3">Storage counts appear when the API responds.</p>
        )}
        <p className="mt-4 text-xs text-ink-3">The backend writes to PostgreSQL when a database is configured and otherwise to a JSON file store on the API server. Both are real storage; the browser keeps no copy.</p>
      </Card>

      <Card title="Processing pipeline" bodyClass="">
        <ol className="divide-y divide-rule">
          {PIPELINE.map(([title, body]) => (
            <li key={title} className="grid gap-1 px-5 py-3 text-sm sm:grid-cols-[11rem_minmax(0,1fr)] sm:gap-4">
              <span className="font-medium text-ink">{title}</span>
              <span className="text-ink-2">{body}</span>
            </li>
          ))}
        </ol>
      </Card>

    </div>
  );
}
