import { apiBaseUrl } from "@/lib/config";
import { isDateOnly } from "@/lib/dates";
import {
  CUSTOMER_STATUSES,
  INTERACTION_TYPES,
  type Contact,
  type Interaction,
  type LatestInteraction,
  type RelationshipDetail,
  type RelationshipSummary,
} from "./types";

// Fact requests are short local reads (technical design, section 12).
const REQUEST_TIMEOUT_MS = 10_000;

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

function isRelationshipSummary(value: unknown): value is RelationshipSummary {
  return (
    isObject(value) &&
    isString(value.id) &&
    isString(value.name) &&
    isOneOf(CUSTOMER_STATUSES, value.status) &&
    (value.latest_interaction === null ||
      isLatestInteraction(value.latest_interaction)) &&
    value.assessment === null
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
