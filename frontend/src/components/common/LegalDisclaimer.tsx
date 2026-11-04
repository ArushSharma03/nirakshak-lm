import React from "react";

interface LegalDisclaimerProps {
  compact?: boolean;
}

export default function LegalDisclaimer({ compact = false }: LegalDisclaimerProps) {
  if (compact) {
    return (
      <div className="text-[11px] text-slate-500 bg-slate-50 border border-slate-200 rounded px-3 py-1.5 flex items-center space-x-2">
        <span className="font-semibold text-slate-700 shrink-0">Disclaimer:</span>
        <span className="truncate">
          Nirikshak-LM provides preliminary screening and inspection support only. Physical validation required before issuing statutory notices.
        </span>
      </div>
    );
  }

  return (
    <div className="bg-amber-50/70 border border-amber-200/80 rounded-xl p-4 text-xs text-amber-900 flex items-start space-x-3">
      <div className="w-5 h-5 rounded-full bg-amber-200 text-amber-800 flex items-center justify-center shrink-0 font-bold mt-0.5">
        !
      </div>
      <div className="space-y-1">
        <p className="font-semibold text-amber-950">
          Statutory Compliance Notice & Operational Disclaimer
        </p>
        <p className="text-amber-800 leading-relaxed">
          Nirikshak-LM is a decision-support and preliminary screening tool for packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011. 
          Automated findings, OCR readings, and character-height scale estimates are calibrated assistive aids and do not constitute an autonomous legal authority. 
          Physical inspection, sample verification, and formal adjudication by an authorized Inspector of Legal Metrology remain mandatory prior to issuing show-cause notices or penalty actions.
        </p>
      </div>
    </div>
  );
}
