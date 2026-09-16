import Link from "next/link";

import { formatDate } from "@/lib/dates";

import type { RowAssessment } from "../assessments";
import {
  ASSESSMENT_STATE_LABEL,
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

// A neutral explanation in place of a state (UX spec, section 5).
const UNAVAILABLE_TEXT: Record<
  Extract<RowAssessment, { kind: "unavailable" }>["cause"],
  string
> = {
  no_interactions: "No interaction history",
  insufficient_evidence: "Not enough clear history to assess",
  temporary: "Temporary problem — assessment could not be produced",
  unknown: "Cause not known",
};

// Colour only supports the text label; it never carries the state alone.
const STATE_LABEL_CLASS = {
  action_needed: "border-blue-300 bg-blue-50 text-blue-900",
  waiting: "border-neutral-300 bg-neutral-50 text-neutral-800",
  no_action_needed: "border-green-300 bg-green-50 text-green-900",
} as const;

export function StateLabel({
  state,
}: {
  state: keyof typeof STATE_LABEL_CLASS;
}) {
  return (
    <span
      className={`inline-block rounded border px-1.5 text-sm font-medium whitespace-nowrap ${STATE_LABEL_CLASS[state]}`}
    >
      {ASSESSMENT_STATE_LABEL[state]}
    </span>
  );
}

function AssessmentText({ assessment }: { assessment: RowAssessment }) {
  switch (assessment.kind) {
    case "assessed":
      return (
        <>
          <StateLabel state={assessment.state} />
          <span className="text-neutral-900"> — {assessment.reason}</span>
        </>
      );
    case "unavailable":
      return (
        <span className="text-neutral-700">
          {UNAVAILABLE_TEXT[assessment.cause]}
        </span>
      );
    case "pending":
      // "Assessing…" only while this relationship's request is in flight.
      return (
        <span className="text-neutral-700">
          {assessment.active ? "Assessing…" : "Waiting to be assessed"}
        </span>
      );
  }
}

export function RelationshipRow({
  relationship,
  assessment,
  isSelected,
}: {
  relationship: RelationshipSummary;
  assessment: RowAssessment;
  isSelected: boolean;
}) {
  const linkId = rowLinkId(relationship.id);
  return (
    <li>
      <Link
        href={relationshipPath(relationship.id)}
        id={linkId}
        data-row-link=""
        aria-labelledby={`${linkId}-name`}
        aria-describedby={`${linkId}-status ${linkId}-assessment ${linkId}-latest`}
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
          id={`${linkId}-assessment`}
          className="mt-1 block text-sm [overflow-wrap:anywhere]"
        >
          <AssessmentText assessment={assessment} />
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
