import { useRef, type ReactNode } from "react";

import type { AssessmentFailure } from "../api";
import type { DetailAssessment } from "../assessments";
import {
  ASSESSMENT_STATE_MEANING,
  type BusinessAssessment,
  type Claim,
  type Contact,
  type Interaction,
  type RelationshipDetail,
  type UnavailableCause,
} from "../types";
import { Evidence, type ShowInHistory } from "./evidence";
import { StateLabel } from "./relationship-row";

// Assessment unavailable messages (UX spec, section 7). No state, reason, summary, open
// items, suggestion or "Based on" is shown with them.
const UNAVAILABLE_MESSAGE: Record<
  UnavailableCause | AssessmentFailure,
  string
> = {
  no_interactions: "There is no interaction history to assess.",
  insufficient_evidence:
    "The history does not give enough clear information for a trustworthy assessment. Read the history below to decide.",
  temporary:
    "The assessment could not be produced because of a temporary problem. The facts and history below are not affected.",
  unknown:
    "Customer Pulse could not produce a trustworthy assessment. Read the history below to decide.",
};

const SUGGESTION_NOTE =
  "A suggestion only. Customer Pulse does not do this for you.";

const buttonClass =
  "rounded border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-900 hover:bg-neutral-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700";

function claimsOf(assessment: BusinessAssessment): Claim[] {
  const claims: Claim[] = [
    assessment.reason,
    assessment.summary,
    ...assessment.open_items,
  ];
  if (assessment.state === "waiting") claims.push(assessment.waiting_for);
  if (assessment.state !== "no_action_needed" && assessment.next_action) {
    claims.push(assessment.next_action);
  }
  return claims;
}

/**
 * True when every cited interaction is a non-empty note of this relationship and every
 * open-item contact is one of its contacts. Otherwise the assessment cannot be traced
 * and is shown as unavailable, never partly and never with a guessed name.
 */
function isTraceable(
  assessment: BusinessAssessment,
  relationship: RelationshipDetail,
): boolean {
  const notes = new Map(relationship.interactions.map((i) => [i.id, i.notes]));
  const contactIds = new Set(relationship.contacts.map((c) => c.id));
  return (
    claimsOf(assessment).every((claim) =>
      claim.evidence.every((id) => (notes.get(id) ?? "").trim() !== ""),
    ) &&
    assessment.open_items.every((item) =>
      item.contact_ids.every((id) => contactIds.has(id)),
    )
  );
}

type EvidenceContext = {
  interactions: Interaction[];
  contactsById: ReadonlyMap<string, Contact>;
  onShowInHistory: ShowInHistory;
};

function Part({
  title,
  claim,
  part,
  note,
  context,
}: {
  title: string;
  claim: Claim;
  part: string;
  note?: string;
  context: EvidenceContext;
}) {
  return (
    <div className="mt-4">
      <h3 className="text-sm font-semibold text-neutral-700">{title}</h3>
      <p className="mt-0.5 text-neutral-900 [overflow-wrap:anywhere]">
        {claim.text}
      </p>
      {note && <p className="mt-0.5 text-sm text-neutral-600">{note}</p>}
      <Evidence ids={claim.evidence} part={part} {...context} />
    </div>
  );
}

function Assessed({
  assessment,
  context,
}: {
  assessment: BusinessAssessment;
  context: EvidenceContext;
}) {
  const contactText = (ids: string[]) =>
    ids
      .map((id) => {
        const contact = context.contactsById.get(id);
        return contact ? `${contact.name}, ${contact.role}` : "";
      })
      .join("; ");

  return (
    <>
      <p className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <StateLabel state={assessment.state} />
        <span className="text-sm text-neutral-700">
          {ASSESSMENT_STATE_MEANING[assessment.state]}
        </span>
      </p>
      <Part
        title="Reason"
        claim={assessment.reason}
        part="the reason"
        context={context}
      />
      <Part
        title="Summary"
        claim={assessment.summary}
        part="the summary"
        context={context}
      />
      <div className="mt-4">
        <h3 className="text-sm font-semibold text-neutral-700">Open items</h3>
        {assessment.open_items.length === 0 ? (
          <p className="mt-0.5 text-neutral-700">No open items.</p>
        ) : (
          <ul className="mt-1 space-y-3">
            {assessment.open_items.map((item, index) => (
              <li key={index}>
                <p className="text-neutral-900 [overflow-wrap:anywhere]">
                  {item.text}
                </p>
                <p className="text-sm text-neutral-600 [overflow-wrap:anywhere]">
                  Contact: {contactText(item.contact_ids)}
                </p>
                <Evidence
                  ids={item.evidence}
                  part={`open item ${index + 1}`}
                  {...context}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
      {assessment.state === "action_needed" && (
        <Part
          title="Suggested next action"
          claim={assessment.next_action}
          part="the suggested next action"
          note={SUGGESTION_NOTE}
          context={context}
        />
      )}
      {assessment.state === "waiting" && (
        <>
          <Part
            title="Waiting for"
            claim={assessment.waiting_for}
            part="what this relationship is waiting for"
            context={context}
          />
          {assessment.next_action && (
            <Part
              title="Suggested next action, once that happens"
              claim={assessment.next_action}
              part="the suggested next action"
              note={SUGGESTION_NOTE}
              context={context}
            />
          )}
        </>
      )}
      {assessment.state === "no_action_needed" && (
        <div className="mt-4">
          <h3 className="text-sm font-semibold text-neutral-700">Next step</h3>
          <p className="mt-0.5 text-neutral-700">No next action suggested.</p>
        </div>
      )}
    </>
  );
}

function statusText(assessment: DetailAssessment, traceable: boolean): string {
  switch (assessment.kind) {
    case "pending":
      return assessment.active
        ? "Assessing this relationship…"
        : "Waiting to be assessed.";
    case "failed":
      return "Assessment unavailable.";
    case "ready":
      return assessment.assessment.status === "assessed" && traceable
        ? "Assessment ready."
        : "Assessment unavailable.";
  }
}

export function AssessmentSection({
  relationship,
  assessment,
  onRetry,
  onShowInHistory,
}: {
  relationship: RelationshipDetail;
  assessment: DetailAssessment;
  onRetry: () => void;
  onShowInHistory: ShowInHistory;
}) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const business =
    assessment.kind === "ready" && assessment.assessment.status === "assessed"
      ? assessment.assessment
      : null;
  const traceable = business === null || isTraceable(business, relationship);

  let body: ReactNode;
  if (assessment.kind === "pending") {
    // The status line below announces this text; hide the copy from screen readers.
    body = (
      <p aria-hidden="true" className="text-neutral-700">
        {statusText(assessment, true)}
      </p>
    );
  } else if (assessment.kind === "failed") {
    body = (
      <>
        <p className="text-neutral-900">
          {UNAVAILABLE_MESSAGE[assessment.failure]}
        </p>
        {assessment.failure === "temporary" && (
          <p className="mt-3">
            <button
              type="button"
              onClick={() => {
                onRetry();
                // The button goes away, so keep focus in the assessment area.
                headingRef.current?.focus();
              }}
              className={buttonClass}
            >
              Try again
            </button>
          </p>
        )}
      </>
    );
  } else if (assessment.assessment.status === "unavailable") {
    body = (
      <p className="text-neutral-900">
        {UNAVAILABLE_MESSAGE[assessment.assessment.cause]}
      </p>
    );
  } else if (business === null || !traceable) {
    body = <p className="text-neutral-900">{UNAVAILABLE_MESSAGE.unknown}</p>;
  } else {
    body = (
      <Assessed
        assessment={business}
        context={{
          interactions: relationship.interactions,
          contactsById: new Map(relationship.contacts.map((c) => [c.id, c])),
          onShowInHistory,
        }}
      />
    );
  }

  return (
    <section
      aria-labelledby="assessment-heading"
      className="mt-6 rounded-lg border border-neutral-200 bg-neutral-50 p-4 sm:p-5"
    >
      <h2
        id="assessment-heading"
        ref={headingRef}
        tabIndex={-1}
        className="text-lg font-semibold text-neutral-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
      >
        Assessment
      </h2>
      <p className="text-sm text-neutral-600">
        AI assessment, based on this relationship’s interaction history
      </p>
      <p role="status" className="sr-only">
        {statusText(assessment, traceable)}
      </p>
      <div className="mt-3">{body}</div>
    </section>
  );
}
