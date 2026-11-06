import ReportsHubContent from "@/components/ReportsHubContent";

export default async function ReportsHubPage({ searchParams }: {
  searchParams: Promise<{ id?: string | string[] }>;
}) {
  const { id } = await searchParams;
  return <ReportsHubContent inspectionId={typeof id === "string" ? id : null} />;
}
