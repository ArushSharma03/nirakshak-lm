import Link from "next/link";
import type { ReactNode } from "react";

/* ---------- Icons: one 1.75 stroke on a 20px grid ---------- */

const PATHS = {
  camera: "M3.5 7.5h3l1.5-2h4l1.5 2h3a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1Z M10 14.25a2.75 2.75 0 1 0 0-5.5 2.75 2.75 0 0 0 0 5.5Z",
  upload: "M10 13V3.5 M6.5 7 10 3.5 13.5 7 M3.5 12.5v3a1 1 0 0 0 1 1h11a1 1 0 0 0 1-1v-3",
  arrowRight: "M4 10h12 M11.5 5.5 16 10l-4.5 4.5",
  arrowLeft: "M16 10H4 M8.5 5.5 4 10l4.5 4.5",
  plus: "M10 4v12 M4 10h12",
  print: "M5.5 8V3.5h9V8 M5.5 14H3.5V9a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v5h-2 M5.5 11.5h9v5h-9Z",
  external: "M8.5 4.5h-4v11h11v-4 M11.5 3.5h5v5 M16.5 3.5 9 11",
  check: "M4.5 10.5 8 14l7.5-8",
  alert: "M10 3.5 17 16H3Z M10 8.5v3.5 M10 14.25v.01",
  info: "M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z M10 9v4.5 M10 6.5v.01",
  search: "M8.75 14.5a5.75 5.75 0 1 0 0-11.5 5.75 5.75 0 0 0 0 11.5Z M13 13l3.5 3.5",
  retake: "M4 10a6 6 0 1 0 1.8-4.3 M4 4v3.5h3.5",
  marker: "M3.5 3.5h13v13h-13Z M6.5 6.5h3v3h-3Z M10.5 10.5h3v3h-3Z",
  switch: "M4 7h11.5 M12.5 4l3 3-3 3 M16 13H4.5 M7.5 10l-3 3 3 3",
  close: "M5 5l10 10 M15 5 5 15",
  menu: "M3.5 5.5h13 M3.5 10h13 M3.5 14.5h13",
  home: "M3.5 9 10 3.5 16.5 9 M5 7.75V16a.5.5 0 0 0 .5.5H8.5v-4.5h3v4.5h3a.5.5 0 0 0 .5-.5V7.75",
  history: "M6.5 4h-1a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1V5a1 1 0 0 0-1-1h-1 M7.5 3h5v2.5h-5Z M7.5 9.5h5 M7.5 12.5h5",
  book: "M10 5.5C8.6 4.5 6.7 4 4.5 4v11c2.2 0 4.1.5 5.5 1.5 1.4-1 3.3-1.5 5.5-1.5V4c-2.2 0-4.1.5-5.5 1.5Z M10 5.5v11",
  box: "M10 3 16.5 6.5v7L10 17l-6.5-3.5v-7Z M3.5 6.5 10 10l6.5-3.5 M10 10v7",
  chart: "M3.5 16.5h13 M5.5 13.5v-3 M9 13.5v-7 M12.5 13.5v-5 M16 13.5V4.5",
  report: "M5.5 3h6l3 3v10.5a.5.5 0 0 1-.5.5h-8.5a.5.5 0 0 1-.5-.5v-13A.5.5 0 0 1 5.5 3Z M11.5 3v3h3 M7.5 10.5h5 M7.5 13.5h3.5",
  system: "M3.5 5h13 M3.5 10h13 M3.5 15h13 M7 3.5v3 M13 8.5v3 M9 13.5v3",
  collapse: "M12 5.5 7.5 10l4.5 4.5 M4 4v12",
  expand: "M8 5.5l4.5 4.5L8 14.5 M16 4v12",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, className = "size-4" }: { name: IconName; className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={`shrink-0 ${className}`}>
      <path d={PATHS[name]} />
    </svg>
  );
}

/* ---------- Buttons ---------- */

const BUTTON_BASE =
  "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 min-h-10 px-4";

export const buttonClass = {
  primary: `${BUTTON_BASE} bg-accent text-white hover:bg-accent-deep`,
  secondary: `${BUTTON_BASE} border border-rule-strong bg-sheet text-ink hover:bg-ground`,
  quiet: `${BUTTON_BASE} px-2.5 text-accent hover:bg-accent-wash`,
  danger: `${BUTTON_BASE} border border-danger/30 bg-sheet text-danger hover:bg-danger-wash`,
};

export function ButtonLink({ href, children, variant = "primary" }: { href: string; children: ReactNode; variant?: keyof typeof buttonClass }) {
  return (
    <Link href={href} className={buttonClass[variant]}>
      {children}
    </Link>
  );
}

/* ---------- Status labels ---------- */

export type Tone = "warn" | "danger" | "ok" | "neutral" | "accent";

const TONE: Record<Tone, string> = {
  warn: "text-warn",
  danger: "text-danger",
  ok: "text-ok",
  neutral: "text-ink-2",
  accent: "text-accent",
};

export function Badge({ tone, children, large = false }: { tone: Tone; children: ReactNode; large?: boolean }) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap font-medium ${TONE[tone]} ${
        large ? "text-sm" : "text-xs"
      }`}
    >
      {children}
    </span>
  );
}

export function qualityTone(status: string | undefined): Tone {
  if (status === "Pass") return "ok";
  if (status === "Warning") return "warn";
  if (status === "Retake Recommended") return "danger";
  return "neutral";
}

/* ---------- Surfaces ---------- */

export function Card({ title, aside, children, className = "", bodyClass = "p-5" }: { title?: ReactNode; aside?: ReactNode; children: ReactNode; className?: string; bodyClass?: string }) {
  return (
    <section className={`min-w-0 overflow-hidden rounded-md border border-rule bg-sheet ${className}`}>
      {(title || aside) && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule px-5 py-3.5">
          {title && <h2 className="text-sm font-semibold text-ink">{title}</h2>}
          {aside}
        </div>
      )}
      <div className={bodyClass}>{children}</div>
    </section>
  );
}

/* ---------- Notices ---------- */

export function Notice({ tone = "warn", title, children, action }: { tone?: Tone; title: string; children?: ReactNode; action?: ReactNode }) {
  const border = { warn: "border-amber-200", danger: "border-rose-200", ok: "border-emerald-200", neutral: "border-rule", accent: "border-teal-200" }[tone];
  const text = { warn: "text-warn", danger: "text-danger", ok: "text-ok", neutral: "text-ink-2", accent: "text-accent" }[tone];
  const bg = { warn: "bg-warn-wash", danger: "bg-danger-wash", ok: "bg-ok-wash", neutral: "bg-sheet", accent: "bg-accent-wash" }[tone];
  return (
    <div role={tone === "danger" ? "alert" : "status"} className={`flex flex-col gap-3 rounded-xl border px-4 py-3 text-sm sm:flex-row sm:items-start sm:justify-between ${border} ${bg}`}>
      <div className="flex gap-2.5">
        <Icon name={tone === "neutral" || tone === "accent" ? "info" : "alert"} className={`mt-0.5 size-4 ${text}`} />
        <div className="space-y-1">
          <p className={`font-semibold ${text}`}>{title}</p>
          {children && <div className="text-ink-2">{children}</div>}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function Loading({ label }: { label: string }) {
  return (
    <p role="status" className="flex items-center gap-2.5 py-8 text-sm text-ink-2">
      <span className="size-3.5 animate-spin rounded-full border-2 border-rule border-t-accent motion-reduce:animate-none" />
      {label}
    </p>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-rule-strong bg-sheet px-6 py-10 text-center">
      <p className="font-semibold text-ink">{title}</p>
      {children && <p className="mx-auto mt-1 max-w-md text-sm text-ink-2">{children}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

export function Field({ label, children, mono = false }: { label: string; children: ReactNode; mono?: boolean }) {
  return (
    <div className="min-w-0">
      <span className="field-label">{label}</span>
      <span className={`mt-0.5 block break-words text-sm text-ink ${mono ? "serial" : ""}`}>{children}</span>
    </div>
  );
}

/* ---------- Data helpers ---------- */

/** Single-hue horizontal meter with its value printed beside it. */
export function Meter({ value, max, tone = "accent" }: { value: number; max: number; tone?: "accent" | "warn" | "neutral" }) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  const fill = tone === "warn" ? "bg-amber-500" : tone === "neutral" ? "bg-slate-400" : "bg-accent";
  return (
    <span className="block h-1.5 w-full overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
      <span className={`block h-full rounded-full ${fill}`} style={{ width: `${pct}%` }} />
    </span>
  );
}

export const inputClass =
  "mt-1.5 block w-full min-h-10 rounded-lg border border-rule-strong bg-sheet px-3 py-2 text-sm text-ink placeholder:text-ink-3 focus:border-accent";
