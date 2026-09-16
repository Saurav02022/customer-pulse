import type { Contact } from "../types";

export function ContactsSection({ contacts }: { contacts: Contact[] }) {
  return (
    <section aria-labelledby="contacts-heading" className="mt-8">
      <h2 id="contacts-heading" className="text-lg font-semibold text-neutral-900">
        Contacts
      </h2>
      {contacts.length === 0 ? (
        <p className="mt-2 text-neutral-600">
          No contacts recorded for this relationship.
        </p>
      ) : (
        <ul className="mt-2 divide-y divide-neutral-200 border-y border-neutral-200">
          {contacts.map((contact) => (
            <li key={contact.id} className="py-3">
              <p className="[overflow-wrap:anywhere]">
                <span className="font-medium text-neutral-900">{contact.name}</span>
                <span className="text-neutral-600"> · {contact.role}</span>
              </p>
              {/* Plain, selectable text. Customer Pulse sends nothing. */}
              <p className="text-neutral-600 [overflow-wrap:anywhere]">
                {contact.email}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
