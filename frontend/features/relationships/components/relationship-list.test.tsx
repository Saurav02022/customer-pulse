import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  actionNeeded,
  fakeApi,
  insufficientEvidence,
  invalidOutput,
  noActionNeeded,
  providerError,
  providerTimeout,
  waiting,
} from "@/test/fake-api";
import { mockFetch } from "@/test/mock-fetch";

import { AssessmentsProvider } from "../assessments";
import { RelationshipList } from "./relationship-list";

function row(
  id: string,
  name: string,
  assessment: unknown,
  latest: unknown = { date: "2026-08-29", count: 1, types: ["note"] },
) {
  return {
    id,
    name,
    status: "prospect",
    latest_interaction: latest,
    assessment,
  };
}

const listed = (state: string, reason: string) => ({
  status: "assessed",
  state,
  reason,
});

function renderList(selectedId: string | null = null) {
  return render(
    <AssessmentsProvider>
      <RelationshipList selectedId={selectedId} />
    </AssessmentsProvider>,
  );
}

function section(name: string | RegExp) {
  return within(screen.getByRole("region", { name }));
}

function namesIn(name: string | RegExp): string[] {
  return section(name)
    .getAllByRole("link")
    .map((link) => link.textContent ?? "")
    .map((text) => text.split(/Prospect|Customer/)[0]);
}

// Three stored outcomes and no null rows: nothing is requested.
const cachedRows = [
  row(
    "cust_1",
    "Northstar Dental Group",
    listed("action_needed", "The proposal has had no response."),
  ),
  {
    ...row("cust_2", "Parkview Dental Studio", insufficientEvidence, {
      date: "2026-08-20",
      count: 2,
      types: ["email", "note"],
    }),
    status: "customer",
  },
  row(
    "cust_3",
    "Quiet Start Clinic",
    { status: "unavailable", cause: "no_interactions" },
    null,
  ),
];

describe("RelationshipList facts", () => {
  it("shows a loading message, then every relationship with status and latest interaction", async () => {
    fakeApi({ relationships: cachedRows });

    renderList();

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading relationships…",
    );
    expect(
      screen.getByRole("heading", { level: 1, name: "Relationships" }),
    ).toBeInTheDocument();

    const links = await screen.findAllByRole("link", {
      name: /Dental|Clinic/,
    });
    expect(links).toHaveLength(3);
    expect(
      screen.queryByText("Loading relationships…"),
    ).not.toBeInTheDocument();
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
    expect(document.body.textContent).not.toMatch(
      /ago|overdue|stale|urgent|due\b/i,
    );
  });

  it("links each row to its relationship route and selects nobody at first", async () => {
    fakeApi({ relationships: cachedRows });

    renderList();

    // Each row is one link named by the customer; status, assessment and facts describe it.
    const link = await screen.findByRole("link", {
      name: "Parkview Dental Studio",
    });
    expect(link).toHaveAttribute("href", "/relationships/cust_2");
    expect(link).toHaveAccessibleDescription(
      /^Customer Not enough clear history to assess Latest interaction: 20 Aug 2026 · 2\sinteractions: Email, Note$/,
    );
    for (const each of screen.getAllByRole("link")) {
      expect(each).not.toHaveAttribute("aria-current");
    }
  });

  it("marks the open relationship as the current page and steps the headings down", async () => {
    fakeApi({ relationships: cachedRows });

    renderList("cust_2");

    const link = await screen.findByRole("link", {
      name: /Parkview Dental Studio/,
    });
    expect(link).toHaveAttribute("aria-current", "page");
    expect(
      screen.getByRole("heading", { level: 2, name: "Relationships" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: /^Action needed/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Northstar Dental Group/ }),
    ).not.toHaveAttribute("aria-current");
  });

  it("shows the empty message for a successful empty response, not an error", async () => {
    const api = fakeApi({ relationships: [] });

    renderList();

    expect(
      await screen.findByText("There are no relationships to show."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    // No count line and no groups.
    expect(screen.queryByText(/Action needed/)).not.toBeInTheDocument();
    expect(api.assessmentCalls).toEqual([]);
  });

  it("shows an error with Try again when loading fails, never the empty message", async () => {
    mockFetch({ status: 500, body: { detail: "Internal error" } });

    renderList();

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
      body: { relationships: cachedRows },
    });

    renderList();

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
    fakeApi({ relationships: cachedRows });

    const { rerender } = renderList("cust_2");
    const link = await screen.findByRole("link", {
      name: /Parkview Dental Studio/,
    });
    expect(link).not.toHaveFocus();

    rerender(
      <AssessmentsProvider>
        <RelationshipList selectedId={null} />
      </AssessmentsProvider>,
    );

    expect(link).toHaveFocus();
    expect(link).not.toHaveAttribute("aria-current");
  });
});

describe("RelationshipList grouping", () => {
  const rows = [
    row(
      "c_zeta",
      "zeta Dental",
      listed("action_needed", "Pricing got no reply."),
    ),
    row(
      "c_alpha",
      "Alpha Dental",
      listed("action_needed", "Demo not scheduled."),
    ),
    row(
      "c_wait",
      "Evergreen Dental",
      listed("waiting", "Waiting for the planning meeting."),
    ),
    row(
      "c_done",
      "Oak Dental",
      listed("no_action_needed", "The issue was resolved."),
    ),
    row(
      "c_beta",
      "beta Dental",
      listed("waiting", "Waiting for the budget decision."),
    ),
    row("c_thin", "Thin Clinic", insufficientEvidence),
  ];

  it("puts cached outcomes in their groups, in state order, alphabetical within each", async () => {
    const api = fakeApi({ relationships: rows });

    renderList();
    await screen.findByRole("link", { name: "Alpha Dental" });

    const headings = screen
      .getAllByRole("heading", { level: 2 })
      .map((heading) => heading.textContent);
    expect(headings).toEqual([
      "Action needed · 2",
      "Waiting · 2",
      "No action needed · 1",
      "Assessment unavailable · 1",
    ]);
    expect(namesIn(/^Action needed/)).toEqual(["Alpha Dental", "zeta Dental"]);
    expect(namesIn(/^Waiting/)).toEqual(["beta Dental", "Evergreen Dental"]);
    expect(namesIn(/^No action needed/)).toEqual(["Oak Dental"]);
    expect(namesIn(/^Assessment unavailable/)).toEqual(["Thin Clinic"]);

    // Each group says what its state means; each row shows the state as a word.
    expect(
      section(/^Waiting/).getByText(
        "The next step depends on something that has not happened yet.",
      ),
    ).toBeInTheDocument();
    expect(
      section(/^Action needed/).getByText("— Pricing got no reply."),
    ).toBeInTheDocument();
    const actionList = section(/^Action needed/).getByRole("list");
    expect(within(actionList).getAllByText("Action needed")).toHaveLength(2);

    // The unavailable row carries an explanation, never a state label.
    const unavailable = section(/^Assessment unavailable/);
    expect(
      unavailable.getByText("Not enough clear history to assess"),
    ).toBeInTheDocument();
    expect(
      unavailable.queryByText(/^(Action needed|Waiting|No action needed)$/),
    ).not.toBeInTheDocument();

    // Cached outcomes need no request.
    expect(api.assessmentCalls).toEqual([]);
    expect(screen.queryByRole("region", { name: /Assessing/ })).toBeNull();
  });

  it("shows every state in the count line, links the non-zero ones and the unavailable part", async () => {
    fakeApi({
      relationships: [
        row("c_1", "Alpha Dental", listed("action_needed", "Reply needed.")),
        row("c_2", "Thin Clinic", insufficientEvidence),
      ],
    });

    renderList();
    await screen.findByRole("link", { name: "Alpha Dental" });

    const countLine = screen.getByText(/0 Waiting/).closest("p");
    expect(countLine).toHaveTextContent(
      "1 Action needed · 0 Waiting · 0 No action needed — 1 assessment unavailable",
    );
    expect(
      within(countLine!).getByRole("link", { name: "1 Action needed" }),
    ).toHaveAttribute("href", "#relationships-action_needed");
    expect(
      within(countLine!).getByRole("link", {
        name: "1 assessment unavailable",
      }),
    ).toHaveAttribute("href", "#relationships-unavailable");
    expect(
      within(countLine!).queryByRole("link", { name: /Waiting/ }),
    ).not.toBeInTheDocument();
    expect(
      document.getElementById("relationships-unavailable"),
    ).toHaveTextContent("Assessment unavailable");
  });

  it("never turns a null assessment into a business state", async () => {
    fakeApi({ relationships: [row("c_1", "Alpha Dental", null)] });

    renderList();
    await screen.findByRole("link", { name: "Alpha Dental" });

    expect(namesIn(/^Assessing…/)).toEqual(["Alpha Dental"]);
    expect(screen.getByText(/0 Waiting/).closest("p")).toHaveTextContent(
      /^0 Action needed · 0 Waiting · 0 No action needed$/,
    );
    expect(
      screen.queryByRole("region", { name: /^No action needed/ }),
    ).toBeNull();
    expect(screen.queryByRole("region", { name: /unavailable/ })).toBeNull();
  });

  it("offers no action controls in the list", async () => {
    fakeApi({ relationships: rows });

    renderList();
    await screen.findByRole("link", { name: "Alpha Dental" });

    expect(screen.queryAllByRole("button")).toEqual([]);
    // Every link either opens a relationship or jumps to a group.
    for (const link of screen.getAllByRole("link")) {
      expect(link.getAttribute("href")).toMatch(
        /^(\/relationships\/|#relationships-)/,
      );
    }
    expect(document.body.textContent).not.toMatch(/confidence|score|priority/i);
  });
});

describe("RelationshipList assessment requests", () => {
  const nullRows = ["A", "B", "C", "D", "E"].map((letter) =>
    row(`c_${letter}`, `${letter} Dental`, null),
  );

  it("runs at most two requests at a time, in list order, each relationship once", async () => {
    const api = fakeApi({
      relationships: [
        ...nullRows,
        row("c_cached", "Cached Dental", listed("waiting", "Waiting.")),
      ],
    });

    renderList();

    // Facts show before any assessment finishes.
    expect(
      await screen.findByRole("link", { name: "E Dental" }),
    ).toBeInTheDocument();
    await waitFor(() => expect(api.active()).toEqual(["c_A", "c_B"]));
    expect(api.assessmentCalls).toEqual(["c_A", "c_B"]);

    await api.respond("c_A", { body: actionNeeded() });
    expect(api.active()).toEqual(["c_B", "c_C"]);

    await api.respond("c_C", { body: waiting() });
    expect(api.active()).toEqual(["c_B", "c_D"]);

    await api.respond("c_B", { body: noActionNeeded() });
    await api.respond("c_D", providerTimeout);
    expect(api.active()).toEqual(["c_E"]);
    await api.respond("c_E", { body: insufficientEvidence });

    expect(api.active()).toEqual([]);
    // Each null row once; the cached row never.
    expect(api.assessmentCalls).toEqual(["c_A", "c_B", "c_C", "c_D", "c_E"]);
  });

  it("shows Assessing only for rows whose request is in flight", async () => {
    const api = fakeApi({ relationships: nullRows.slice(0, 3) });

    renderList();
    await waitFor(() => expect(api.active()).toHaveLength(2));

    const assessing = section(/^Assessing…/);
    const rowText = (name: string) =>
      assessing.getByRole("link", { name }).textContent;
    expect(rowText("A Dental")).toContain("Assessing…");
    expect(rowText("B Dental")).toContain("Assessing…");
    expect(rowText("C Dental")).toContain("Waiting to be assessed");
    expect(rowText("C Dental")).not.toContain("Assessing");
  });

  it("moves a row from waiting to be assessed, to assessing, to its group", async () => {
    const api = fakeApi({ relationships: nullRows.slice(0, 3) });

    renderList();
    await waitFor(() => expect(api.active()).toHaveLength(2));
    const cRow = () => screen.getByRole("link", { name: "C Dental" });
    expect(cRow()).toHaveTextContent("Waiting to be assessed");

    await api.respond("c_A", { body: waiting() });
    expect(cRow()).toHaveTextContent("Assessing…");
    expect(namesIn(/^Waiting/)).toEqual(["A Dental"]);

    await api.respond("c_C", { body: actionNeeded("Pricing got no reply.") });
    expect(namesIn(/^Action needed/)).toEqual(["C Dental"]);
    expect(cRow()).toHaveTextContent("Action needed — Pricing got no reply.");
    expect(cRow()).not.toHaveTextContent("Assessing");
    expect(namesIn(/^Assessing…/)).toEqual(["B Dental"]);
  });

  it("announces the work once while it runs and once when it ends", async () => {
    const api = fakeApi({ relationships: nullRows.slice(0, 2) });

    renderList();
    await waitFor(() => expect(api.active()).toHaveLength(2));
    const announcement = () =>
      screen
        .getAllByRole("status")
        .find((status) => status.className.includes("sr-only"));
    expect(announcement()).toHaveTextContent("Assessing relationships…");

    await api.respond("c_A", { body: waiting() });
    expect(announcement()).toHaveTextContent("Assessing relationships…");
    await api.respond("c_B", { body: waiting() });
    expect(announcement()).toHaveTextContent("Assessments finished.");
  });

  it.each([
    [
      "timeout",
      providerTimeout,
      "Temporary problem — assessment could not be produced",
    ],
    [
      "provider error",
      providerError,
      "Temporary problem — assessment could not be produced",
    ],
    [
      "network failure",
      new TypeError("Failed to fetch"),
      "Temporary problem — assessment could not be produced",
    ],
    ["invalid output", invalidOutput, "Cause not known"],
    [
      "server error",
      { status: 500, body: { detail: "Internal error" } },
      "Cause not known",
    ],
    [
      "a body outside the contract",
      { body: { status: "assessed", state: "maybe" } },
      "Cause not known",
    ],
  ])(
    "moves a row whose request failed with %s to the unavailable section",
    async (_, reply, text) => {
      const api = fakeApi({ relationships: nullRows.slice(0, 1) });

      renderList();
      await waitFor(() => expect(api.active()).toEqual(["c_A"]));
      await api.respond("c_A", reply);

      const unavailable = section(/^Assessment unavailable/);
      expect(
        unavailable.getByRole("link", { name: "A Dental" }),
      ).toHaveTextContent(text);
      // The detail owns Try again; the row stays one clean link.
      expect(screen.queryByRole("button")).not.toBeInTheDocument();
      // Backend detail text is never shown.
      expect(document.body.textContent).not.toMatch(
        /provider|trusted|Internal error/,
      );
      expect(api.assessmentCalls).toEqual(["c_A"]);
    },
  );

  it("keeps focus on a row when its result moves it to another group", async () => {
    const api = fakeApi({ relationships: nullRows.slice(0, 2) });

    renderList();
    await waitFor(() => expect(api.active()).toHaveLength(2));
    screen.getByRole("link", { name: "B Dental" }).focus();

    await api.respond("c_B", { body: actionNeeded() });

    const moved = section(/^Action needed/).getByRole("link", {
      name: "B Dental",
    });
    expect(moved).toHaveFocus();
  });

  it("does not take focus when a row moves that was not focused", async () => {
    const api = fakeApi({ relationships: nullRows.slice(0, 2) });

    renderList();
    await waitFor(() => expect(api.active()).toHaveLength(2));
    const aLink = screen.getByRole("link", { name: "A Dental" });
    aLink.focus();

    await api.respond("c_B", { body: actionNeeded() });

    expect(aLink).toHaveFocus();
    expect(screen.getByRole("link", { name: "B Dental" })).not.toHaveFocus();
  });

  it("does not bring focus back after the owner moved it away", async () => {
    const api = fakeApi({ relationships: nullRows.slice(0, 1) });

    renderList();
    await waitFor(() => expect(api.active()).toHaveLength(1));
    const link = screen.getByRole("link", { name: "A Dental" });
    link.focus();
    link.blur();
    await Promise.resolve();

    await api.respond("c_A", { body: actionNeeded() });

    expect(document.body).toHaveFocus();
  });

  it("does not assess an unchanged relationship again when the list loads again", async () => {
    const api = fakeApi({ relationships: nullRows.slice(0, 2) });

    const view = renderList();
    await waitFor(() => expect(api.active()).toHaveLength(2));
    await api.respond("c_A", { body: waiting() });
    await api.respond("c_B", providerTimeout);

    // A new list instance under the same provider fetches the list again.
    view.rerender(
      <AssessmentsProvider>
        <RelationshipList key="again" selectedId={null} />
      </AssessmentsProvider>,
    );
    await screen.findByRole("link", { name: "A Dental" });
    await act(async () => {});

    expect(api.assessmentCalls).toEqual(["c_A", "c_B"]);
    expect(namesIn(/^Waiting/)).toEqual(["A Dental"]);
    expect(namesIn(/^Assessment unavailable/)).toEqual(["B Dental"]);
  });

  it("cancels running requests when the workspace unmounts", async () => {
    const api = fakeApi({ relationships: nullRows.slice(0, 3) });

    const view = renderList();
    await waitFor(() => expect(api.active()).toHaveLength(2));
    view.unmount();
    await act(async () => {});

    expect(api.active()).toEqual([]);
    // Nothing more starts after unmount.
    expect(api.assessmentCalls).toEqual(["c_A", "c_B"]);
  });
});
