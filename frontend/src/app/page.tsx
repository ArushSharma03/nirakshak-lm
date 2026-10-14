import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-gray-50">
      <div className="max-w-2xl text-center space-y-6">
        <h1 className="text-4xl font-bold text-gray-900">
          Nirikshak-LM
        </h1>
        <p className="text-lg text-gray-600">
          An Evidence-Calibrated Multiview System for Explainable
          Packaged-Commodity Compliance Screening
        </p>
        <Link
          href="/inspect"
          className="inline-block rounded-lg bg-blue-600 px-6 py-3 text-white font-medium hover:bg-blue-700 transition-colors"
        >
          Start New Inspection
        </Link>
        <p className="text-sm text-gray-500">
          B.Tech CSE Minor Project (COM-711) — Group 27
        </p>
      </div>
    </main>
  );
}
