import { useEffect, useRef } from "react";

import { fetchRelationships } from "../api";
import { useApiRequest } from "../use-api-request";
import { RelationshipRow, rowLinkId } from "./relationship-row";

export function RelationshipList({
  selectedId,
}: {
  selectedId: string | null;
}) {
  const { state, retry } = useApiRequest(fetchRelationships, undefined);
  const previousSelectedId = useRef<string | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const focusHeadingWhenSettled = useRef(false);

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

      {state.status === "ok" && state.data.length > 0 && (
        <ul className="divide-y divide-neutral-200 border-t border-neutral-200">
          {state.data.map((relationship) => (
            <RelationshipRow
              key={relationship.id}
              relationship={relationship}
              isSelected={relationship.id === selectedId}
            />
          ))}
        </ul>
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
