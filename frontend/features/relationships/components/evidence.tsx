import { useRef } from "react";

import { formatDate } from "@/lib/dates";

import {
  INTERACTION_TYPE_LABEL,
  type Contact,
  type Interaction,
} from "../types";
import { groupByDate } from "./interaction-history";

export type ShowInHistory = (
  interactionId: string,
  returnTo: HTMLElement | null,
) => void;

const controlClass =
  "inline-block rounded py-1 text-blue-800 underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700";

/**
 * "Based on N interactions", closed at first (UX spec, section 8). Sources are the
 * original records of this relationship, in history order and grouped by date, so
 * nothing suggests which of several same-date interactions came first.
 */
export function Evidence({
  ids,
  part,
  interactions,
  contactsById,
  onShowInHistory,
}: {
  ids: string[];
  /** What the sources support, for screen readers: "the reason". */
  part: string;
  /** The loaded history, newest date first. */
  interactions: Interaction[];
  contactsById: ReadonlyMap<string, Contact>;
  onShowInHistory: ShowInHistory;
}) {
  const summaryRef = useRef<HTMLElement>(null);
  const cited = new Set(ids);
  // Filtering the history keeps each interaction once, however often it is cited.
  const sources = interactions.filter((interaction) =>
    cited.has(interaction.id),
  );
  const count = sources.length;

  return (
    <details className="mt-1 text-sm">
      <summary
        ref={summaryRef}
        className={`w-fit cursor-pointer ${controlClass}`}
      >
        {`Based on ${count} ${count === 1 ? "interaction" : "interactions"}`}
        <span className="sr-only">, for {part}</span>
      </summary>
      <ul className="mt-2 space-y-3 border-l-2 border-neutral-300 pl-3">
        {groupByDate(sources).map((group) => (
          <li key={group.date}>
            <p className="font-medium text-neutral-900">
              {formatDate(group.date)}
              {group.interactions.length > 1 && (
                <span className="font-normal text-neutral-600">
                  {` — ${group.interactions.length} interactions — order within this date is not known`}
                </span>
              )}
            </p>
            <ul className="mt-1 space-y-2">
              {group.interactions.map((interaction) => {
                const type = INTERACTION_TYPE_LABEL[interaction.type];
                const contact = contactsById.get(interaction.contact_id);
                const which = `${type}, ${formatDate(interaction.occurred_at)}`;
                return (
                  <li key={interaction.id}>
                    <p className="text-neutral-700 [overflow-wrap:anywhere]">
                      {type}
                      {contact && ` · ${contact.name}`}
                    </p>
                    <div className="mt-0.5 flex flex-wrap items-start gap-x-4 gap-y-1">
                      <details className="min-w-0 basis-full">
                        <summary
                          className={`w-fit cursor-pointer ${controlClass}`}
                        >
                          Show note<span className="sr-only">: {which}</span>
                        </summary>
                        <p className="mt-1 whitespace-pre-line text-neutral-900 [overflow-wrap:anywhere]">
                          {interaction.notes}
                        </p>
                      </details>
                      <button
                        type="button"
                        onClick={() =>
                          onShowInHistory(interaction.id, summaryRef.current)
                        }
                        className={controlClass}
                      >
                        Show in history
                        <span className="sr-only">: {which}</span>
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          </li>
        ))}
      </ul>
    </details>
  );
}
