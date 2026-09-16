import { describe, expect, it } from "vitest";

import { mockFetch } from "@/test/mock-fetch";

import { fetchRelationship, fetchRelationships } from "./api";

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
