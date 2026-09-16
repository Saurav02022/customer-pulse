// The read-only FastAPI relationship and assessment contract. Field names match the API.

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

export const ASSESSMENT_STATES = [
  "action_needed",
  "waiting",
  "no_action_needed",
] as const;
export type AssessmentState = (typeof ASSESSMENT_STATES)[number];

export const UNAVAILABLE_CAUSES = [
  "no_interactions",
  "insufficient_evidence",
] as const;
export type UnavailableCause = (typeof UNAVAILABLE_CAUSES)[number];

/** Assessment unavailable with a known cause. A fallback, not a business state. */
export type UnavailableAssessment = {
  status: "unavailable";
  cause: UnavailableCause;
};

/** What the list sends for a stored business assessment: the row needs no more. */
export type ListAssessed = {
  status: "assessed";
  state: AssessmentState;
  reason: string;
};

export type RelationshipSummary = {
  id: string;
  name: string;
  status: CustomerStatus;
  latest_interaction: LatestInteraction | null;
  /**
   * Null means nothing valid is stored yet, so the browser asks the assessment route.
   * It is not a business state and not "Assessment unavailable".
   */
  assessment: ListAssessed | UnavailableAssessment | null;
};

/** One statement and the real interaction ids that support it. */
export type Claim = { text: string; evidence: string[] };
export type OpenItem = Claim & { contact_ids: string[] };

type AssessedBase = {
  status: "assessed";
  summary: Claim;
  reason: Claim;
  open_items: OpenItem[];
};

export type ActionNeededAssessment = AssessedBase & {
  state: "action_needed";
  next_action: Claim;
};

export type WaitingAssessment = AssessedBase & {
  state: "waiting";
  waiting_for: Claim;
  /** Applies only once the awaited event happens. */
  next_action: Claim | null;
};

/** Has no next_action field at all, and no open items. */
export type NoActionNeededAssessment = AssessedBase & {
  state: "no_action_needed";
};

export type BusinessAssessment =
  ActionNeededAssessment | WaitingAssessment | NoActionNeededAssessment;

/** A 200 body from GET /api/relationships/{id}/assessment. */
export type AssessmentResult = BusinessAssessment | UnavailableAssessment;

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

export const ASSESSMENT_STATE_LABEL: Record<AssessmentState, string> = {
  action_needed: "Action needed",
  waiting: "Waiting",
  no_action_needed: "No action needed",
};

// Shown wherever a state is shown, so no help page is needed (UX spec, section 5).
export const ASSESSMENT_STATE_MEANING: Record<AssessmentState, string> = {
  action_needed: "The history shows something to consider doing now.",
  waiting: "The next step depends on something that has not happened yet.",
  no_action_needed: "The history shows nothing needs doing right now.",
};
