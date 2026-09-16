# Customer Pulse — UI research: Practice by Numbers

Status: Complete for MVP UX planning.

Research notes on how one existing product, Practice by Numbers (PbN), presents relationship
and attention information to dental practices. They fed the UX design in `docs/UX_SPEC.md`.
They are not requirements: the frozen PRD decides what Customer Pulse does, and section 4 marks
every pattern that would need something the PRD rules out as **Avoid** or **Not relevant**.

All sources were read on 2026-09-16 and are listed in section 6. Throughout:

- **Observed** means written in the source or visible in a screenshot the source published.
  Screenshots were opened and looked at directly.
- **Interpretation** means our reading of what we observed.
- Quoted text is copied from the source, except the Capterra points in section 3, which are
  paraphrased.

## 1. Limits of the evidence

- Only public pages were used. We had no account and saw no live product.
- The Desktop App screenshots show 2024 dates ("Last Update: 08/01/2024"). The guide page was
  last updated on 28 May 2026. The current app may look different.
- The Practice IQ web screenshot shows the range 07/01/2025 to 07/31/2025.
- Product pages (PRM, Ops AI, Call AI, Revenue IQ) are marketing text. They describe features
  but do not show them.
- The screenshots have no alt text. Where a guide gives no meaning for a colour or icon, this
  document says so and does not guess. Colour names are approximate; exact values, type sizes
  and spacing are not published and are not stated here.
- PbN serves dental practice teams with many roles and locations. Customer Pulse serves one
  owner with one workspace. The users differ a lot, which limits how far the feedback in
  section 3 transfers.

## 2. What we observed

### 2.1 Navigation and dashboards

**Observed**

- PbN is a broad suite: Business Analytics (Practice IQ, Revenue IQ, Enterprise Dashboard),
  Patient Relationship Management, Operational Efficiency, PbN AI, Marketing, Payments, Voice
  and Forms. The Enterprise Dashboard, reached through a practice switcher, covers one or
  many practices. [S1, S4, S8]
- The **Desktop App** (S7-a to S7-f) has a dark, icon-only left rail with 13 sections. The
  current item has a teal-green background. Two icons carry red count badges ("2", "99+").
  Hovering shows a tooltip with the section name. [S7]
- The **Practice IQ web app** (S9-a) has a dark top bar with text links, including "Tasks"
  with a red "315" badge, and a left panel "Your Dashboards" ("Home", "Financial", "Doctors",
  "Hygienists", "New Dashboard", "Customize Dashboards"). [S9]
- The **Daily Dashboard** (S7-a): title, practice name with a green dot and "Last Update:
  08/01/2024", a "Filters" row of pill chips with coloured dots ("Appt Request",
  "Appointment", "Form", "Payment", "Refund", "Feedback", "Review") and "Select All", then two
  columns: "Action Needed" (tabs "Pending", "Ignored", "Completed", "All") and "Notifications"
  (tabs "Unread", "All"). The guide says it "provides a snapshot of daily activities and
  pending actions". [S7]
- **Production and Phone Metrics** (S7-b): a grid of solid-colour tiles, each with a big white
  number and a label ("Today's Production", "Scheduled", "Missed", "New Patients Saved" and
  others). Tile colours include grey, light blue, teal, dark red, dark green and olive. The
  guide does not say what the colours mean. [S7]
- **Practice IQ Home** (S9-a): one plain sentence at the top, "Welcome back [first name]! Your
  practice produced $93,229.81 from 243 patients. You added $94,135.00 worth of appointments
  and 27 new patients.", numbers in teal. Then a filter bar ("Practices", "Current Month",
  date arrows, "Compare to"), four summary tiles, and six white cards ("Production", "Patient
  Retention", "Treatment Acceptance", "Hyg Retention", "Accounts Receivables", "Revenue
  Lost"). Each card has one headline number, a bar, gauge, donut or bar chart, then label and
  value rows. Some bars carry "25th", "50th", "75th", "90th" labels the guide does not explain.
  [S9]
- The guide calls the Home Dashboard "a mission-critical tool used by practices daily" and
  advises "Monitor these tiles first thing each morning and again before closing". The
  Enterprise Dashboard offers "over 400 KPIs to choose from". Custom dashboards let "team
  members to see only the information they need to see in order to do their specific job".
  [S2, S3, S9]

**Interpretation**

- There are two kinds of dashboard. The Daily Dashboard is a work queue: what needs a person.
  Practice IQ is a metrics board: how are we doing.
- The Practice IQ sentence is the calmest element we saw. It turns numbers into one readable
  line before the detail.
- Role-based dashboards are PbN's main answer to having too much data.
- The percentile labels probably show a benchmark; the analytics page mentions comparing with
  "almost 1000 practices" [S3]. We did not confirm the link.

### 2.2 How attention and actions are surfaced

**Observed**

- "Action Needed" highlights tasks that need immediate attention, such as new appointment
  requests and payment confirmations. Each has a time stamp and can be marked completed or
  ignored. [S7]
- In S7-a each Action Needed item is a bordered card: a round initials avatar, a small
  coloured category tag ("Appointment"), one sentence ("A patient responded with a text
  message that we need your help with"), a relative time ("44 minutes ago"), and two round
  buttons, a green tick and a red cross. Notification cards use the same layout with an
  orange dot. [S7]
- **Task Management** (S7-e): four large counts with coloured labels, "Overdue" 270 (red),
  "Due Today" 18 (orange), "Due Tomorrow" 3 (grey), "All Tasks" 415 (blue). Rows sit under a
  full-width "Overdue" group row with a pale red background. Each task has a coloured type tag
  and a status cell "Due 2024-01-24" over "Created 2024-01-23". [S7]
- The Practice IQ guide has an "Action-Oriented KPI Guidance" table, "If You See..." and
  "Suggested Action" ("Tx Acceptance <50%" → "Enhance treatment presentation training and use
  visual tools"), plus "Best Practice Tip", "Suggestion", "Practice Strategy" and "Insight"
  callouts after each metric group. [S9]
- Revenue IQ describes opportunity lists ("incomplete treatments, overdue recalls, ASAP
  patients, and cancelled appointments") and "Auto-assign follow-ups directly from patient
  lists and track them by status: overdue, due today, and upcoming". [S6]
- Call AI summaries highlight "purpose, outcome, action items, concerns raised, and follow-up
  needs", and Call AI sends "automatic alerts" on sentiment. Ops AI drafts messages and review
  replies. [S10, S11]

**Interpretation**

- PbN's attention model is event-driven and date-driven: new requests, unread items, overdue
  and due-today tasks, metric thresholds.
- "Action Needed" in PbN is a queue of system events, each closed by a person. It is not a
  judgement about a whole relationship.
- The "Overdue 270" count shows a known risk: when counts get large they stop telling the user
  what to do first.
- The step from insight to action happens inside PbN (task, message, campaign). The public AI
  pages describe what the AI produces but not how a user checks it. On the pages we read we
  found no statement about showing the source behind an AI summary, or what happens when the
  AI fails. [S10, S11]

### 2.3 Lists, detail views and filters

**Observed**

- **Two-pane list and thread** (S7-c, Communication Center): a left list of rows with a small
  icon, a name, a time and one cut-off preview line; the selected row has a light blue
  background. The right pane shows the thread with a "Today" divider, a message box and a
  "Send" button. The guide does not say what the row icons mean. [S7]
- **Tables** (S7-e, S7-f): upper-case column headers, row checkboxes, bulk action buttons
  ("Change Due Date", "Reassign", "Close", "Reopen", "Edit Multiple"). The Marketing IQ empty
  state reads "No data available in table", with "Show 10 entries" and paging. [S7]
- **Patient Overview** (S7-d): a header block with initials avatar, name, email, a round phone
  button, and buttons "ADD TASK" and "CREATE NOTE". Below: "Sex", "Age", "Inactive" in red
  text, and dollar amounts under "Current", "30", "60", "90". Then eight tabs ("Overview",
  "Account", "Treatment", "Communications", "Details", "Insurance", "Documents", "Form"). The
  Overview tab shows label/value blocks ("Last Visit", "Next Recall Due", "Open Tasks" and
  others), each with a coloured left border, some blue-teal and some red. Empty values show
  "-". A "Family" panel shows linked people with orange text such as "Recall Overdue". [S7]
- Filters and search appear on nearly every screen: category chips, funnel icons, "Filters"
  bars, period dropdowns with date ranges, and a full-width patient search. Revenue IQ
  advertises "40+ filters and custom tags", "Saved Searches & Smart Filters" and natural
  language search such as "patients who missed appointments last month". [S6, S7]

**Interpretation**

- The detail view puts identity and status first, then key facts, then deeper data in tabs.
- The meaning of red versus teal left borders is not stated. It may mean "needs attention";
  we cannot confirm it.
- "-" for empty data is compact but does not say whether data is missing or zero.
- Filtering is the main tool for narrowing large data. For a small list it would add work.

### 2.4 Density, colour and tone

**Observed**

- PbN handles density by adding structure: cards, groups, tabs, filters, role dashboards, and
  a help centre that defines every metric with "Definition" and "Calculation". [S2, S3, S9]
- Short forms are everywhere in the UI: "MTD Prod", "AR Due", "Tx Pending", "Hyg Pts
  Re-appntd", "NP Pre-Appmnt". [S7, S9]
- Colour carries status: coloured category tags and chip dots, red "Overdue" and orange
  "Due Today" labels, "Inactive" in red text, a pale red "Overdue" group row, red count badges,
  a green dot next to "Last Update". Call AI groups calls as "positive, neutral, or negative".
  [S7, S9, S11]
- Visual base: light grey (Practice IQ) or mostly white (Desktop App) page background; dark
  navy navigation; teal as the main data colour; white rounded cards with a thin border or
  light shadow; round initials avatars; pill-shaped chips and buttons; sans-serif type with
  large numbers and small grey labels. Practice IQ has generous white space; the Desktop App
  metric grid is packed edge to edge. [S7, S9]
- Marketing tone is confident and outcome-led: "Run Your Dental Practice Like a True CEO"
  [S3], "Discover hidden opportunities" and "Detect revenue leaks" [S2]. In-product queue text
  is one plain sentence, and help-guide advice is imperative ("Launch a post-visit follow-up
  campaign for new patients"). Queue times are relative ("44 minutes ago"). [S7, S9]
- Stated philosophy: "What is measured will ultimately improve." [S3]; "view the information
  that's most important to you, in a single view" [S2]; AI framed as "instant clarity", "no
  digging required". [S9, S10]

**Interpretation**

- In the screenshots, text labels sit next to most colours, but some meanings (tile colours,
  left borders, green dots) are carried by colour alone.
- Urgency in PbN is mostly about dates. Priority is money and volume first, then retention,
  then the day's queue. Decisions are helped by comparing numbers to goals, past periods and
  other practices, and by rules of thumb that map a number to an action.
- PbN both creates and manages overload: 400+ KPIs and 13 desktop sections, managed with role
  dashboards, filters and help articles. Users still report overload (section 3).
- Customer Pulse is meant to read the notes of each relationship and explain the situation,
  and PRD FR-3.7 says recency alone never decides the state. PbN's date-based urgency does not
  transfer.

## 3. User feedback (secondary sources)

Weaker than the official sources: few reviews, unknown collection methods. G2 returned
HTTP 403. Capterra (S12) was read only through a fetch tool that returns a summary, so its
wording and rating could not be re-checked and its points are paraphrased. Software Finder
(S13) quotes were checked against the page text.

**Clear or useful**

- One place for many tools: "Everything we need is in one place". Tasks replacing "sticky
  notes all over the office". [S13]
- An office manager says it changed how they look at their numbers and make decisions. [S12]
- Responsive support. [S12, S13]

**Overwhelming or hard**

- A manager found it overwhelming at first to decide which reports matter most. [S12]
- "too many options packed onto one page". [S13]
- A learning curve and a wish for tailored onboarding. [S12, S13]
- Data trust: some numbers synced from Dentrix are said to be inaccurate or not to match.
  [S13]

**Interpretation**

- The overload complaints are about choosing among many reports. A product with one list and
  one detail view avoids that by design.
- The data-trust complaint matters for AI. If users doubt synced numbers, they will doubt an
  AI assessment more. Showing where each statement comes from (PRD FR-3.6) is the direct
  answer.

## 4. Relevance to Customer Pulse

**Adopt** — use as is. **Adapt** — use the idea, changed to fit the PRD. **Avoid** — do not
use. **Not relevant** — outside the PRD's scope. Rows marked "UX decides" were options for the
UX design, not commitments.

| # | PbN pattern | Class | Why |
| --- | --- | --- | --- |
| P1 | Work queue kept apart from metrics | Adapt | No metrics board. Keep the idea: the list answers "who needs me" (UJ1), not "how are we doing". |
| P2 | One plain summary sentence above the detail | Adapt | A short line can orient the owner. It must not add new AI text; any count only restates the assessments shown. Not a greeting or a KPI. UX decides. |
| P3 | Filter chips with "Select All" | Adapt | One way to meet FR-1.3; grouping (P4) is another. Chips need text, not only a colour dot. UX decides. |
| P4 | Group header rows ("Overdue" band) | Adapt | Grouping by assessment state is another way to meet FR-1.3. Groups by state, never by date. |
| P5 | Queue card: avatar, type tag, one-sentence reason | Adapt | Maps to a row with name, status, state and reason (FR-1.1, FR-1.2). Avatars add little. |
| P6 | Tick / cross, "Pending/Ignored/Completed" tabs | Avoid | PRD section 7 excludes correcting, dismissing or snoozing; the MVP is read-only. |
| P7 | "Action Needed" as a label | Adapt | Same words as PRD FR-3.2, different meaning: PbN's is a system event a person closes; ours is a judgement on the whole history. Copy must make that clear. |
| P8 | Due-date urgency ("Overdue", "Due Today") | Avoid | FR-3.7 and AC-7: dates passing never change the state. No tasks or due dates in scope. |
| P9 | Big alarm counts ("Overdue 270") | Avoid | Pressure without telling the owner who to open first. A small plain count per state may be fine. |
| P10 | Red count badges on navigation | Avoid | Notifications are a non-goal; noise in a two-view product. |
| P11 | Solid-colour metric tile grid | Avoid | Not a metrics dashboard; tile colours carry unexplained meaning. |
| P12 | 400+ KPIs, custom and role dashboards, "Compare to", percentiles | Not relevant | Single owner, single workspace, no reports. |
| P13 | Practice switcher and Enterprise Dashboard | Not relevant | One workspace only. |
| P14 | Two-pane list and detail | Adapt | Fits UJ1 → UJ2 on wide screens. Must also work as two separate pages on narrow screens. UX decides. |
| P15 | Date divider in a thread ("Today") | Adapt | Grouping history under date headings suits our data: same-date interactions sit under one date without implying order (PRD section 8). Real dates, not "Today". |
| P16 | Relative times ("44 minutes ago") | Avoid | Our dates have no time of day and "today" is not defined. Relative dates suggest precision and recency meaning we do not have. |
| P17 | Detail header: identity, status, key facts first | Adopt | Matches FR-2.1 and FR-4.1. Placement is a UX decision. |
| P18 | Tabs for detail sections | Adapt | Four parts only (FR-2). Tabs could hide the assessment or its evidence. One page is likely enough; UX decides. |
| P19 | Label/value blocks with "-" for empty | Adapt | Label/value is fine. Replace "-" with a clear message where the PRD asks for one. |
| P20 | Coloured borders and status text with no stated meaning | Avoid | Colour must never be the only signal (`frontend/AGENTS.md`). Every state needs a text label. |
| P21 | Coloured type tags on items | Adapt | A small text tag for interaction type aids scanning. Colour secondary. |
| P22 | "ADD TASK", "CREATE NOTE", call button, composer | Avoid | Read-only, sends nothing (PRD sections 6 and 7). No buttons that suggest actions Customer Pulse cannot take. |
| P23 | Bulk actions, row checkboxes | Avoid | No editing in scope. |
| P24 | Table paging | Not relevant | The seeded list is small. Revisit only if data grows. |
| P25 | "If You See… → Suggested Action" table | Adapt | The pairing "situation → next step" matches FR-3.5. Ours comes from each relationship's own history, not thresholds, and is traceable (FR-3.6). |
| P26 | AI call summary: purpose, outcome, action items, concerns, follow-up | Adapt | Similar shape to our reason, summary and open items (FR-3.4). The PRD adds what PbN's pages do not show: tracing each statement (FR-3.6) and an unavailable fallback (FR-4.2). |
| P27 | AI drafting of messages | Not relevant | A future opportunity (PRD section 15). |
| P28 | Opportunity lists, campaigns, auto-assigned follow-ups | Avoid | Pipelines, tasks and sending are non-goals. |
| P29 | 40+ filters, saved searches, natural-language search | Not relevant | Search is a future opportunity. |
| P30 | Freshness indicator ("Last Update" with green dot) | Adapt | Telling the owner how current something is could help the loading and unavailable states (FR-4.1, FR-4.2). A dot alone is not enough. When assessments are made is a technical decision. |
| P31 | Icon-only navigation with tooltips | Avoid | Two views need no navigation. Icon-only hides meaning and is weak for keyboard and touch. |
| P32 | Domain short forms ("Tx", "MTD") | Avoid | Our user is one owner, not trained staff. Plain words. |
| P33 | One plain sentence per item | Adopt | Matches the PRD's "short reason" (FR-1.2). |
| P34 | Confident, outcome-led tone | Avoid | The product must not claim more than the history supports (PRD principles 2 and 6). Calm, factual copy. |
| P35 | Help text with a "Definition" per metric | Adapt | Each state could have one plain line of meaning the owner can find. UX decides. |
| P36 | Light background, white rounded cards, one accent, generous space | Adapt | A calm base that suits the goal. Colours and spacing are for the UX design, not copied. |

## 5. Design principles for Customer Pulse

Derived from the above and the PRD. They guided the UX design; they do not define screens.

1. **Answer "who needs me" first.** The list leads with the assessment state and short reason.
   Facts support it; they do not compete with it. (UJ1, FR-1.2, FR-1.3)
2. **Keep the answers visibly different.** `Action needed`, `Waiting` and `No action needed`
   each have their own text label. Assessment unavailable looks like a missing answer, never
   like a fourth state or like "nothing to do". Colour only supports the text. (FR-4.2)
3. **Put the why next to the what.** Every reason, open item and suggested step sits close to
   the interactions behind it. (FR-3.6, UJ3)
4. **Facts never wait.** Name, status, contacts and history show without waiting for the
   assessment. The assessment area shows its own loading or unavailable message. (FR-4.1)
5. **Calm over complete.** No metric tiles, alarm counts, badges or relative times. A few
   things per row, in plain words. The PbN feedback shows that more options do not make
   decisions easier.
6. **Urgency comes from the history, not the calendar.** No overdue styling, no date-based
   highlighting. A passed date changes nothing on its own. (FR-3.7, AC-7)
7. **Suggest, do not act.** A suggested next step is text for the owner to judge. No buttons
   that imply Customer Pulse will send, create, complete or dismiss anything.
8. **Be honest about what the data cannot say.** Same-date interactions show no implied
   order. No sender or direction is shown as fact. Empty and missing data get a clear message,
   not a dash. (PRD sections 8 and 11)

## 6. Sources

All accessed 2026-09-16.

Official — product site

- **S1** Practice by Numbers home page — https://practicenumbers.com/
- **S2** Enterprise Dashboard product page — https://practicenumbers.com/business-analytics/enterprise-dashboard/
- **S3** Dental Analytics Dashboard page — https://practicenumbers.com/dental-analytics-dashboard/
- **S4** Patient Relationship Management page — https://practicenumbers.com/prm/
- **S6** Revenue IQ page — https://practicenumbers.com/business-analytics/revenue-iq/
- **S10** Ops AI page — https://practicenumbers.com/pbn-ai/ops-ai/ (reached from https://practicenumbers.com/ops-ai/)
- **S11** Call AI page — https://practicenumbers.com/pbn-ai/call-ai/ (reached from https://practicenumbers.com/call-ai/)

(S5 is not used.)

Official — help centre

- **S7** Comprehensive Guide to the Desktop App (last updated 28 May 2026) —
  https://help.practicenumbers.com/en/articles/9980449-comprehensive-guide-to-the-desktop-app
  Screenshots viewed from this page (hosted by the help centre, no alt text):
  - S7-a Daily Dashboard (Filters, Action Needed, Notifications)
  - S7-b Production and Phone metric tiles
  - S7-c Communication Center (Messages)
  - S7-d Patient Overview
  - S7-e Task Management
  - S7-f Marketing IQ (New Patient ROI Snapshot, Leads table)
- **S8** Accessing Enterprise Dashboards —
  https://help.practicenumbers.com/en/articles/9980235-accessing-enterprise-dashboards
- **S9** Practice IQ Home Dashboard – Complete Guide —
  https://help.practicenumbers.com/en/articles/11842471-practice-iq-home-dashboard-complete-guide
  - S9-a Practice IQ Home Dashboard screenshot (date range July 2025)

Secondary — user feedback only

- **S12** Capterra, Practice by Numbers reviews (5.0 from 6 reviews as reported by the fetch
  tool summary; not re-checked) —
  https://www.capterra.com/p/10003188/Practice-by-Numbers/reviews/
- **S13** Software Finder, Practice by Numbers reviews (4.8 from 84 reviews at access time) —
  https://softwarefinder.com/emr-software/practice-by-numbers/reviews
- **Not read:** G2 reviews — https://www.g2.com/products/practice-by-numbers/reviews
  (returned HTTP 403).

## 7. Research gaps

- **How PbN shows AI output in the product.** No public screenshot of an AI summary, its
  sources or its failure state. This is the area closest to Customer Pulse's core.
- **Revenue IQ opportunity lists** are described in text only; we did not see how a reason is
  shown per person.
- **Current look.** Desktop App screenshots are from 2024.
- **Mobile, accessibility, empty and error states.** No evidence on narrow screens, keyboard
  use, contrast or screen readers; only one empty state seen ("No data available in table").
- **Colour meanings.** Tile colours, left borders and green dots are not explained.
- **Feedback quality.** Small review counts, unknown collection method, G2 unreadable,
  Capterra wording not re-checkable, and PbN users are dental teams rather than a single owner.
