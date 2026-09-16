import { apiBaseUrl } from "@/lib/config";
import { isDateOnly } from "@/lib/dates";
import {
  ASSESSMENT_STATES,
  CUSTOMER_STATUSES,
  INTERACTION_TYPES,
  UNAVAILABLE_CAUSES,
  type AssessmentResult,
  type Claim,
  type Contact,
  type Interaction,
  type LatestInteraction,
  type ListAssessed,
  type OpenItem,
  type RelationshipDetail,
  type RelationshipSummary,
  type UnavailableAssessment,
} from "./types";

// Fact requests are short local reads. An assessment may wait for one model call plus
// one retry (technical design, section 12).
const REQUEST_TIMEOUT_MS = 10_000;
const ASSESSMENT_TIMEOUT_MS = 75_000;

// Backend causes that mean trying again later may help (technical design, section 13).
const TEMPORARY_CAUSES = ["provider_timeout", "provider_error"] as const;

export type ApiResult<T> =
  | { status: "ok"; data: T }
  | { status: "not_found" }
  /** Network failure, timeout, non-2xx response, or a body outside the contract. */
  | { status: "failed" };

export async function fetchRelationships(): Promise<
  ApiResult<RelationshipSummary[]>
> {
  const result = await getJson("/api/relationships", isRelationshipList);
  if (result.status === "ok") {
    return { status: "ok", data: result.data.relationships };
  }
  // The list route has no 404; an unexpected one is a failure like any other.
  return { status: "failed" };
}

export function fetchRelationship(
  id: string,
): Promise<ApiResult<RelationshipDetail>> {
  return getJson(
    `/api/relationships/${encodeURIComponent(id)}`,
    isRelationshipDetail,
  );
}

/**
 * "temporary": the provider timed out or failed, or the browser could not get an answer.
 * Trying again may help. "unknown": the reply could not be trusted, the server failed,
 * or the body is outside the contract. Nothing more is said to the owner.
 */
export type AssessmentFailure = "temporary" | "unknown";

export type AssessmentFetchResult =
  | { status: "ok"; data: AssessmentResult }
  | { status: "not_found" }
  | { status: "failed"; failure: AssessmentFailure };

export async function fetchAssessment(
  id: string,
  signal?: AbortSignal,
): Promise<AssessmentFetchResult> {
  const timeout = AbortSignal.timeout(ASSESSMENT_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(
      `${apiBaseUrl}/api/relationships/${encodeURIComponent(id)}/assessment`,
      {
        headers: { Accept: "application/json" },
        signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
      },
    );
  } catch {
    // Network failure, CORS or the browser timeout.
    return { status: "failed", failure: "temporary" };
  }
  if (response.status === 404) return { status: "not_found" };

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = undefined;
  }
  if (response.status === 200 && isAssessmentResult(body)) {
    return { status: "ok", data: body };
  }
  const temporary =
    response.status === 503 &&
    isObject(body) &&
    isOneOf(TEMPORARY_CAUSES, body.cause);
  return { status: "failed", failure: temporary ? "temporary" : "unknown" };
}

async function getJson<T>(
  path: string,
  isExpected: (value: unknown) => value is T,
): Promise<ApiResult<T>> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch {
    return { status: "failed" };
  }
  if (response.status === 404) return { status: "not_found" };
  if (!response.ok) return { status: "failed" };

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return { status: "failed" };
  }
  return isExpected(body) ? { status: "ok", data: body } : { status: "failed" };
}

// --- type guards: the only place the network shape is trusted ---

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isOneOf<T extends string>(
  options: readonly T[],
  value: unknown,
): value is T {
  return options.some((option) => option === value);
}

function isLatestInteraction(value: unknown): value is LatestInteraction {
  return (
    isObject(value) &&
    isDateOnly(value.date) &&
    typeof value.count === "number" &&
    Number.isInteger(value.count) &&
    value.count > 0 &&
    Array.isArray(value.types) &&
    value.types.length > 0 &&
    value.types.every((type) => isOneOf(INTERACTION_TYPES, type))
  );
}

/** True when the object has exactly these keys, so an unexpected field is rejected. */
function hasExactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every((key) => key in value);
}

function isText(value: unknown): value is string {
  return isString(value) && value.trim() !== "";
}

function isIdList(value: unknown): value is string[] {
  return Array.isArray(value) && value.length > 0 && value.every(isText);
}

function isClaim(value: unknown): value is Claim {
  return (
    isObject(value) &&
    hasExactKeys(value, ["text", "evidence"]) &&
    isText(value.text) &&
    isIdList(value.evidence)
  );
}

function isOpenItem(value: unknown): value is OpenItem {
  return (
    isObject(value) &&
    hasExactKeys(value, ["text", "evidence", "contact_ids"]) &&
    isText(value.text) &&
    isIdList(value.evidence) &&
    isIdList(value.contact_ids)
  );
}

function isUnavailable(value: unknown): value is UnavailableAssessment {
  return (
    isObject(value) &&
    hasExactKeys(value, ["status", "cause"]) &&
    value.status === "unavailable" &&
    isOneOf(UNAVAILABLE_CAUSES, value.cause)
  );
}

const ASSESSED_KEYS = ["status", "state", "summary", "reason", "open_items"];

function isAssessmentResult(value: unknown): value is AssessmentResult {
  if (isUnavailable(value)) return true;
  if (
    !isObject(value) ||
    value.status !== "assessed" ||
    !isClaim(value.summary) ||
    !isClaim(value.reason) ||
    !Array.isArray(value.open_items) ||
    !value.open_items.every(isOpenItem)
  ) {
    return false;
  }
  // Each state has exactly its own fields (technical design, section 7).
  switch (value.state) {
    case "action_needed":
      return (
        hasExactKeys(value, [...ASSESSED_KEYS, "next_action"]) &&
        isClaim(value.next_action)
      );
    case "waiting":
      return (
        hasExactKeys(value, [...ASSESSED_KEYS, "waiting_for", "next_action"]) &&
        isClaim(value.waiting_for) &&
        (value.next_action === null || isClaim(value.next_action))
      );
    case "no_action_needed":
      return (
        hasExactKeys(value, ASSESSED_KEYS) && value.open_items.length === 0
      );
    default:
      return false;
  }
}

function isListAssessed(value: unknown): value is ListAssessed {
  return (
    isObject(value) &&
    hasExactKeys(value, ["status", "state", "reason"]) &&
    value.status === "assessed" &&
    isOneOf(ASSESSMENT_STATES, value.state) &&
    isText(value.reason)
  );
}

function isRelationshipSummary(value: unknown): value is RelationshipSummary {
  return (
    isObject(value) &&
    isString(value.id) &&
    isString(value.name) &&
    isOneOf(CUSTOMER_STATUSES, value.status) &&
    (value.latest_interaction === null ||
      isLatestInteraction(value.latest_interaction)) &&
    (value.assessment === null ||
      isListAssessed(value.assessment) ||
      isUnavailable(value.assessment))
  );
}

function isRelationshipList(
  value: unknown,
): value is { relationships: RelationshipSummary[] } {
  return (
    isObject(value) &&
    Array.isArray(value.relationships) &&
    value.relationships.every(isRelationshipSummary)
  );
}

function isContact(value: unknown): value is Contact {
  return (
    isObject(value) &&
    isString(value.id) &&
    isString(value.name) &&
    isString(value.email) &&
    isString(value.role)
  );
}

function isInteraction(value: unknown): value is Interaction {
  return (
    isObject(value) &&
    isString(value.id) &&
    isOneOf(INTERACTION_TYPES, value.type) &&
    isDateOnly(value.occurred_at) &&
    isString(value.contact_id) &&
    isString(value.notes)
  );
}

function isRelationshipDetail(value: unknown): value is RelationshipDetail {
  return (
    isObject(value) &&
    isString(value.id) &&
    isString(value.name) &&
    isOneOf(CUSTOMER_STATUSES, value.status) &&
    isDateOnly(value.created_at) &&
    Array.isArray(value.contacts) &&
    value.contacts.every(isContact) &&
    Array.isArray(value.interactions) &&
    value.interactions.every(isInteraction)
  );
}
