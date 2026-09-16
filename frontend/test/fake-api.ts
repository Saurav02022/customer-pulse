import { act } from "@testing-library/react";
import { vi } from "vitest";

type Reply = { status?: number; body?: unknown } | Error;

type Pending = { id: string; settle: (reply: Reply) => void };

const ASSESSMENT_PATH = /^\/api\/relationships\/([^/]+)\/assessment$/;
const DETAIL_PATH = /^\/api\/relationships\/([^/]+)$/;

function jsonResponse(reply: { status?: number; body?: unknown }): Response {
  return new Response(JSON.stringify(reply.body ?? null), {
    status: reply.status ?? 200,
    headers: { "Content-Type": "application/json" },
  });
}

/**
 * Replaces global fetch with a small fake of the backend. The list and detail answer at
 * once. Each assessment request stays open until the test settles it with `respond`,
 * so tests control exactly when work finishes, with no timers.
 */
export function fakeApi({
  relationships,
  details = {},
}: {
  relationships?: unknown[];
  details?: Record<string, unknown>;
}) {
  const open: Pending[] = [];
  const assessmentCalls: string[] = [];

  const fetchMock = vi.fn(
    (url: string, init?: RequestInit): Promise<Response> => {
      const path = new URL(url).pathname;
      const assessment = ASSESSMENT_PATH.exec(path);
      if (assessment) {
        const id = decodeURIComponent(assessment[1]);
        assessmentCalls.push(id);
        return new Promise((resolve, reject) => {
          const pending: Pending = {
            id,
            settle: (reply) => {
              const index = open.indexOf(pending);
              if (index === -1) return;
              open.splice(index, 1);
              if (reply instanceof Error) reject(reply);
              else resolve(jsonResponse(reply));
            },
          };
          open.push(pending);
          init?.signal?.addEventListener("abort", () =>
            pending.settle(new DOMException("Aborted", "AbortError")),
          );
        });
      }
      if (path === "/api/relationships") {
        return Promise.resolve(jsonResponse({ body: { relationships } }));
      }
      const detail = DETAIL_PATH.exec(path);
      const body = detail ? details[decodeURIComponent(detail[1])] : undefined;
      return Promise.resolve(
        jsonResponse(
          body === undefined
            ? { status: 404, body: { detail: "Relationship not found" } }
            : { body },
        ),
      );
    },
  );
  vi.stubGlobal("fetch", fetchMock);

  return {
    /** Ids of every assessment request, in the order they were made. */
    assessmentCalls,
    /** Ids whose assessment request is still in flight. */
    active: () => open.map((pending) => pending.id),
    /** Settles the in-flight assessment request for `id` and lets React update. */
    async respond(id: string, reply: Reply) {
      const pending = open.find((each) => each.id === id);
      if (!pending) throw new Error(`No assessment request is open for ${id}`);
      await act(async () => {
        pending.settle(reply);
      });
    },
  };
}

// --- response bodies ---

export const claim = (text: string, ...evidence: string[]) => ({
  text,
  evidence,
});

export function actionNeeded(reason = "The proposal has had no response.") {
  return {
    status: "assessed",
    state: "action_needed",
    summary: claim("A proposal was sent.", "int_1"),
    reason: claim(reason, "int_1"),
    open_items: [],
    next_action: claim("Follow up on the proposal.", "int_1"),
  };
}

export function waiting(reason = "Waiting for the planning meeting.") {
  return {
    status: "assessed",
    state: "waiting",
    summary: claim("Pricing was sent.", "int_1"),
    reason: claim(reason, "int_1"),
    open_items: [],
    waiting_for: claim("The September planning meeting.", "int_1"),
    next_action: null,
  };
}

export function noActionNeeded(reason = "The issue was confirmed resolved.") {
  return {
    status: "assessed",
    state: "no_action_needed",
    summary: claim("An issue was reported and resolved.", "int_1"),
    reason: claim(reason, "int_1"),
    open_items: [],
  };
}

export const insufficientEvidence = {
  status: "unavailable",
  cause: "insufficient_evidence",
};

export const providerTimeout = {
  status: 503,
  body: {
    detail: "The assessment provider did not reply in time.",
    cause: "provider_timeout",
  },
};
export const providerError = {
  status: 503,
  body: {
    detail: "The assessment provider is temporarily unavailable.",
    cause: "provider_error",
  },
};
export const invalidOutput = {
  status: 502,
  body: {
    detail: "The assessment reply could not be trusted.",
    cause: "invalid_output",
  },
};
