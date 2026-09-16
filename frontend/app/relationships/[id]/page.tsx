import { RelationshipDetail } from "@/features/relationships/components/relationship-detail";

export default async function RelationshipPage({
  params,
}: PageProps<"/relationships/[id]">) {
  const { id } = await params;
  return <RelationshipDetail id={id} />;
}
