import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  actionNeeded,
  claim,
  fakeApi,
  insufficientEvidence,
  invalidOutput,
  providerError,
  providerTimeout,
} from "@/test/fake-api";
import { mockFetch } from "@/test/mock-fetch";

import { AssessmentsProvider } from "../assessments";
import { RelationshipDetail } from "./relationship-detail";
import { RelationshipList } from "./relationship-list";

// An assessment reply the facts-only tests do not need: it succeeds as unavailable.
const pendingAssessment = { body: { status: "unavailable", cause: "insufficient_evidence" } };

function renderDetail(id: string) {
  return render(
    <AssessmentsProvider>
      <RelationshipDetail id={id} />
    </AssessmentsProvider>,
  );
}

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
    mockFetch({ body: detail }, pendingAssessment);

    renderDetail("cust_9");

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
    mockFetch({ body: detail }, pendingAssessment);

    renderDetail("cust_9");

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
    mockFetch({ body: detail }, pendingAssessment);

    const { unmount } = renderDetail("cust_9");
    await screen.findByRole("heading", { name: "Parkview Dental Studio" });

    expect(document.title).toBe("Parkview Dental Studio · Customer Pulse");

    unmount();

    expect(document.title).toBe("Customer Pulse");
  });

  it("moves focus to the relationship heading once it has loaded", async () => {
    mockFetch({ body: detail }, pendingAssessment);

    renderDetail("cust_9");

    expect(
      await screen.findByRole("heading", { name: "Parkview Dental Studio" }),
    ).toHaveFocus();
  });

  it("offers no actions: nothing sends, creates, edits or deletes", async () => {
    mockFetch({ body: detail }, pendingAssessment);

    renderDetail("cust_9");
    await screen.findByRole("heading", { name: "Parkview Dental Studio" });

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(1);
    expect(
      screen.getByRole("link", { name: "Back to all relationships" }),
    ).toHaveAttribute("href", "/");
  });

  it("says when there are no contacts and no interactions", async () => {
    mockFetch(
      { body: { ...detail, contacts: [], interactions: [] } },
      { body: { status: "unavailable", cause: "no_interactions" } },
    );

    renderDetail("cust_9");

    expect(
      await screen.findByText("No contacts recorded for this relationship."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No interactions recorded for this relationship."),
    ).toBeInTheDocument();
  });

  it("shows a not-found message with a way back for a 404", async () => {
    mockFetch({ status: 404, body: { detail: "Relationship not found" } });

    renderDetail("cust_999");

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
    mockFetch(
      { status: 500, body: { detail: "Internal error" } },
      { body: detail },
      pendingAssessment,
    );

    renderDetail("cust_9");

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

    // Assessment requests stay open; this test is about the facts.
    fetchMock.mockReturnValue(new Promise(() => {}));

    const { rerender } = renderDetail("cust_9");
    rerender(
      <AssessmentsProvider>
        <RelationshipDetail id="cust_2" />
      </AssessmentsProvider>,
    );
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

// --- the assessment in the detail ---

function assessmentRegion() {
  return within(screen.getByRole("region", { name: "Assessment" }));
}

function statusLine() {
  return assessmentRegion().getByRole("status");
}

async function openDetail(body: unknown = detail) {
  const api = fakeApi({ details: { cust_9: body } });
  renderDetail("cust_9");
  await screen.findByRole("heading", { level: 1, name: "Parkview Dental Studio" });
  await waitFor(() => expect(api.active()).toEqual(["cust_9"]));
  return api;
}

const actionNeededDetail = {
  status: "assessed",
  state: "action_needed",
  summary: claim("Pricing looks reasonable and a timeline was asked for.", "int_39", "int_40"),
  // A repeated id is one supporting interaction.
  reason: claim("The onboarding timeline is not confirmed.", "int_40", "int_39", "int_40"),
  open_items: [
    {
      text: "Confirm the onboarding timeline.",
      evidence: ["int_40"],
      contact_ids: ["contact_10"],
    },
  ],
  next_action: claim("Confirm the onboarding timeline with Chris.", "int_40"),
};

const waitingDetail = {
  status: "assessed",
  state: "waiting",
  summary: claim("A demo was completed.", "int_38"),
  reason: claim("Waiting for the planning meeting.", "int_38"),
  open_items: [],
  waiting_for: claim("The September planning meeting.", "int_38"),
  next_action: claim("After the meeting, ask about the budget.", "int_38"),
};

const noActionDetail = {
  status: "assessed",
  state: "no_action_needed",
  summary: claim("The pricing question was answered.", "int_39"),
  reason: claim("Chris said pricing looks reasonable.", "int_39"),
  open_items: [],
};

describe("RelationshipDetail assessment", () => {
  it("shows facts, contacts and history while the assessment is being produced", async () => {
    await openDetail();

    expect(statusLine()).toHaveTextContent("Assessing this relationship…");
    expect(
      assessmentRegion().getByText(
        "AI assessment, based on this relationship’s interaction history",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Contacts" })).toBeInTheDocument();
    expect(screen.getByText("Demo completed.")).toBeInTheDocument();
    // Order: facts, assessment, contacts, history.
    expect(
      screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent),
    ).toEqual(["Assessment", "Contacts", "Interaction history"]);
    // Opening the detail still focuses its heading, not the assessment.
    expect(
      screen.getByRole("heading", { level: 1, name: "Parkview Dental Studio" }),
    ).toHaveFocus();
  });

  it("shows an Action needed assessment with every part and a suggestion note", async () => {
    const api = await openDetail();

    await api.respond("cust_9", { body: actionNeededDetail });

    const region = assessmentRegion();
    expect(statusLine()).toHaveTextContent("Assessment ready.");
    expect(region.getByText("Action needed")).toBeInTheDocument();
    expect(
      region.getByText("The history shows something to consider doing now."),
    ).toBeInTheDocument();
    expect(
      region.getAllByRole("heading", { level: 3 }).map((h) => h.textContent),
    ).toEqual(["Reason", "Summary", "Open items", "Suggested next action"]);
    expect(
      region.getByText("The onboarding timeline is not confirmed."),
    ).toBeInTheDocument();
    expect(region.getByText("Confirm the onboarding timeline.")).toBeInTheDocument();
    // Contact ids become names from the facts; ids are never shown.
    expect(region.getByText("Contact: Chris Evans, Dentist")).toBeInTheDocument();
    expect(
      region.getByText("Confirm the onboarding timeline with Chris."),
    ).toBeInTheDocument();
    expect(
      region.getByText("A suggestion only. Customer Pulse does not do this for you."),
    ).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/contact_10|int_\d+|confidence/);
    // The focus stays where the owner left it.
    expect(
      screen.getByRole("heading", { level: 1, name: "Parkview Dental Studio" }),
    ).toHaveFocus();
  });

  it("shows what a Waiting relationship waits for before any next step", async () => {
    const api = await openDetail();

    await api.respond("cust_9", { body: waitingDetail });

    const region = assessmentRegion();
    expect(region.getByText("Waiting")).toBeInTheDocument();
    expect(
      region.getAllByRole("heading", { level: 3 }).map((h) => h.textContent),
    ).toEqual([
      "Reason",
      "Summary",
      "Open items",
      "Waiting for",
      "Suggested next action, once that happens",
    ]);
    expect(region.getByText("The September planning meeting.")).toBeInTheDocument();
    expect(region.getByText("No open items.")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/overdue|due\b/i);
  });

  it("shows No action needed with no suggested action", async () => {
    const api = await openDetail();

    await api.respond("cust_9", { body: noActionDetail });

    const region = assessmentRegion();
    expect(region.getByText("No action needed")).toBeInTheDocument();
    expect(region.getByText("No next action suggested.")).toBeInTheDocument();
    expect(region.queryByText(/Suggested next action/)).not.toBeInTheDocument();
    expect(region.queryByText(/A suggestion only/)).not.toBeInTheDocument();
  });

  it("offers only Based on controls: no action buttons", async () => {
    const api = await openDetail();

    await api.respond("cust_9", { body: actionNeededDetail });

    const buttonNames = screen
      .getAllByRole("button")
      .map((button) => button.textContent);
    expect(new Set(buttonNames)).toEqual(new Set(["Show in history: Email, 20 Aug 2026", "Show in history: Note, 20 Aug 2026"]));
    expect(document.body.textContent).not.toMatch(
      /send email|schedule a|dismiss|snooze|mark done|mark as done/i,
    );
  });

  it("shows insufficient evidence as unavailable, with the history and no Try again", async () => {
    const api = await openDetail();

    await api.respond("cust_9", { body: insufficientEvidence });

    const region = assessmentRegion();
    expect(
      region.getByText(
        "The history does not give enough clear information for a trustworthy assessment. Read the history below to decide.",
      ),
    ).toBeInTheDocument();
    expect(statusLine()).toHaveTextContent("Assessment unavailable.");
    expect(region.queryByText(/^(Action needed|Waiting|No action needed)$/)).toBeNull();
    expect(region.queryByText(/Based on/)).toBeNull();
    expect(region.queryByText(/No next action suggested/)).toBeNull();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByText("Demo completed.")).toBeInTheDocument();
  });

  it.each([
    ["a provider timeout", providerTimeout],
    ["a provider error", providerError],
    ["a network failure", new TypeError("Failed to fetch")],
  ])("offers Try again after %s and retries only this relationship", async (_, failure) => {
    const api = await openDetail();

    await api.respond("cust_9", failure);

    const region = assessmentRegion();
    expect(
      region.getByText(
        "The assessment could not be produced because of a temporary problem. The facts and history below are not affected.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Contacts" })).toBeInTheDocument();
    expect(screen.getByText("Demo completed.")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/provider|Failed to fetch/);

    fireEvent.click(region.getByRole("button", { name: "Try again" }));

    expect(statusLine()).toHaveTextContent("Assessing this relationship…");
    expect(screen.getByRole("heading", { name: "Assessment" })).toHaveFocus();
    expect(api.assessmentCalls).toEqual(["cust_9", "cust_9"]);

    await api.respond("cust_9", { body: actionNeededDetail });
    expect(assessmentRegion().getByText("Action needed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
  });

  it.each([
    ["invalid output", invalidOutput],
    ["a server error", { status: 500, body: { detail: "Internal error" } }],
    ["a body outside the contract", { body: { ...noActionDetail, next_action: claim("Call.", "int_39") } }],
  ])("shows the cause-not-known message with no Try again after %s", async (_, failure) => {
    const api = await openDetail();

    await api.respond("cust_9", failure);

    expect(
      assessmentRegion().getByText(
        "Customer Pulse could not produce a trustworthy assessment. Read the history below to decide.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByText(/Internal error|trusted/)).toBeNull();
    expect(screen.getByText("Demo completed.")).toBeInTheDocument();
  });

  it.each([
    ["an interaction this relationship does not have", { ...noActionDetail, reason: claim("Resolved.", "int_999") }],
    ["an interaction with empty notes", { ...noActionDetail, reason: claim("Resolved.", "int_36") }],
    [
      "a contact this relationship does not have",
      {
        ...actionNeededDetail,
        open_items: [{ text: "Confirm.", evidence: ["int_40"], contact_ids: ["contact_99"] }],
      },
    ],
  ])("does not show an assessment that cites %s", async (_, body) => {
    const api = await openDetail();
    const logged = vi.spyOn(console, "error");
    const warned = vi.spyOn(console, "warn");
    const info = vi.spyOn(console, "log");

    await api.respond("cust_9", { body });

    const region = assessmentRegion();
    expect(
      region.getByText(
        "Customer Pulse could not produce a trustworthy assessment. Read the history below to decide.",
      ),
    ).toBeInTheDocument();
    expect(region.queryByText(/Resolved|Confirm\./)).toBeNull();
    expect(document.body.textContent).not.toMatch(/contact_99|int_999/);
    // Fails safely without writing ids or payloads to the browser console.
    expect(logged).not.toHaveBeenCalled();
    expect(warned).not.toHaveBeenCalled();
    expect(info).not.toHaveBeenCalled();
  });
});

function summaryNamed(container: HTMLElement, name: string) {
  return within(container).getByText(
    (_, element) =>
      element?.tagName === "SUMMARY" && element.textContent === name,
  );
}

describe("RelationshipDetail evidence", () => {
  async function openEvidence() {
    const api = await openDetail();
    await api.respond("cust_9", { body: actionNeededDetail });
    // The summary also cites two interactions; this is the reason's control.
    return screen.getByText(
      (_, element) =>
        element?.tagName === "SUMMARY" &&
        element.textContent === "Based on 2 interactions, for the reason",
    );
  }

  it("starts closed, counts unique interactions and says what it covers", async () => {
    const control = await openEvidence();

    const details = control.closest("details")!;
    expect(details).not.toHaveAttribute("open");
    expect(summaryNamed(details, "Show note: Email, 20 Aug 2026")).not.toBeVisible();

    fireEvent.click(control);

    expect(details).toHaveAttribute("open");
    // One date heading; the two same-date sources are marked as unordered.
    const dateLabels = within(details)
      .getAllByText(/Aug 2026/, { selector: "p" })
      .map((label) => label.textContent);
    expect(dateLabels).toEqual([
      "20 Aug 2026 — 2 interactions — order within this date is not known",
    ]);
    expect(within(details).getByText("Note · Chris Evans")).toBeVisible();
    expect(within(details).getByText("Email · Chris Evans")).toBeVisible();
    expect(details.textContent).not.toMatch(/int_\d+|e_[0-9a-f]{10}/);
  });

  it("shows the original note in place", async () => {
    const control = await openEvidence();
    fireEvent.click(control);
    const details = control.closest("details")!;
    const noteControl = summaryNamed(details, "Show note: Note, 20 Aug 2026");
    const note = within(details).getByText("Need to confirm onboarding timeline.");
    expect(note).not.toBeVisible();

    fireEvent.click(noteControl);

    expect(note).toBeVisible();
  });

  it("jumps to the interaction in the history, marks it with text, and comes back", async () => {
    const control = await openEvidence();
    fireEvent.click(control);

    fireEvent.click(
      within(control.closest("details")!).getByRole("button", {
        name: "Show in history: Email, 20 Aug 2026",
      }),
    );

    const history = within(screen.getByRole("region", { name: "Interaction history" }));
    const item = history
      .getByText("Chris replied that pricing looks reasonable.")
      .closest("li")!;
    expect(item).toHaveFocus();
    expect(within(item).getByText("Shown from the assessment")).toBeInTheDocument();
    expect(history.getAllByText("Shown from the assessment")).toHaveLength(1);

    fireEvent.click(within(item).getByRole("button", { name: "Back to assessment" }));

    expect(control).toHaveFocus();
    expect(history.queryByText("Shown from the assessment")).toBeNull();
  });
});

describe("Assessments shared by the list and the detail", () => {
  const listRow = (id: string, name: string, assessment: unknown) => ({
    id,
    name,
    status: "prospect",
    latest_interaction: { date: "2026-08-20", count: 1, types: ["note"] },
    assessment,
  });

  function renderWorkspace(id: string | null) {
    const tree = (openId: string | null) => (
      <AssessmentsProvider>
        <RelationshipList selectedId={openId} />
        {openId && <RelationshipDetail id={openId} />}
      </AssessmentsProvider>
    );
    const view = render(tree(id));
    return { ...view, open: (openId: string) => view.rerender(tree(openId)) };
  }

  it("a detail opened by URL shares the list's request instead of making a second one", async () => {
    const api = fakeApi({
      relationships: [listRow("cust_9", "Parkview Dental Studio", null)],
      details: { cust_9: detail },
    });

    renderWorkspace("cust_9");
    await screen.findByRole("heading", { level: 1, name: "Parkview Dental Studio" });
    await waitFor(() => expect(api.active()).toEqual(["cust_9"]));
    await act(async () => {});

    expect(api.assessmentCalls).toEqual(["cust_9"]);

    await api.respond("cust_9", { body: actionNeededDetail });

    // Both views show the one result.
    expect(assessmentRegion().getByText("Action needed")).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: /^Action needed/ }),
    ).toHaveTextContent("Parkview Dental Studio");
    expect(api.assessmentCalls).toEqual(["cust_9"]);
  });

  it("reuses a result the list already requested, with no new request", async () => {
    const api = fakeApi({
      relationships: [listRow("cust_9", "Parkview Dental Studio", null)],
      details: { cust_9: detail },
    });
    const view = renderWorkspace(null);
    await waitFor(() => expect(api.active()).toEqual(["cust_9"]));
    await api.respond("cust_9", { body: actionNeededDetail });

    view.open("cust_9");
    await screen.findByRole("heading", { level: 1, name: "Parkview Dental Studio" });

    expect(assessmentRegion().getByText("Action needed")).toBeInTheDocument();
    expect(api.assessmentCalls).toEqual(["cust_9"]);
  });

  it("uses an unavailable cause from the list with no request", async () => {
    const api = fakeApi({
      relationships: [
        listRow("cust_9", "Parkview Dental Studio", {
          status: "unavailable",
          cause: "no_interactions",
        }),
      ],
      details: { cust_9: { ...detail, interactions: [] } },
    });
    const view = renderWorkspace(null);
    await screen.findByRole("link", { name: "Parkview Dental Studio" });

    view.open("cust_9");
    await screen.findByRole("heading", { level: 1, name: "Parkview Dental Studio" });

    expect(
      assessmentRegion().getByText("There is no interaction history to assess."),
    ).toBeInTheDocument();
    expect(api.assessmentCalls).toEqual([]);
  });

  it("asks once for the full result of a row the list already shows, without moving the row", async () => {
    const api = fakeApi({
      relationships: [
        listRow("cust_9", "Parkview Dental Studio", {
          status: "assessed",
          state: "action_needed",
          reason: "The onboarding timeline is not confirmed.",
        }),
      ],
      details: { cust_9: detail },
    });
    const view = renderWorkspace(null);
    await screen.findByRole("link", { name: "Parkview Dental Studio" });
    expect(api.assessmentCalls).toEqual([]);

    view.open("cust_9");
    await waitFor(() => expect(api.active()).toEqual(["cust_9"]));

    // The row keeps its stored state while the detail loads the rest.
    expect(
      screen.getByRole("region", { name: /^Action needed/ }),
    ).toHaveTextContent("Parkview Dental Studio");
    expect(screen.queryByRole("region", { name: /^Assessing/ })).toBeNull();

    await api.respond("cust_9", { body: actionNeededDetail });
    expect(assessmentRegion().getByText("Confirm the onboarding timeline.")).toBeInTheDocument();
    expect(api.assessmentCalls).toEqual(["cust_9"]);
  });

  it("puts the open relationship next in line, still two at a time", async () => {
    const api = fakeApi({
      relationships: [
        listRow("c_a", "A Dental", null),
        listRow("c_b", "B Dental", null),
        listRow("c_c", "C Dental", null),
        listRow("cust_9", "Parkview Dental Studio", null),
      ],
      details: { cust_9: detail },
    });
    const view = renderWorkspace(null);
    await waitFor(() => expect(api.active()).toEqual(["c_a", "c_b"]));

    view.open("cust_9");
    await screen.findByRole("heading", { level: 1, name: "Parkview Dental Studio" });
    expect(api.active()).toEqual(["c_a", "c_b"]);
    // Queued, not yet running.
    expect(statusLine()).toHaveTextContent("Waiting to be assessed.");
    expect(statusLine()).not.toHaveTextContent("Assessing");

    await api.respond("c_a", { body: actionNeeded() });

    expect(api.active()).toEqual(["c_b", "cust_9"]);
    expect(statusLine()).toHaveTextContent("Assessing this relationship…");
  });
});
