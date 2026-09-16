import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mockFetch } from "@/test/mock-fetch";

import { RelationshipDetail } from "./relationship-detail";

const detail = {
  id: "cust_9",
  name: "Parkview Dental Studio",
  status: "prospect",
  created_at: "2026-08-17",
  contacts: [
    {
      id: "contact_10",
      name: "Chris Evans",
      email: "chris@parkviewdental.example",
      role: "Dentist",
    },
    {
      id: "contact_11",
      name: "Dana Ortiz",
      email: "dana@parkviewdental.example",
      role: "Office Manager",
    },
  ],
  // Newest date first, as the API sends it. Two interactions share 20 Aug 2026.
  interactions: [
    {
      id: "int_40",
      type: "note",
      occurred_at: "2026-08-20",
      contact_id: "contact_10",
      notes: "Need to confirm onboarding timeline.",
    },
    {
      id: "int_39",
      type: "email",
      occurred_at: "2026-08-20",
      contact_id: "contact_10",
      notes: "Chris replied that pricing looks reasonable.",
    },
    {
      id: "int_38",
      type: "meeting",
      occurred_at: "2026-08-19",
      contact_id: "contact_11",
      notes: "Demo completed.",
    },
    {
      id: "int_36",
      type: "email",
      occurred_at: "2026-08-17",
      contact_id: "contact_10",
      notes: "",
    },
  ],
};

describe("RelationshipDetail", () => {
  it("shows a loading message, then the facts, contacts and complete history", async () => {
    mockFetch({ body: detail });

    render(<RelationshipDetail id="cust_9" />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading relationship…",
    );

    const heading = await screen.findByRole("heading", {
      level: 1,
      name: "Parkview Dental Studio",
    });
    expect(heading).toBeInTheDocument();
    expect(
      screen.getByText("Prospect · Record created 17 Aug 2026"),
    ).toBeInTheDocument();

    const contacts = within(
      screen.getByRole("region", { name: "Contacts" }),
    ).getAllByRole("listitem");
    expect(contacts).toHaveLength(2);
    expect(contacts[0]).toHaveTextContent("Chris Evans");
    expect(contacts[0]).toHaveTextContent("Dentist");
    expect(contacts[0]).toHaveTextContent("chris@parkviewdental.example");
    expect(contacts[1]).toHaveTextContent("Dana Ortiz");
    expect(
      screen.queryByRole("link", { name: /parkviewdental\.example/ }),
    ).not.toBeInTheDocument();

    const history = screen.getByRole("region", { name: "Interaction history" });
    const dates = within(history)
      .getAllByRole("heading", { level: 3 })
      .map((each) => each.textContent);
    expect(dates).toEqual(["20 Aug 2026", "19 Aug 2026", "17 Aug 2026"]);
    expect(within(history).getAllByRole("listitem")).toHaveLength(4);
    expect(
      within(history).getByText("Need to confirm onboarding timeline."),
    ).toBeInTheDocument();
    expect(
      within(history).getByText("Chris replied that pricing looks reasonable."),
    ).toBeInTheDocument();
    expect(within(history).getByText("Demo completed.")).toBeInTheDocument();
    expect(within(history).getByText("No notes recorded.")).toBeInTheDocument();
    expect(
      within(history).getAllByText("· Contact: Chris Evans, Dentist"),
    ).toHaveLength(3);
    expect(
      within(history).getByText("· Contact: Dana Ortiz, Office Manager"),
    ).toBeInTheDocument();
    expect(history.textContent).not.toMatch(/\b(from|to):/i);
  });

  it("keeps every same-date interaction under one date heading without claiming an order", async () => {
    mockFetch({ body: detail });

    render(<RelationshipDetail id="cust_9" />);

    const history = within(
      await screen.findByRole("region", { name: "Interaction history" }),
    );
    expect(history.getAllByRole("heading", { name: "20 Aug 2026" })).toHaveLength(
      1,
    );
    expect(
      history.getByText(
        "2 interactions — order within this date is not known.",
      ),
    ).toBeInTheDocument();
    expect(history.getByText("Note")).toBeInTheDocument();
    expect(history.getAllByText("Email")).toHaveLength(2);
    expect(history.getByText("Meeting")).toBeInTheDocument();
    expect(history.queryByText(/\b(then|later|earlier|first|last)\b/i)).toBeNull();
    // Only the shared date carries the note about unknown order.
    expect(
      history.queryByText(/1 interactions?/),
    ).not.toBeInTheDocument();
  });

  it("names the relationship in the page title while it is open", async () => {
    mockFetch({ body: detail });

    const { unmount } = render(<RelationshipDetail id="cust_9" />);
    await screen.findByRole("heading", { name: "Parkview Dental Studio" });

    expect(document.title).toBe("Parkview Dental Studio · Customer Pulse");

    unmount();

    expect(document.title).toBe("Customer Pulse");
  });

  it("moves focus to the relationship heading once it has loaded", async () => {
    mockFetch({ body: detail });

    render(<RelationshipDetail id="cust_9" />);

    expect(
      await screen.findByRole("heading", { name: "Parkview Dental Studio" }),
    ).toHaveFocus();
  });

  it("offers no actions: nothing sends, creates, edits or deletes", async () => {
    mockFetch({ body: detail });

    render(<RelationshipDetail id="cust_9" />);
    await screen.findByRole("heading", { name: "Parkview Dental Studio" });

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(1);
    expect(
      screen.getByRole("link", { name: "Back to all relationships" }),
    ).toHaveAttribute("href", "/");
  });

  it("says when there are no contacts and no interactions", async () => {
    mockFetch({ body: { ...detail, contacts: [], interactions: [] } });

    render(<RelationshipDetail id="cust_9" />);

    expect(
      await screen.findByText("No contacts recorded for this relationship."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No interactions recorded for this relationship."),
    ).toBeInTheDocument();
  });

  it("shows a not-found message with a way back for a 404", async () => {
    mockFetch({ status: 404, body: { detail: "Relationship not found" } });

    render(<RelationshipDetail id="cust_999" />);

    const heading = await screen.findByRole("heading", {
      level: 1,
      name: "This relationship could not be found.",
    });
    expect(heading).toHaveFocus();
    expect(
      screen.getByRole("link", { name: "Back to all relationships" }),
    ).toHaveAttribute("href", "/");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(document.title).toBe("Customer Pulse");
  });

  it("shows a load error with Try again for a server failure, not not-found", async () => {
    mockFetch({ status: 500, body: { detail: "Internal error" } }, { body: detail });

    render(<RelationshipDetail id="cust_9" />);

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Customer Pulse could not load this relationship.",
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/could not be found/)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/No interactions recorded/),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(
      await screen.findByRole("heading", { name: "Parkview Dental Studio" }),
    ).toBeInTheDocument();
  });

  it("ignores a late response for a relationship that is no longer open", async () => {
    let resolveFirst: (value: Response) => void = () => {};
    const first = new Promise<Response>((resolve) => {
      resolveFirst = resolve;
    });
    const fetchMock = mockFetch({ body: { ...detail, id: "cust_2", name: "Second Clinic" } });
    fetchMock.mockReset();
    fetchMock
      .mockReturnValueOnce(first)
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...detail, id: "cust_2", name: "Second Clinic" }), {
          status: 200,
        }),
      );

    const { rerender } = render(<RelationshipDetail id="cust_9" />);
    rerender(<RelationshipDetail id="cust_2" />);
    await screen.findByRole("heading", { name: "Second Clinic" });

    resolveFirst(new Response(JSON.stringify(detail), { status: 200 }));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(
      screen.getByRole("heading", { name: "Second Clinic" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Parkview Dental Studio" }),
    ).not.toBeInTheDocument();
  });
});
