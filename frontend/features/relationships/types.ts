// The read-only FastAPI relationship contract. Field names match the API.

export const CUSTOMER_STATUSES = ["prospect", "customer"] as const;
export type CustomerStatus = (typeof CUSTOMER_STATUSES)[number];

export const INTERACTION_TYPES = ["email", "call", "meeting", "note"] as const;
export type InteractionType = (typeof INTERACTION_TYPES)[number];

export const CUSTOMER_STATUS_LABEL: Record<CustomerStatus, string> = {
  prospect: "Prospect",
  customer: "Customer",
};

export const INTERACTION_TYPE_LABEL: Record<InteractionType, string> = {
  email: "Email",
  call: "Call",
  meeting: "Meeting",
  note: "Note",
};

export type LatestInteraction = {
  /** YYYY-MM-DD */
  date: string;
  count: number;
  /** Distinct types on that date, in a stable listing order that is not chronology. */
  types: InteractionType[];
};

export type RelationshipSummary = {
  id: string;
  name: string;
  status: CustomerStatus;
  latest_interaction: LatestInteraction | null;
  /**
   * Always null until the assessment stage exists. Null means nothing is stored. It is
   * not a business state and not "Assessment unavailable".
   */
  assessment: null;
};

export type Contact = {
  id: string;
  name: string;
  email: string;
  role: string;
};

export type Interaction = {
  id: string;
  type: InteractionType;
  /** YYYY-MM-DD */
  occurred_at: string;
  contact_id: string;
  notes: string;
};

export type RelationshipDetail = {
  id: string;
  name: string;
  status: CustomerStatus;
  /** YYYY-MM-DD */
  created_at: string;
  contacts: Contact[];
  /** Newest date first. Within one date the order is a stable display order only. */
  interactions: Interaction[];
};
