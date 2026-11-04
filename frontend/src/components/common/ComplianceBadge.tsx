import React from "react";
import { ComplianceOutcome } from "@/types";

interface ComplianceBadgeProps {
  outcome: ComplianceOutcome | string;
  size?: "sm" | "md" | "lg";
}

export default function ComplianceBadge({ outcome, size = "md" }: ComplianceBadgeProps) {
  let badgeStyle = "bg-gray-100 text-gray-700 border-gray-200";
  let dotStyle = "bg-gray-400";

  if (outcome === "Compliant within Implemented Checks") {
    badgeStyle = "bg-emerald-50 text-emerald-800 border-emerald-200";
    dotStyle = "bg-emerald-500";
  } else if (outcome === "Potential Non-Compliance") {
    badgeStyle = "bg-rose-50 text-rose-800 border-rose-200";
    dotStyle = "bg-rose-500";
  } else if (outcome === "Manual Review Required") {
    badgeStyle = "bg-amber-50 text-amber-800 border-amber-200";
    dotStyle = "bg-amber-500";
  }

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-1 text-xs sm:text-sm font-medium",
    lg: "px-3.5 py-1.5 text-sm sm:text-base font-semibold",
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded-full border ${sizeClasses} ${badgeStyle} shadow-xs font-medium tracking-tight`}
    >
      <span className={`w-2 h-2 rounded-full mr-1.5 shrink-0 ${dotStyle}`} />
      <span>{outcome}</span>
    </span>
  );
}
