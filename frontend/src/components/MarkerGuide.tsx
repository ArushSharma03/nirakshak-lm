import { getReferenceMarkerUrl } from "@/lib/api";
import { Icon } from "@/components/ui";

/** Printable reference marker and placement rules, as an inline disclosure. */
export default function MarkerGuide() {
  return (
    <details className="group rounded-xl border border-rule bg-sheet text-sm">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 font-semibold [&::-webkit-details-marker]:hidden">
        <Icon name="marker" className="size-4 text-accent" />
        Reference marker for physical scale
        <span className="ml-auto text-xs font-normal text-ink-3 group-open:hidden">Optional · show</span>
      </summary>
      <div className="grid gap-5 border-t border-rule px-4 py-4 sm:grid-cols-[9rem_minmax(0,1fr)]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={getReferenceMarkerUrl(0)} alt="ArUco 4x4_50 marker ID 0 with white border" className="w-36 border border-rule" />
        <div className="space-y-3 text-ink-2">
          <p>
            ArUco 4x4_50, ID 0. Print it so the black square measures exactly <strong className="text-ink">50 mm</strong>; check with a ruler, because printers rescale.
          </p>
          <ul className="list-disc space-y-1 pl-5">
            <li>Keep the white border around the black square.</li>
            <li>Lay it flat in the same plane as the label panel, not in front of or behind it.</li>
            <li>Shoot from 20–50 cm without glare across the marker.</li>
          </ul>
          <p>Without a marker the photo is still read; only text-height estimates are skipped.</p>
          <a href={getReferenceMarkerUrl(0)} target="_blank" rel="noreferrer" download="nirikshak-aruco-4x4-id0-50mm.png" className="inline-flex items-center gap-1.5 font-semibold text-accent hover:underline">
            Open printable PNG
            <Icon name="external" className="size-3.5" />
          </a>
        </div>
      </div>
    </details>
  );
}
