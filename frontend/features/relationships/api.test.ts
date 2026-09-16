import { describe, expect, it } from "vitest";

import { mockFetch } from "@/test/mock-fetch";

import {
  actionNeeded,
  claim,
  invalidOutput,
  noActionNeeded,
  providerError,
  providerTimeout,
  waiting,
} from "@/test/fake-api";

import { fetchAssessment, fetchRelationship, fetchRelationships } from "./api";

const summary = {
  id: "cust_1",
  name: "Northstar Dental Group",
  status: "prospect",
  latest_interaction: { date: "2026-08-29", count: 1, types: ["note"] },
  assessment: null,
};

const detail = {
  id: "cust_1",
  name: "Northstar Dental Group",
  status: "prospect",
  created_at: "2026-05-12",
  contacts: [
    {
      id: "contact_1",
      name: "Sarah Mitchell",
      email: "sarah@northstar.example",
      role: "Owner",
    },
  ],
  interactions: [
    {
      id: "int_1",
      type: "email",
      occurred_at: "2026-08-18",
      contact_id: "contact_1",
      notes: "Asked for pricing.",
    },
  ],
};

describe("fetchRelationships", () => {
  it("returns the relationships from a successful response", async () => {
    const fetchMock = mockFetch({ body: { relationships: [summary] } });

    const result = await fetchRelationships();

    expect(result).toEqual({ status: "ok", data: [summary] });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/relationships",
      expect.objectContaining({ headers: { Accept: "application/json" } }),
    );
  });

  it("returns an empty list as a success, not a failure", async () => {
    mockFetch({ body: { relationships: [] } });

    expect(await fetchRelationships()).toEqual({ status: "ok", data: [] });
  });

  it("treats a server error as a failure, never as an empty list", async () => {
    mockFetch({ status: 500, body: { detail: "Internal error" } });

    expect(await fetchRelationships()).toEqual({ status: "failed" });
  });

  it("treats a network failure as a failure", async () => {
    mockFetch(new TypeError("Failed to fetch"));

    expect(await fetchRelationships()).toEqual({ status: "failed" });
  });

  it("treats a body outside the contract as a failure", async () => {
    mockFetch({ body: { relationships: [{ ...summary, status: "lead" }] } });

    expect(await fetchRelationships()).toEqual({ status: "failed" });
  });

  it("treats a body that is not JSON as a failure", async () => {
    mockFetch({ text: "<html>not json</html>" });

    expect(await fetchRelationships()).toEqual({ status: "failed" });
  });

  it.each([
    ["nothing stored", null],
    [
      "a stored business assessment",
      {
        status: "assessed",
        state: "waiting",
        reason: "Waiting for a decision.",
      },
    ],
    [
      "a code-decided cause",
      { status: "unavailable", cause: "no_interactions" },
    ],
    [
      "stored insufficient evidence",
      { status: "unavailable", cause: "insufficient_evidence" },
    ],
  ])("accepts a list assessment with %s", async (_, assessment) => {
    const row = { ...summary, assessment };
    mockFetch({ body: { relationships: [row] } });

    expect(await fetchRelationships()).toEqual({ status: "ok", data: [row] });
  });

  it.each([
    ["an empty object", {}],
    [
      "an unknown state",
      { status: "assessed", state: "urgent", reason: "Now." },
    ],
    ["an empty reason", { status: "assessed", state: "waiting", reason: " " }],
    [
      "an extra field",
      {
        status: "assessed",
        state: "waiting",
        reason: "Wait.",
        confidence: 0.9,
      },
    ],
    ["a failure cause", { status: "unavailable", cause: "provider_timeout" }],
    ["the full assessment shape", actionNeeded()],
  ])("rejects a list assessment with %s", async (_, assessment) => {
    mockFetch({ body: { relationships: [{ ...summary, assessment }] } });

    expect(await fetchRelationships()).toEqual({ status: "failed" });
  });
});

describe("fetchAssessment", () => {
  it.each([
    ["Action needed", actionNeeded()],
    ["Waiting", waiting()],
    [
      "Waiting with a next action",
      { ...waiting(), next_action: claim("After the meeting, ask.", "int_1") },
    ],
    ["No action needed", noActionNeeded()],
    [
      "an open item",
      {
        ...actionNeeded(),
        open_items: [
          { text: "Confirm.", evidence: ["int_1"], contact_ids: ["contact_1"] },
        ],
      },
    ],
    [
      "insufficient evidence",
      { status: "unavailable", cause: "insufficient_evidence" },
    ],
    ["no interactions", { status: "unavailable", cause: "no_interactions" }],
  ])("returns %s from a 200", async (_, body) => {
    const fetchMock = mockFetch({ body });

    expect(await fetchAssessment("cust_1")).toEqual({
      status: "ok",
      data: body,
    });
    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://127.0.0.1:8000/api/relationships/cust_1/assessment",
    );
  });

  it.each([
    [
      "No action needed with a next action",
      { ...noActionNeeded(), next_action: claim("Call.", "int_1") },
    ],
    [
      "No action needed with an open item",
      {
        ...noActionNeeded(),
        open_items: [
          { text: "Check.", evidence: ["int_1"], contact_ids: ["contact_1"] },
        ],
      },
    ],
    [
      "Action needed without a next action",
      { ...actionNeeded(), next_action: undefined },
    ],
    [
      "Action needed with waiting_for",
      { ...actionNeeded(), waiting_for: claim("x", "int_1") },
    ],
    ["Waiting without waiting_for", { ...waiting(), waiting_for: undefined }],
    [
      "Waiting without a next_action field",
      Object.fromEntries(
        Object.entries(waiting()).filter(([key]) => key !== "next_action"),
      ),
    ],
    [
      "a claim with no evidence",
      { ...actionNeeded(), reason: claim("No reason given.") },
    ],
    [
      "a claim with empty text",
      { ...actionNeeded(), reason: claim("  ", "int_1") },
    ],
    [
      "an open item with no contact",
      {
        ...actionNeeded(),
        open_items: [
          { text: "Confirm.", evidence: ["int_1"], contact_ids: [] },
        ],
      },
    ],
    [
      "an open item using the model field name",
      {
        ...actionNeeded(),
        open_items: [
          { text: "Confirm.", evidence: ["int_1"], contacts: ["contact_1"] },
        ],
      },
    ],
    ["a confidence score", { ...actionNeeded(), confidence: 0.8 }],
    ["an unknown state", { ...actionNeeded(), state: "urgent" }],
    [
      "a failure cause in a 200",
      { status: "unavailable", cause: "provider_timeout" },
    ],
    [
      "the list shape",
      { status: "assessed", state: "waiting", reason: "Wait." },
    ],
    ["null", null],
  ])("treats a 200 with %s as an unknown failure", async (_, body) => {
    mockFetch({ body: JSON.parse(JSON.stringify(body)) });

    expect(await fetchAssessment("cust_1")).toEqual({
      status: "failed",
      failure: "unknown",
    });
  });

  it.each([
    ["a provider timeout", providerTimeout, "temporary"],
    ["a provider error", providerError, "temporary"],
    ["invalid output", invalidOutput, "unknown"],
    [
      "a 503 without a known cause",
      { status: 503, body: { detail: "Busy" } },
      "unknown",
    ],
    [
      "a setup error",
      { status: 500, body: { detail: "Internal error" } },
      "unknown",
    ],
    ["a 200 that is not JSON", { text: "<html></html>" }, "unknown"],
  ])("maps %s to a %s failure", async (_, reply, failure) => {
    mockFetch(reply);

    expect(await fetchAssessment("cust_1")).toEqual({
      status: "failed",
      failure,
    });
  });

  it("treats a network failure or timeout as temporary", async () => {
    mockFetch(
      new TypeError("Failed to fetch"),
      // What fetch rejects with when the timeout signal fires.
      Object.assign(new Error("The operation timed out."), {
        name: "TimeoutError",
      }),
    );

    expect(await fetchAssessment("cust_1")).toEqual({
      status: "failed",
      failure: "temporary",
    });
    expect(await fetchAssessment("cust_1")).toEqual({
      status: "failed",
      failure: "temporary",
    });
  });

  it("keeps a 404 apart from failures", async () => {
    mockFetch({ status: 404, body: { detail: "Relationship not found" } });

    expect(await fetchAssessment("cust_9")).toEqual({ status: "not_found" });
  });

  it("encodes the id and passes a signal that the caller can abort", async () => {
    const fetchMock = mockFetch({ body: noActionNeeded() });
    const controller = new AbortController();

    await fetchAssessment("a/b", controller.signal);

    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://127.0.0.1:8000/api/relationships/a%2Fb/assessment",
    );
    const signal: AbortSignal = fetchMock.mock.calls[0][1].signal;
    expect(signal.aborted).toBe(false);
    controller.abort();
    expect(signal.aborted).toBe(true);
  });
});

describe("fetchRelationship", () => {
  it("returns the detail for a known relationship", async () => {
    const fetchMock = mockFetch({ body: detail });

    const result = await fetchRelationship("cust_1");

    expect(result).toEqual({ status: "ok", data: detail });
    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://127.0.0.1:8000/api/relationships/cust_1",
    );
  });

  it("keeps a 404 apart from other failures", async () => {
    mockFetch({ status: 404, body: { detail: "Relationship not found" } });

    expect(await fetchRelationship("cust_999")).toEqual({
      status: "not_found",
    });
  });

  it("treats a server error as a failure, not as not found", async () => {
    mockFetch({ status: 500, body: { detail: "Internal error" } });

    expect(await fetchRelationship("cust_1")).toEqual({ status: "failed" });
  });

  it("rejects a detail whose dates are not date-only values", async () => {
    mockFetch({ body: { ...detail, created_at: "2026-05-12T00:00:00Z" } });

    expect(await fetchRelationship("cust_1")).toEqual({ status: "failed" });
  });

  it("encodes the id in the request path", async () => {
    const fetchMock = mockFetch({ status: 404, body: {} });

    await fetchRelationship("a/b c");

    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://127.0.0.1:8000/api/relationships/a%2Fb%20c",
    );
  });
});
