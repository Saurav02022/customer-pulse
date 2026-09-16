import { formatDate } from "@/lib/dates";

import {
  INTERACTION_TYPE_LABEL,
  type Contact,
  type Interaction,
} from "../types";

type DateGroup = { date: string; interactions: Interaction[] };

/**
 * Puts each date under one heading, keeping the API's order: newest date first, and a
 * stable display order within a date that means nothing. Nothing here reorders.
 */
export function groupByDate(interactions: Interaction[]): DateGroup[] {
  const byDate = new Map<string, Interaction[]>();
  for (const interaction of interactions) {
    const group = byDate.get(interaction.occurred_at);
    if (group) group.push(interaction);
    else byDate.set(interaction.occurred_at, [interaction]);
  }
  return Array.from(byDate, ([date, group]) => ({ date, interactions: group }));
}

function contactText(contact: Contact | undefined): string {
  return contact ? `${contact.name}, ${contact.role}` : "not recorded";
}

export function InteractionHistory({
  interactions,
  contacts,
}: {
  interactions: Interaction[];
  contacts: Contact[];
}) {
  const contactsById = new Map(contacts.map((contact) => [contact.id, contact]));
  const groups = groupByDate(interactions);

  return (
    <section aria-labelledby="history-heading" className="mt-8">
      <h2 id="history-heading" className="text-lg font-semibold text-neutral-900">
        Interaction history
      </h2>

      {groups.length === 0 && (
        <p className="mt-2 text-neutral-600">
          No interactions recorded for this relationship.
        </p>
      )}

      {groups.map((group) => (
        <div key={group.date} className="mt-5">
          <h3 className="font-medium text-neutral-900">{formatDate(group.date)}</h3>
          {group.interactions.length > 1 && (
            <p className="text-sm text-neutral-600">
              {group.interactions.length} interactions — order within this date is
              not known.
            </p>
          )}
          <ul className="mt-2 divide-y divide-neutral-200 border-y border-neutral-200">
            {group.interactions.map((interaction) => (
              <li key={interaction.id} className="py-3">
                <p className="text-sm">
                  <span className="font-medium text-neutral-900">
                    {INTERACTION_TYPE_LABEL[interaction.type]}
                  </span>
                  <span className="text-neutral-600">
                    {" "}
                    · Contact:{" "}
                    {contactText(contactsById.get(interaction.contact_id))}
                  </span>
                </p>
                {interaction.notes.trim() === "" ? (
                  <p className="mt-1 text-neutral-600">No notes recorded.</p>
                ) : (
                  <p className="mt-1 whitespace-pre-line text-neutral-900 [overflow-wrap:anywhere]">
                    {interaction.notes}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
