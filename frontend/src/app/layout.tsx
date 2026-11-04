import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/layout/AppShell";

export const metadata: Metadata = {
  title: "Nirikshak-LM — Packaged Commodity Compliance Screening",
  description:
    "An Evidence-Calibrated Multiview System for Explainable Packaged-Commodity Compliance Screening under Legal Metrology Rules",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full h-full font-sans bg-slate-50 text-slate-800 antialiased selection:bg-teal-500 selection:text-white">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
