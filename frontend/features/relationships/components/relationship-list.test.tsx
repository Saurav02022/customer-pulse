import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mockFetch } from "@/test/mock-fetch";

import { RelationshipList } from "./relationship-list";

const rows = [
  {
    id: "cust_1",
    name: "Northstar Dental Group",
    status: "prospect",
    latest_interaction: { date: "2026-08-29", count: 1, types: ["note"] },
    assessment: null,
  },
  {
    id: "cust_2",
    name: "Parkview Dental Studio",
    status: "customer",
    latest_interaction: {
      date: "2026-08-20",
      count: 2,
      types: ["email", "note"],
    },
    assessment: null,
  },
  {
    id: "cust_3",
    name: "Quiet Start Clinic",
    status: "prospect",
    latest_interaction: null,
    assessment: null,
  },
];

describe("RelationshipList", () => {
  it("shows a loading message, then every relationship with status and latest interaction", async () => {
    mockFetch({ body: { relationships: rows } });

    render(<RelationshipList selectedId={null} />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading relationships…",
    );
    expect(
      screen.getByRole("heading", { level: 1, name: "Relationships" }),
    ).toBeInTheDocument();

    const list = await screen.findByRole("list");
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    expect(within(items[0]).getByText("Prospect")).toBeInTheDocument();
    expect(within(items[1]).getByText("Customer")).toBeInTheDocument();
    expect(
      screen.getByText("Latest interaction: 29 Aug 2026 · Note"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Latest interaction: 20 Aug 2026 · 2 interactions: Email, Note",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Latest interaction: No interactions yet"),
    ).toBeInTheDocument();

    // Dates are information only: nothing relative, nothing urgent.
    expect(list.textContent).not.toMatch(/ago|overdue|stale|urgent|due/i);
  });

  it("links each row to its relationship route and selects nobody at first", async () => {
    mockFetch({ body: { relationships: rows } });

    render(<RelationshipList selectedId={null} />);

    // Each row is one link named by the customer; the facts describe it.
    const link = await screen.findByRole("link", {
      name: "Parkview Dental Studio",
    });
    expect(link).toHaveAttribute("href", "/relationships/cust_2");
    expect(link).toHaveAccessibleDescription(
      /^Customer Latest interaction: 20 Aug 2026 · 2\sinteractions: Email, Note$/,
    );
    for (const each of screen.getAllByRole("link")) {
      expect(each).not.toHaveAttribute("aria-current");
    }
  });

  it("marks the open relationship as the current page and steps the heading down", async () => {
    mockFetch({ body: { relationships: rows } });

    render(<RelationshipList selectedId="cust_2" />);

    const link = await screen.findByRole("link", {
      name: /Parkview Dental Studio/,
    });
    expect(link).toHaveAttribute("aria-current", "page");
    expect(
      screen.getByRole("heading", { level: 2, name: "Relationships" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Northstar Dental Group/ }),
    ).not.toHaveAttribute("aria-current");
  });

  it("shows the empty message for a successful empty response, not an error", async () => {
    mockFetch({ body: { relationships: [] } });

    render(<RelationshipList selectedId={null} />);

    expect(
      await screen.findByText("There are no relationships to show."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("shows an error with Try again when loading fails, never the empty message", async () => {
    mockFetch({ status: 500, body: { detail: "Internal error" } });

    render(<RelationshipList selectedId={null} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Customer Pulse could not load your relationships.",
    );
    expect(
      screen.getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("There are no relationships to show."),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("asks for the list again when Try again is pressed", async () => {
    const fetchMock = mockFetch(new TypeError("Failed to fetch"), {
      body: { relationships: rows },
    });

    render(<RelationshipList selectedId={null} />);

    fireEvent.click(await screen.findByRole("button", { name: "Try again" }));

    expect(
      await screen.findByRole("link", { name: /Northstar Dental Group/ }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    // The pressed button is gone, so focus goes to the list heading, not the page.
    expect(
      screen.getByRole("heading", { name: "Relationships" }),
    ).toHaveFocus();
  });

  it("returns focus to the row that was open when the owner goes back", async () => {
    mockFetch({ body: { relationships: rows } });

    const { rerender } = render(<RelationshipList selectedId="cust_2" />);
    const link = await screen.findByRole("link", {
      name: /Parkview Dental Studio/,
    });
    expect(link).not.toHaveFocus();

    rerender(<RelationshipList selectedId={null} />);

    expect(link).toHaveFocus();
    expect(link).not.toHaveAttribute("aria-current");
  });
});
