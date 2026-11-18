"use client";

import { createContext, useContext, type ReactNode } from "react";
import { createPortal } from "react-dom";

export const TopBarTarget = createContext<HTMLDivElement | null>(null);

/** Pages render their title and actions into the shell's single top bar. */
export function TopBarContent({ title, lede, actions }: { title: string; lede?: ReactNode; actions?: ReactNode }) {
  const target = useContext(TopBarTarget);
  if (!target) return null;
  return createPortal(
    <>
      <div className="topbar-title min-w-0 space-y-1">
        <h1 className="break-words text-base font-semibold text-ink">{title}</h1>
        {lede && <p className="max-w-3xl text-xs leading-relaxed text-ink-2">{lede}</p>}
      </div>
      {actions && <div className="topbar-actions flex min-w-0 flex-wrap items-center gap-2">{actions}</div>}
    </>,
    target,
  );
}
