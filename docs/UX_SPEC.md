# Customer Pulse — UX specification v0.2

Status: **Approved for MVP implementation.**

How the MVP works from the owner's point of view. Requirements come from the frozen PRD
(`docs/PRD.md`, v0.3). `docs/UI_RESEARCH.md` is evidence; "P14" and similar refer to its
section 5 table. This document does not decide architecture, APIs, data storage, frameworks,
AI output format or visual styling. Quoted copy is draft wording. Examples use the seeded data
and are illustrations, not expected AI output.

## 1. UX goals

1. **Find who needs attention fast.** `Action needed` relationships are visible without
   opening any of them.
2. **Keep the answers apart.** The three business states never look alike, and a missing
   assessment never looks like any of them.
3. **Understand one relationship quickly.** The detail shows the current situation first, then
   the facts and history behind it.
4. **Check, don't trust.** Every AI statement can be traced to the interactions behind it in
   one step.
5. **Suggest, never act.** Nothing suggests Customer Pulse will send, create, complete or
   dismiss anything.
6. **Stay calm.** Few items per row, plain words, no metric cards, badges or date urgency.
7. **Facts never wait.** Facts, contacts and history are usable whatever the assessment is
   doing.

## 2. Information architecture

Two views only:

```
Relationship list      all relationships, grouped by business state
Relationship detail    one relationship
  ├── Facts            name, status, record created date
  ├── Assessment       AI-generated: state, reason, summary, open items, next step
  ├── Contacts         name, role, email
  └── Interaction history
```

- No navigation menu, dashboard, settings, search or help page. The product name at the top
  leads back to the list.
- Each state's meaning is shown where the state is shown, so no help page is needed.
- An open relationship survives browser back, forward and reload.

## 3. Primary user flow

1. The owner opens Customer Pulse. The list appears.
2. The count line at the top shows how many relationships are in each state, and how many
   have no assessment. Each non-zero count jumps to its section.
3. The owner scans the `Action needed` group (first on the page): name, status, reason.
4. The owner opens a relationship. Wide screen: detail opens beside the list. Narrow screen:
   detail replaces the list.
5. Facts show at once. The assessment shows when ready.
6. The owner reads the assessment and opens "Based on" for any statement they want to check.
7. If needed, the owner reads contacts and the full history on the same page.
8. The owner decides what to do, outside Customer Pulse.
9. The owner goes back. The list keeps its scroll position and focus returns to the row they
   opened.

For `Waiting` and `No action needed`, reading the reason (and its "Based on" if unsure) is
usually enough to move on.

## 4. Relationship list

### Row content

1. **Customer name** — opens the relationship.
2. **Assessment** — the state as a text label with a one-sentence reason. For a `Waiting`
   relationship, the reason says what it is waiting for when the history supports it. A row
   without an assessment shows a neutral message instead (section 5).
3. **Status** — "Prospect" or "Customer".
4. **Latest interaction** — the most recent date and what happened on it.
   - One interaction on that date: date and type, for example
     "Latest interaction: 29 Aug 2026 · Note".
   - Several interactions on that date: date, count and their types as a set, for example
     "Latest interaction: 20 Aug 2026 · 2 interactions: Email, Note". No single type is picked
     as the latest. The types are listed in the PRD's fixed display order, which is only a
     stable way to list them and says nothing about which came first. Interaction ids are
     never used as evidence of order.
   - It is **information only**. It is not an urgency score. It never sorts, colours, flags or
     ranks a row, and its age never changes how the row looks.

Example:

> **Northstar Dental Group** · Prospect
> `Action needed` — The proposal sent on 23 Aug 2026 has had no response.
> Latest interaction: 29 Aug 2026 · Note

### Not in the list

Summary, open items, suggested action, "Based on" sources, contacts, note previews, record
created date, total interaction counts, relative times ("3 weeks ago"), overdue or age styling,
avatars, badges, confidence or health scores, and any action buttons. The row answers "who and
why"; suggestions are read in the detail, next to their evidence.

## 5. Grouping and finding attention

### Business-state groups

The list shows three groups, in this order, each with a heading, a count and a meaning line:

| Order | Heading | Meaning line |
| --- | --- | --- |
| 1 | `Action needed` | "The history shows something to consider doing now." |
| 2 | `Waiting` | "The next step depends on something that has not happened yet." |
| 3 | `No action needed` | "The history shows nothing needs doing right now." |

- Rows within a group are in **alphabetical order** by customer name.
- Empty groups are hidden. The count line still shows "0" for each state, as plain text.
- No filter controls in the MVP.

### Relationships without an assessment

`Assessment unavailable` is the PRD fallback condition, **not** a fourth business state. These
relationships sit in a separate section after the three groups, headed "Assessment
unavailable", with the line "Customer Pulse could not produce a trustworthy assessment for
these relationships. Their facts and history are still available."

- The section looks different from the state groups: its heading is not styled as a state,
  and its rows carry no state label.
- Each row shows a neutral explanation in place of a state and reason:
  - "No interaction history"
  - "Not enough clear history to assess"
  - "Temporary problem — assessment could not be produced"
  - "Cause not known"
- The count line lists it apart from the states, for example:
  "2 Action needed · 3 Waiting · 2 No action needed — 1 assessment unavailable". That last
  part links to the section and appears only when the number is above zero.
- While assessments load, rows without a result sit in a separate "Assessing…" area, also
  outside the state groups, just before the unavailable section. When a result arrives, the
  row moves to its group or to the unavailable section. Focus does not move and the page does
  not jump.

### Why

- `Action needed` is always first, so the main question needs no clicks.
- Alphabetical order means nothing, so it cannot suggest a priority the assessment does not
  give. Order comes only from the state. Dates never sort or rank, and a passing date changes
  nothing.
- A separate section means a missing answer cannot be read as "wait" or "nothing to do".

### Trade-offs

- **Separate "Assessment unavailable" section.** It sits at the bottom, so it is below
  `No action needed`, and an owner who only scans the top may miss it. The count line link and
  the distinct heading make it findable, but it is less visible than a group near the top. We
  accept this so it never reads as a peer of the business states.
- **Alphabetical order.** No "most pressing first" within `Action needed`.
- **Loading.** Rows move out of the "Assessing…" area as assessments finish.
- **No filter.** A long list needs scrolling. Revisit if the data grows.

## 6. Relationship detail

One page, no tabs, in this order:

1. **Facts** — name (page heading), status, "Record created 12 May 2026". On narrow screens,
   a "Back to all relationships" link.
2. **Assessment** (section 7), with a subtle label: "AI assessment, based on this
   relationship's interaction history". It is visually set apart from the facts so AI
   interpretation is never mistaken for recorded data.
3. **Contacts** — name, role, email. Email is plain, selectable text, not a link. No contact
   is marked as "primary". None: "No contacts recorded for this relationship."
4. **Interaction history** (section 9).

On wide screens, contacts may sit beside the facts, as long as the reading order stays the
same.

## 7. AI assessment

### For all states

- The state is a text label followed by its meaning line. Colour may support it, never
  replace it.
- Parts shown: reason, summary, open items, next step (as the state allows). Each part has its
  own "Based on" control (section 8).
- Open items are one line each. With several contacts, each item names its contact. Empty:
  "No open items."
- No confidence score. No buttons except "Based on" controls: no done, dismiss, snooze, send,
  schedule or create.
- No sender or direction presented as fact.

### Per state

| State | Next step | Must not imply |
| --- | --- | --- |
| `Action needed` | One, labelled "Suggested next action", followed by "A suggestion only. Customer Pulse does not do this for you." | That Customer Pulse will act, or that anything is overdue. |
| `Waiting` | The assessment makes clear what the relationship is waiting for, whenever the history supports it. If a next step is given, it is shown after that waiting condition and worded so it clearly applies only once the event or condition happens. | Acting before the event. No countdown, "due" or "overdue" wording. A mentioned date that has passed changes nothing. Not the same as "nothing to do". |
| `No action needed` | None: "No next action suggested." | That the relationship is "healthy" or should never be contacted. |

The UX does not need a particular AI output format for the waiting condition. It can be
part of the reason or shown on its own, as long as the owner can see it.

### Assessment unavailable

Shown in the detail in place of the assessment. It shows **no** state, reason, summary, open
items, suggestion or "Based on". It looks neutral, not like a state. The history below is
unchanged.

| Cause (when known) | Message |
| --- | --- |
| No interactions | "There is no interaction history to assess." |
| Not enough clear context | "The history does not give enough clear information for a trustworthy assessment. Read the history below to decide." |
| Temporary failure | "The assessment could not be produced because of a temporary problem. The facts and history below are not affected." |
| Cause not known | "Customer Pulse could not produce a trustworthy assessment. Read the history below to decide." |

All four are the same PRD fallback. The different wording only helps the owner know whether
reading the history themselves is the answer (thin context) or whether trying later may help
(failure).

### Loading

- Detail: "Assessing this relationship…" in the assessment area. Everything else is usable.
- List: the row sits in the "Assessing…" area (section 5).
- The result replaces the loading message in place, without moving focus or scrolling, and is
  announced politely to screen readers.

## 8. Evidence and traceability

### Pattern: collapsed "Based on" per part

- The reason, the summary, each open item and the suggested action each have one small
  control: "Based on 2 interactions". It starts collapsed.
- Opening it shows a compact list of those interactions: type, date and contact
  ("Email · 23 Aug 2026 · Sarah Mitchell"). Each item can:
  - **show the original note** in place, word for word as recorded, and
  - **"Show in history"**: jump to that interaction in the history, where it is marked with
    text (not colour alone). A "Back to assessment" link returns to where the owner was.
- Only original notes are shown as evidence. No AI-picked quotes.
- Interactions with empty notes are never listed.
- A part with no supporting interactions is not shown; an assessment that cannot be traced is
  Assessment unavailable.

### Trade-off

Evidence is one click away instead of always visible. This keeps the assessment short and
easy to scan. The cost is that the owner must choose to check. Two levels (list of sources,
then the note) keep an open "Based on" short even when it cites several interactions.
Rejected: evidence always expanded (too heavy), marking cited items only inside the history
(forces page jumps, hard on phones and screen readers), and hover pop-ups (no touch or
keyboard support).

## 9. Interaction history

- **Newest date first**, so the current context is at the top.
- **Grouped under date headings** ("22 Aug 2026"). Each date appears once.
- Each interaction shows its type as a word, "Contact: Sarah Mitchell, Owner", and the full
  notes as plain text (text in notes never becomes links, formatting or instructions). Never
  "From" or "To". Empty notes: "No notes recorded."
- Interaction ids are never shown and never used to suggest order.

### Same-date interactions

- Listed under their shared date heading, in the PRD's fixed display order, which is only for
  a stable layout.
- No numbers, arrows, connecting lines or "then/later" wording between them. Any line joining
  dates connects date headings only.
- When a date has more than one interaction, the heading says: "2 interactions — order within
  this date is not known."

> **20 Aug 2026** — 2 interactions — order within this date is not known
> Email · Contact: Chris Evans, Dentist — "Chris replied that pricing looks reasonable…"
> Note · Contact: Chris Evans, Dentist — "Need to confirm onboarding timeline…"

**Trade-off:** newest first puts the latest context at the top, but reading the story from the
start means scrolling down and reading upwards. The assessment summary covers most of that
need.

## 10. Product states

| State | Behaviour |
| --- | --- |
| List loading | "Loading relationships…". No placeholder rows with made-up content. |
| Detail loading | "Loading relationship…". |
| Assessment loading | Section 7. Facts and history never wait. |
| Assessment unavailable | Sections 5 and 7. Facts, contacts and history still show. |
| No interactions | List: "No interaction history" in the "Assessment unavailable" section; latest interaction reads "No interactions yet". Detail: assessment message from section 7; history reads "No interactions recorded for this relationship." |
| No contacts | "No contacts recorded for this relationship." |
| Thin or unclear history | No special state. If the history clearly supports a business state, that state shows with its evidence; otherwise it is `Assessment unavailable` with "Not enough clear context". Missing or weak evidence is never shown as `No action needed`. |
| List fails to load | "Customer Pulse could not load your relationships. Try again." with a "Try again" button. Never the empty-list message. |
| Detail fails to load | "Customer Pulse could not load this relationship." with "Try again" and a back link. |
| Part of the detail fails to load | That area shows its own error with "Try again"; the rest still shows. A failed load is never shown as "No interactions" or "No contacts". |
| Relationship not found | "This relationship could not be found." with a back link. |
| No relationships | "There are no relationships to show." No count line, no groups, no "add" prompt. |

"Try again" only asks for the same data again. It never changes data.

## 11. Responsive behaviour

Desktop and laptop are the primary context for the information design. That is a design
priority. It does not conflict with writing responsive styles mobile-first; this document does
not decide how styles are written.

| | Wide screens | Narrow screens |
| --- | --- | --- |
| Layout | List and detail side by side; the list stays visible. | Separate screens. Back returns to the same list position. |
| Nothing selected | "Select a relationship to see its details." Nothing opens by itself. | List only. |
| Content | Same rows, same detail order, same "Based on" behaviour. | Same. Nothing is dropped. |

- The layout switches when the detail would be too narrow to read. The exact width is decided
  later.
- Nothing is available only on hover. Controls are easy to tap. The page never scrolls
  sideways, even with long notes or email addresses.

## 12. Accessibility and clarity

- One main heading per view, headings in order. The list is a real list, and each row is one
  link named by the customer.
- State, status and interaction type are always words. "Based on" controls say what they
  cover ("Based on 2 interactions, for the reason") and whether they are open.
- Keyboard only works end to end with visible focus. Opening a relationship moves focus to its
  heading; going back returns it to the row.
- No meaning by colour alone.
- Loading and "assessment ready" are announced without moving focus.
- Plain words, no short forms ("N/A", "TBD", ids). Dates use the month as a word
  ("23 Aug 2026"). Empty values get a sentence, never a dash.

## 13. Out of scope

- Creating, editing, deleting or importing data. Sign-in, users, more than one workspace.
- Correcting, dismissing, snoozing, completing or rating an assessment.
- Tasks, reminders, notifications, badges, scheduling, calendar views.
- Email, messaging, calling, drafting, campaigns, or links that start them.
- Deals, pipeline, reports, analytics, charts, business-number dashboards, AI chat.
- Search, saved views, custom sorting, filters.
- Any date-based urgency: overdue, due today, "no contact in N days", relative times.
- Showing when an assessment was produced (timing belongs to the technical design).
- Visual styling: colours, fonts, spacing, icons, components.

## 14. Decisions and trade-offs

| Decision | Why | Trade-off |
| --- | --- | --- |
| Two views: list and detail | All the PRD needs. | Extras need a new decision. |
| Group by business state; alphabetical within | `Action needed` first; order carries no false priority. | No "most pressing first". |
| `Assessment unavailable` relationships in a separate section after the groups | Never reads as a fourth state or as "nothing to do". | Lower on the page; relies on the count line and a distinct heading to be found. |
| Unavailable message varies by cause, when known | Tells the owner whether to read the history or try later. | Four messages to write and test; all are the same fallback. |
| Count line as navigation, no filters | Enough for a small list. | Long lists need scrolling. |
| Latest interaction shown as information only; a shared date shows the count and all its types | Useful context without urgency or false order; still shows type as FR-1.1 requires. | Slightly longer row. |
| Side by side on wide screens, separate screens on narrow | Fast switching on desktop; readable on phones. | Two layouts to check. |
| One detail page, no tabs: facts → assessment → contacts → history | Evidence always reachable. | Longer page. |
| Subtle "AI assessment" label, set apart from facts; no confidence score | AI interpretation stays separate from recorded data. | Owner judges certainty only from the evidence. |
| Collapsed "Based on" per part, then note in place or jump to history | Traceable without a heavy assessment. | Evidence takes a click. |
| History newest date first, grouped by date | Current context first; same-date items share a heading with no false order. | Reading the story from the start runs bottom to top. |
| Email as plain text | No communication actions. | Owner copies the address. |

## 15. UX acceptance checklist

**List**

- [ ] Every relationship shows name, "Prospect"/"Customer", state or unavailable explanation,
      and latest interaction date and type.
- [ ] A latest date shared by several interactions shows the date, the count and all their
      types, with none presented as the latest (for example Parkview Dental Studio,
      20 Aug 2026).
- [ ] Groups appear as `Action needed`, `Waiting`, `No action needed`, with rows in
      alphabetical order.
- [ ] Relationships with an unavailable assessment appear only in the separate
      "Assessment unavailable" section,
      with no state label, and the count line links to it.
- [ ] The count line shows all three states (including 0) and non-zero counts jump to their
      group.
- [ ] No row shows a suggestion, note preview, relative time, overdue marker, badge or score.
- [ ] Changing the device date changes no row's group, order or look.

**Detail and assessment**

- [ ] Facts, contacts and history show while the assessment is still loading.
- [ ] Order is facts, assessment, contacts, history on all screen sizes.
- [ ] The assessment carries an "AI assessment" label and looks separate from the facts.
- [ ] `Action needed` shows one suggested action with the "suggestion only" note.
- [ ] `Waiting` makes clear what it waits for (when the history supports it), and any next
      step clearly applies only after that.
- [ ] `No action needed` shows "No next action suggested".
- [ ] Assessment unavailable shows no state, reason, summary, open items, suggestion or
      "Based on", and shows the message for its cause.
- [ ] A customer with no interactions says there is no interaction history to assess.
- [ ] With several contacts, each open item names its contact.
- [ ] No button sends, calls, schedules, creates, edits, deletes, dismisses, snoozes or
      completes anything. Emails are not links.

**Evidence**

- [ ] Reason, summary, each open item and the suggested action each have a collapsed
      "Based on" control.
- [ ] Opening it lists the supporting interactions; each can show its original note or jump
      to it in the history, where it is marked with text.
- [ ] No interaction with empty notes is listed.

**History**

- [ ] Dates run newest first, each date once as a heading.
- [ ] A date with several interactions says order within the date is not known, and nothing
      numbers or connects those items.
- [ ] Each interaction shows type, contact and full notes, with no "from"/"to" wording.

**States, layout, access**

- [ ] A failed list load shows an error with "Try again", not the empty message.
- [ ] A failed history load shows an error, not "No interactions".
- [ ] With no relationships, the list says so and offers no "add" prompt.
- [ ] Wide screen: list and detail side by side, nothing opens by itself.
- [ ] Phone: separate screens, back keeps list position, no sideways scrolling.
- [ ] The whole flow works by keyboard with visible focus; focus returns to the row on back.
- [ ] No meaning depends on colour alone; assessment loading results are announced.

## Open questions

These do not block review, and none needs a PRD change.

1. **Knowing the cause of an unavailable assessment.** The varied messages in section 7 apply
   only if the technical design can tell the causes apart. Otherwise the "cause not known"
   message is used.
2. **"Try again" for a failed assessment.** This depends on when assessments are produced
   (technical design). If offered, it appears only for a temporary failure.
