"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { formatDate } from "@/lib/dates";

import { fetchRelationship } from "../api";
import { detailAssessment, useAssessments } from "../assessments";
import { CUSTOMER_STATUS_LABEL } from "../types";
import { useApiRequest } from "../use-api-request";
import { AssessmentSection } from "./assessment-section";
import { ContactsSection } from "./contacts-section";
import type { ShowInHistory } from "./evidence";
import { InteractionHistory, historyItemId } from "./interaction-history";

const BASE_TITLE = "Customer Pulse";

const headingClass =
  "text-2xl font-semibold text-neutral-900 [overflow-wrap:anywhere] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-700";
const buttonClass =
  "rounded border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-900 hover:bg-neutral-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700";
const linkClass =
  "inline-block py-1 text-sm text-blue-800 underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700";

function BackToListLink({ narrowOnly }: { narrowOnly: boolean }) {
  return (
    <p className={narrowOnly ? "mb-4 md:hidden" : "mt-4"}>
      <Link href="/" className={linkClass}>
        Back to all relationships
      </Link>
    </p>
  );
}

type Shown = {
  relationshipId: string;
  interactionId: string;
  returnTo: HTMLElement | null;
};

export function RelationshipDetail({ id }: { id: string }) {
  const { state, retry } = useApiRequest(fetchRelationship, id);
  const assessments = useAssessments();
  const { requestFull } = assessments;
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [shown, setShown] = useState<Shown | null>(null);
  const name = state.status === "ok" ? state.data.name : null;
  const factsLoaded = state.status === "ok";

  // Facts never wait for the assessment. Once they show, the shared pool is asked for
  // the full assessment; it reuses what it already has or is already doing.
  useEffect(() => {
    if (factsLoaded) requestFull(id);
  }, [factsLoaded, id, requestFull]);

  // "Show in history" moves focus to the interaction it names.
  useEffect(() => {
    if (shown)
      document.getElementById(historyItemId(shown.interactionId))?.focus();
  }, [shown]);

  // Opening a relationship moves focus to its heading once the outcome is known
  // (UX spec, section 12). Each outcome renders its own heading on the same ref.
  useEffect(() => {
    if (state.status !== "loading") headingRef.current?.focus();
  }, [state.status]);

  // The page title names the relationship while it is open. Metadata cannot do this
  // because the facts are fetched in the browser.
  useEffect(() => {
    if (name === null) return;
    document.title = `${name} · ${BASE_TITLE}`;
    return () => {
      document.title = BASE_TITLE;
    };
  }, [name]);

  if (state.status === "loading") {
    return (
      <p role="status" className="text-neutral-600">
        Loading relationship…
      </p>
    );
  }

  if (state.status === "not_found") {
    return (
      <div>
        <h1 ref={headingRef} tabIndex={-1} className={headingClass}>
          This relationship could not be found.
        </h1>
        <BackToListLink narrowOnly={false} />
      </div>
    );
  }

  if (state.status === "failed") {
    return (
      <div>
        <h1 ref={headingRef} tabIndex={-1} className={headingClass}>
          Customer Pulse could not load this relationship.
        </h1>
        <p className="mt-4">
          <button type="button" onClick={retry} className={buttonClass}>
            Try again
          </button>
        </p>
        <BackToListLink narrowOnly={false} />
      </div>
    );
  }

  const relationship = state.data;
  const shownId =
    shown?.relationshipId === relationship.id ? shown.interactionId : null;
  const showInHistory: ShowInHistory = (interactionId, returnTo) =>
    setShown({ relationshipId: relationship.id, interactionId, returnTo });
  const backToAssessment = () => {
    const target = shown?.returnTo;
    setShown(null);
    target?.focus();
  };

  return (
    <article aria-labelledby="relationship-heading" className="max-w-2xl">
      <BackToListLink narrowOnly />
      <h1
        id="relationship-heading"
        ref={headingRef}
        tabIndex={-1}
        className={headingClass}
      >
        {relationship.name}
      </h1>
      <p className="mt-1 text-neutral-600">
        {`${CUSTOMER_STATUS_LABEL[relationship.status]} · Record created ${formatDate(relationship.created_at)}`}
      </p>
      <AssessmentSection
        relationship={relationship}
        assessment={detailAssessment(assessments.entries.get(relationship.id))}
        onRetry={() => assessments.retry(relationship.id)}
        onShowInHistory={showInHistory}
      />
      <ContactsSection contacts={relationship.contacts} />
      <InteractionHistory
        interactions={relationship.interactions}
        contacts={relationship.contacts}
        shownId={shownId}
        onBackToAssessment={backToAssessment}
      />
    </article>
  );
}
