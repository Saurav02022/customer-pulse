import { useEffect, useLayoutEffect, useRef, type FocusEvent } from "react";

import { fetchRelationships } from "../api";
import {
  rowAssessment,
  useAssessments,
  type RowAssessment,
} from "../assessments";
import {
  ASSESSMENT_STATES,
  ASSESSMENT_STATE_LABEL,
  ASSESSMENT_STATE_MEANING,
  type AssessmentState,
  type RelationshipSummary,
} from "../types";
import { useApiRequest } from "../use-api-request";
import { RelationshipRow, rowLinkId } from "./relationship-row";

type Row = { relationship: RelationshipSummary; assessment: RowAssessment };

type Sections = Record<AssessmentState, Row[]> & {
  assessing: Row[];
  unavailable: Row[];
};

const UNAVAILABLE_MEANING =
  "Customer Pulse could not produce a trustworthy assessment for these relationships. Their facts and history are still available.";

function byName(a: Row, b: Row): number {
  return (
    a.relationship.name.localeCompare(b.relationship.name, "en", {
      sensitivity: "base",
    }) || a.relationship.id.localeCompare(b.relationship.id)
  );
}

/**
 * Groups rows by what their assessment says. Order comes only from the state, then
 * the name; dates never sort or rank. Rows still being assessed keep the API order.
 */
export function sectionRows(rows: Row[]): Sections {
  const sections: Sections = {
    action_needed: [],
    waiting: [],
    no_action_needed: [],
    assessing: [],
    unavailable: [],
  };
  for (const row of rows) {
    const { assessment } = row;
    if (assessment.kind === "assessed") sections[assessment.state].push(row);
    else if (assessment.kind === "unavailable") sections.unavailable.push(row);
    else sections.assessing.push(row);
  }
  for (const state of ASSESSMENT_STATES) sections[state].sort(byName);
  sections.unavailable.sort(byName);
  return sections;
}

function sectionId(key: string): string {
  return `relationships-${key}`;
}

const countLinkClass =
  "text-blue-800 underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700";

function CountLine({ sections }: { sections: Sections }) {
  const unavailable = sections.unavailable.length;
  return (
    <p className="px-4 pb-3 text-sm text-neutral-700">
      {ASSESSMENT_STATES.map((state, index) => {
        const count = sections[state].length;
        const text = `${count} ${ASSESSMENT_STATE_LABEL[state]}`;
        return (
          <span key={state}>
            {index > 0 && " · "}
            {count > 0 ? (
              <a href={`#${sectionId(state)}`} className={countLinkClass}>
                {text}
              </a>
            ) : (
              text
            )}
          </span>
        );
      })}
      {unavailable > 0 && (
        <>
          {" — "}
          <a href={`#${sectionId("unavailable")}`} className={countLinkClass}>
            {`${unavailable} assessment unavailable`}
          </a>
        </>
      )}
    </p>
  );
}

function RowSection({
  id,
  heading,
  meaning,
  rows,
  headingLevel,
  selectedId,
  muted,
}: {
  id: string;
  heading: string;
  meaning?: string;
  rows: Row[];
  headingLevel: "h2" | "h3";
  selectedId: string | null;
  muted?: boolean;
}) {
  const Heading = headingLevel;
  const headingId = sectionId(id);
  return (
    <section
      aria-labelledby={headingId}
      className="border-t border-neutral-200"
    >
      <div className={`px-4 pt-4 pb-2 ${muted ? "bg-neutral-50" : ""}`}>
        {/* The count line links here; tabIndex lets the jump move keyboard focus. */}
        <Heading
          id={headingId}
          tabIndex={-1}
          className={`scroll-mt-2 font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 ${muted ? "text-neutral-700" : "text-neutral-900"}`}
        >
          {heading}
          <span className="font-normal text-neutral-600"> · {rows.length}</span>
        </Heading>
        {meaning && (
          <p className="mt-0.5 text-sm text-neutral-600">{meaning}</p>
        )}
      </div>
      <ul className="divide-y divide-neutral-200 border-t border-neutral-200">
        {rows.map(({ relationship, assessment }) => (
          <RelationshipRow
            key={relationship.id}
            relationship={relationship}
            assessment={assessment}
            isSelected={relationship.id === selectedId}
          />
        ))}
      </ul>
    </section>
  );
}

/**
 * Keeps keyboard focus on a row whose link was re-created in another section when its
 * assessment arrived. Only a link that left the page is followed: if the owner moved
 * focus away themselves, nothing is focused.
 */
function useKeepRowFocus() {
  const lastFocused = useRef<HTMLElement | null>(null);

  useLayoutEffect(() => {
    const node = lastFocused.current;
    if (node === null || node.isConnected) return;
    const active = document.activeElement;
    if (active !== null && active !== document.body) return;
    // preventScroll: a result arriving never moves the page (UX spec, section 5).
    document.getElementById(node.id)?.focus({ preventScroll: true });
  });

  return {
    onFocus(event: FocusEvent<HTMLElement>) {
      if (event.target.dataset.rowLink !== undefined) {
        lastFocused.current = event.target;
      }
    },
    onBlur(event: FocusEvent<HTMLElement>) {
      const node = event.target;
      if (event.relatedTarget !== null) {
        lastFocused.current = null;
        return;
      }
      // Focus went nowhere: either the owner clicked away (the link is still on the
      // page after this commit) or the link was removed (it is not).
      queueMicrotask(() => {
        if (node.isConnected && lastFocused.current === node) {
          lastFocused.current = null;
        }
      });
    },
  };
}

export function RelationshipList({
  selectedId,
}: {
  selectedId: string | null;
}) {
  const { state, retry } = useApiRequest(fetchRelationships, undefined);
  const { entries, addListed } = useAssessments();
  const previousSelectedId = useRef<string | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const focusHeadingWhenSettled = useRef(false);
  const keepRowFocus = useKeepRowFocus();

  const listed = state.status === "ok" ? state.data : null;

  // Facts show at once; assessments are then requested for rows without one.
  useEffect(() => {
    if (listed !== null) addListed(listed);
  }, [listed, addListed]);

  // Leaving a relationship returns focus to the row that opened it (UX spec, section
  // 12). Nothing happens on first load or when no row was opened.
  useEffect(() => {
    const previous = previousSelectedId.current;
    previousSelectedId.current = selectedId;
    if (selectedId === null && previous !== null) {
      document.getElementById(rowLinkId(previous))?.focus();
    }
  }, [selectedId]);

  // "Try again" disappears when the retry settles, so focus moves to the heading
  // instead of falling back to the page.
  useEffect(() => {
    if (state.status !== "loading" && focusHeadingWhenSettled.current) {
      focusHeadingWhenSettled.current = false;
      headingRef.current?.focus();
    }
  }, [state.status]);

  // The list is the view's main heading only while no relationship is open.
  const Heading = selectedId === null ? "h1" : "h2";
  const sectionHeading = selectedId === null ? "h2" : "h3";

  const sections =
    listed === null
      ? null
      : sectionRows(
          listed.map((relationship) => ({
            relationship,
            assessment: rowAssessment(
              relationship.assessment,
              entries.get(relationship.id),
            ),
          })),
        );
  const anyRequested = Array.from(entries.values()).some(
    (entry) => entry.requested,
  );
  // One steady message while work runs, one when it ends: never one per row.
  const announcement =
    sections === null
      ? ""
      : sections.assessing.length > 0
        ? "Assessing relationships…"
        : anyRequested
          ? "Assessments finished."
          : "";

  return (
    <section aria-labelledby="relationships-heading">
      <Heading
        id="relationships-heading"
        ref={headingRef}
        tabIndex={-1}
        className="px-4 py-3 text-lg font-semibold text-neutral-900 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-blue-700"
      >
        Relationships
      </Heading>

      {state.status === "loading" && (
        <p role="status" className="px-4 py-3 text-neutral-600">
          Loading relationships…
        </p>
      )}

      {state.status === "ok" && state.data.length === 0 && (
        <p className="px-4 py-3 text-neutral-600">
          There are no relationships to show.
        </p>
      )}

      {sections !== null && listed !== null && listed.length > 0 && (
        <div onFocus={keepRowFocus.onFocus} onBlur={keepRowFocus.onBlur}>
          <CountLine sections={sections} />
          <p role="status" className="sr-only">
            {announcement}
          </p>
          {ASSESSMENT_STATES.map(
            (state) =>
              sections[state].length > 0 && (
                <RowSection
                  key={state}
                  id={state}
                  heading={ASSESSMENT_STATE_LABEL[state]}
                  meaning={ASSESSMENT_STATE_MEANING[state]}
                  rows={sections[state]}
                  headingLevel={sectionHeading}
                  selectedId={selectedId}
                />
              ),
          )}
          {sections.assessing.length > 0 && (
            <RowSection
              id="assessing"
              heading="Assessing…"
              rows={sections.assessing}
              headingLevel={sectionHeading}
              selectedId={selectedId}
              muted
            />
          )}
          {sections.unavailable.length > 0 && (
            <RowSection
              id="unavailable"
              heading="Assessment unavailable"
              meaning={UNAVAILABLE_MEANING}
              rows={sections.unavailable}
              headingLevel={sectionHeading}
              selectedId={selectedId}
              muted
            />
          )}
        </div>
      )}

      {(state.status === "failed" || state.status === "not_found") && (
        <div className="px-4 py-3">
          <p role="alert" className="text-neutral-900">
            Customer Pulse could not load your relationships.
          </p>
          <button
            type="button"
            onClick={() => {
              focusHeadingWhenSettled.current = true;
              retry();
            }}
            className="mt-3 rounded border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-900 hover:bg-neutral-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
          >
            Try again
          </button>
        </div>
      )}
    </section>
  );
}
