import Link from "next/link";

import { formatDate } from "@/lib/dates";

import {
  CUSTOMER_STATUS_LABEL,
  INTERACTION_TYPE_LABEL,
  type LatestInteraction,
  type RelationshipSummary,
} from "../types";

export function relationshipPath(id: string): string {
  return `/relationships/${encodeURIComponent(id)}`;
}

export function rowLinkId(id: string): string {
  return `relationship-${id}`;
}

/**
 * "29 Aug 2026 · Note", or "20 Aug 2026 · 2 interactions: Email, Note" when several
 * interactions share the latest date. The types are a set in a stable order; nothing
 * here says which happened first.
 */
export function latestInteractionText(latest: LatestInteraction | null): string {
  if (latest === null) return "No interactions yet";
  const date = formatDate(latest.date);
  const types = latest.types
    .map((type) => INTERACTION_TYPE_LABEL[type])
    .join(", ");
  return latest.count === 1
    ? `${date} · ${types}`
    : // A no-break space keeps the count on the same line as "interactions".
      `${date} · ${latest.count}\u00a0interactions: ${types}`;
}

export function RelationshipRow({
  relationship,
  isSelected,
}: {
  relationship: RelationshipSummary;
  isSelected: boolean;
}) {
  const linkId = rowLinkId(relationship.id);
  return (
    <li>
      <Link
        href={relationshipPath(relationship.id)}
        id={linkId}
        aria-labelledby={`${linkId}-name`}
        aria-describedby={`${linkId}-status ${linkId}-latest`}
        aria-current={isSelected ? "page" : undefined}
        className="block px-4 py-3 hover:bg-neutral-50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-blue-700 aria-[current=page]:bg-neutral-100"
      >
        <span className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <span
            id={`${linkId}-name`}
            className="font-medium text-neutral-900 [overflow-wrap:anywhere]"
          >
            {relationship.name}
          </span>
          <span id={`${linkId}-status`} className="text-sm text-neutral-600">
            {CUSTOMER_STATUS_LABEL[relationship.status]}
          </span>
        </span>
        <span
          id={`${linkId}-latest`}
          className="mt-1 block text-sm text-neutral-600"
        >
          Latest interaction:{" "}
          {latestInteractionText(relationship.latest_interaction)}
        </span>
      </Link>
    </li>
  );
}
