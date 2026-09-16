# Customer Pulse — UI research: Practice by Numbers

Status: Complete for MVP UX planning

This is research input for UX design. It is not a design and not a requirement. It may be
updated later if new evidence is researched on purpose.

The frozen PRD (`docs/PRD.md`, v0.3) decides what Customer Pulse does. This document only looks
at how one existing product presents similar information, so the later UX design can make
better choices. Nothing here adds scope. Where a pattern would need something the PRD rules
out, it is marked **Avoid** or **Not relevant**.

All sources were read on **2026-09-16**. Section 8 lists them.

## 1. How to read this document

- **Observed** means it is written in the source, or visible in a screenshot published by the
  source. Screenshots were opened and looked at directly. Nothing else is described as seen.
- **Interpretation** means our reading of what we observed. It is marked as such.
- Text in quotes is copied exactly from the source, except where section 4 says otherwise.
- The source guides use screenshots with no alt text. Where a guide gives no meaning for a
  colour or icon, this document says so and does not guess.

### Limits of the evidence

- Only public pages were used. We had no account and saw no live product.
- The Desktop App screenshots show dates in 2024 ("Last Update: 08/01/2024"). The guide page
  itself was last updated on 28 May 2026. The current app may look different.
- The Practice IQ web screenshot shows the date range 07/01/2025 to 07/31/2025.
- Product pages (PRM, Ops AI, Call AI, Revenue IQ) are marketing text. They describe features
  but do not show how those features look.
- Practice by Numbers (PbN) serves dental practice teams with many roles and many locations.
  Customer Pulse serves one small-business owner with one workspace. The users differ a lot.

## 2. Observed product patterns

### 2.1 Navigation and information structure

**Observed**

- Main site modules: Business Analytics (Practice IQ, Revenue IQ, Enterprise Dashboard),
  Patient Relationship Management, Operational Efficiency, PbN AI, Marketing, Payments, Voice,
  Forms. The PRM page calls PRM part of one platform. [S1, S4]
- **Desktop App** (screenshots S7-a to S7-f): a dark, icon-only rail on the left. The current
  item has a teal-green background. Two icons carry red count badges ("2" and "99+"). Hovering
  an icon shows a dark tooltip with its name ("Marketing IQ"). The guide lists 13 sections:
  Daily Dashboard, Production and Phone Metrics, Patient Search and Overview, Communication
  Center, Call Log, Appointment Schedule, Patient Flow, Task Management, Marketing IQ, Team
  Messaging, Huddle, Payments, Call Center. [S7]
- **Practice IQ web app** (screenshot S9-a): a dark top bar with the logo and text links:
  "Practice IQ", "Tasks" (with a red "315" badge), "Revenue IQ", "Phone IQ", "Huddle",
  "Reputation", "Appointments", "Forms", "Payments". Search and user icons are on the right.
  A left panel headed "Your Dashboards" lists "Home", "Financial", "Doctors", "Hygienists",
  plus "New Dashboard" and "Customize Dashboards". [S9]
- **Enterprise Dashboard**: reached from the practice switcher. Click the arrow next to the
  practice name, open "Switch Practice", then click "Enterprise Dashboards" at the bottom. A
  "Practices" dropdown at the top selects one or many practices, applied with "Select". [S8]
- The analytics page says custom dashboards let "team members to see only the information they
  need to see in order to do their specific job". [S3]

**Interpretation**

- PbN is a broad suite. Hierarchy is module first, then a page inside the module.
- Role-based dashboards are PbN's main answer to having too much data.

### 2.2 Dashboard structure

**Observed**

- **Daily Dashboard** (S7-a), top to bottom: title "Daily Dashboard"; top right shows the
  practice name, a green dot and "Last Update: 08/01/2024". Then a "Filters" row with a
  "Select All" link and pill-shaped chips, each with a small coloured dot: "Appt Request",
  "Appointment", "Form", "Payment", "Refund", "Feedback", "Review". Below are two columns side
  by side: "Action Needed" (tabs "Pending", "Ignored", "Completed", "All") and "Notifications"
  (tabs "Unread", "All"). [S7]
- The guide says the Daily Dashboard "provides a snapshot of daily activities and pending
  actions". [S7]
- **Production and Phone Metrics** (S7-b), lower on the same Home page: a grid of large,
  solid-colour tiles, each with a big white number and a label at the bottom left
  ("Today's Production", "Scheduled", "MTD Projection", "Daily Goal Forward", "Incoming",
  "Missed", "Return Time", "New Patients Saved" and others). Tile colours include grey, light
  blue, teal, dark red, dark green and olive. The guide does not explain what the colours mean.
  [S7]
- **Practice IQ Home** (S9-a): a heading "PracticeIQ" next to one plain sentence:
  "Welcome back [first name]! Your practice produced $93,229.81 from 243 patients. You added
  $94,135.00 worth of appointments and 27 new patients." The numbers are in teal text. Then a
  filter bar ("Practices", "Current Month", back/forward arrows with a date range,
  "Compare to"), a toggle, a menu icon and a "?" help icon. Then four summary tiles ("On
  Schedule", "Appmts Added", "Appmts Dollars Added", "New Patients Added"), each with an icon,
  a value and "Today". Then six white cards with rounded corners and a light shadow:
  "Production", "Patient Retention", "Treatment Acceptance", "Hyg Retention",
  "Accounts Receivables", "Revenue Lost". [S9]
- Each Practice IQ card has one headline number, then a teal bar, arc gauge, donut or bar
  chart, then a list of label and value rows. Under some bars there are small labels such as
  "25th", "50th", "75th", "90th". The guide text we read does not explain these labels. [S9]
- The guide calls the Home Dashboard "a mission-critical tool used by practices daily" and
  advises: "Monitor these tiles first thing each morning and again before closing." [S9]
- Enterprise Dashboard: "over 400 KPIs to choose from", "high-level overviews and detailed
  drill-downs". [S2]

**Interpretation**

- There are two kinds of dashboard. The Daily Dashboard is a work queue ("what needs a
  person"). Practice IQ is a metrics board ("how are we doing").
- The Practice IQ sentence summary is the calmest element we saw. It turns numbers into one
  readable line before the detail.
- The percentile-style labels probably show a benchmark. The analytics page mentions comparing
  with "almost 1000 practices" [S3]. We did not confirm this link.

### 2.3 How attention and action items are surfaced

**Observed**

- The guide says "Action Needed" highlights tasks that need immediate attention, such as new
  appointment requests and payment confirmations. Each task has a time stamp and can be marked
  as completed or ignored. [S7]
- In S7-a each Action Needed item is a bordered card with a round initials avatar, a small
  coloured category tag (for example "Appointment"), one sentence ("A patient responded with a
  text message that we need your help with"), a relative time ("44 minutes ago", "4 hours
  ago"), and two round buttons: a green tick and a red cross. [S7]
- Notification cards have the same layout, with a small orange dot on the right. The guide
  says the section "Displays unread notifications". [S7]
- **Task Management** (S7-e): four large counts at the top, each with a coloured label:
  "Overdue" 270 (red label), "Due Today" 18 (orange label), "Due Tomorrow" 3 (grey label),
  "All Tasks" 415 (blue label). [S7]
- Navigation badges show unread or open counts ("2", "99+", "315"). [S7, S9]
- Practice IQ guide has an "Action-Oriented KPI Guidance" table with two columns,
  "If You See..." and "Suggested Action". Example: "Tx Acceptance <50%" → "Enhance treatment
  presentation training and use visual tools". [S9]
- The same guide has callouts marked "Best Practice Tip", "Suggestion", "Practice Strategy"
  and "Insight" after each metric group. [S9]
- Revenue IQ describes opportunity lists that cover "incomplete treatments, overdue recalls,
  ASAP patients, and cancelled appointments". [S6]
- Call AI summaries highlight "purpose, outcome, action items, concerns raised, and follow-up
  needs". Call AI also sends "automatic alerts" on sentiment. [S11]

**Interpretation**

- PbN's attention model is mostly event-driven and date-driven: new requests, unread items,
  overdue and due-today tasks, thresholds on metrics.
- "Action Needed" in PbN is a queue of system events. Each item is closed by a person. It is
  not a judgement about a whole relationship.
- The count badges and the "Overdue 270" count show a known risk: when counts get large, they
  stop telling the user what to do first.

### 2.4 Filters and search

**Observed**

- Daily Dashboard: category chips with coloured dots and "Select All". [S7]
- Communication Center (S7-c): a menu icon and a funnel icon above a "Search" field. [S7]
- Task Management (S7-e): a full-width "Filters" bar (collapsed in the screenshot) and a
  "Search:" field on the right. [S7]
- Marketing IQ (S7-f): a "Filter" button and a "Search" field on the Leads table; a period
  dropdown ("Current Month") with back/forward arrows and a from–to date range. [S7]
- Patient Overview (S7-d): a full-width search box at the top holding a patient name. [S7]
- Call Log: "filter calls by status and date". Appointment Schedule: filter "by confirmation
  status or insurance status". [S7]
- Revenue IQ: "40+ filters and custom tags", "Saved Searches & Smart Filters", and natural
  language search such as "patients who missed appointments last month". [S6]

**Interpretation**

- Filtering is everywhere and is the main tool for narrowing large data. For a small list it
  would add work, not remove it.

### 2.5 List, table, card and detail patterns

**Observed**

- **Cards** for queue items (S7-a) and for metric groups (S9-a).
- **Two-pane list and thread** (S7-c): header "Messages (2)". The left list has rows with a
  small icon (mobile phone, house or phone handset), a name, a time and one cut-off preview
  line. The guide does not say what the icons mean. Some rows have a green dot. The
  selected row has a light blue background. The right pane shows the thread with a "Today"
  divider, blurred message content, a "Type message here..." box, icon buttons and a "Send" button.
  [S7]
- **Tables** (S7-e, S7-f): upper-case column headers ("PATIENT", "TASK", "STATUS",
  "ASSIGNEE"), row checkboxes, bulk action buttons ("Change Due Date", "Reassign", "Close",
  "Reopen", "Edit Multiple"). In Task Management, rows sit under a full-width group row
  "Overdue" with a pale red background. Each task has a small coloured type tag ("Task:" grey,
  "Cancelled Appointment:" orange, "Preappointment:" blue, "Treatment Followup:" purple) and a
  status cell with "Due 2024-01-24" over "Created 2024-01-23". [S7]
- Marketing IQ table empty state: "No data available in table", with "Show 10 entries",
  "Showing 0 to 0 of 0 entries", "Previous" and "Next". [S7]
- **Detail view — Patient Overview** (S7-d): title "Patient Overview" with previous/next
  arrows. A header block with initials avatar, name, email (with a dropdown), a round phone
  button, a refresh icon, and two buttons "ADD TASK" and "CREATE NOTE". Below: "Sex", "Age",
  and "Inactive" in red text. On the right, dollar amounts under "Current", "30", "60", "90". Then
  tabs: "Overview", "Account", "Treatment", "Communications", "Details", "Insurance",
  "Documents", "Form". The Overview tab shows a "Patient" panel of label/value blocks
  ("Last Visit", "Next Regular", "Next Preventive", "Next Recall Due", "Benefits Left",
  "Open Tasks"), each with a coloured left border (some blue-teal, some red). Empty values show
  as "-". A "Family" panel shows linked people with orange text such as "Recall Overdue" and
  "Inactive". [S7]
- The guide describes the patient view as "Patient Details", "Account and Treatment" and
  "Family Information". [S7]

**Interpretation**

- The detail view puts identity and status first, then key facts, then deeper data in tabs.
- The meaning of the red versus teal left borders is not stated. It may mean "needs attention",
  but we cannot confirm it.
- A "-" for empty data is compact but does not say whether data is missing or zero.

### 2.6 Making dense information understandable

**Observed**

- A one-sentence plain summary above the Practice IQ dashboard. [S9]
- Each Practice IQ card leads with one big number, then supporting rows. [S9]
- Help text defines every metric with "Definition" and "Calculation". [S9]
- Role-based and custom dashboards. [S2, S3]
- Heavy use of short forms in the UI: "MTD Prod", "AR Due", "Tx Pending",
  "Unscheduled Fam Members", "Hyg Pts Re-appntd", "NP Pre-Appmnt". [S7, S9]

**Interpretation**

- PbN handles density by adding structure (cards, groups, tabs, filters) and a help centre, not
  by showing less. The short forms assume trained dental staff.

### 2.7 Status and priority treatments

**Observed**

- Coloured category tags and chip dots for item types. [S7]
- Coloured labels for task urgency (red "Overdue", orange "Due Today"). [S7]
- Coloured text for patient state ("Inactive" in red, "Recall Overdue" in orange). [S7]
- A pale red group row for "Overdue" tasks. [S7]
- Red count badges on navigation. [S7, S9]
- A green dot next to "Last Update" and next to the practice name in the window title. [S7]
- Call AI groups calls as "positive, neutral, or negative". [S11]

**Interpretation**

- Colour does much of the work. In the screenshots, text labels also appear next to most
  colours, but some meanings (tile colours, left borders, green dots) are only colour.
- Urgency is mostly about dates (overdue, due today).

### 2.8 From insight to action

**Observed**

- Queue items are closed with tick and cross buttons, and filed under "Completed" or
  "Ignored". [S7]
- Patient Overview offers "ADD TASK", "CREATE NOTE" and a call button. [S7]
- The Communication Center sends forms, treatment plans, review requests, payment requests and
  SMS templates from the message window. [S7]
- Revenue IQ: "Auto-assign follow-ups directly from patient lists and track them by status:
  overdue, due today, and upcoming", and "Launch campaigns". [S6]
- Practice IQ guide maps a metric pattern to a "Suggested Action". [S9]
- Ops AI drafts messages and review replies ("Message Creation", "Review Response"). [S10]

**Interpretation**

- In PbN the step from insight to action happens inside the product: task, message, campaign.
- The public AI pages describe what the AI produces, but not how a user checks it. On the pages
  we read, we found no statement about showing the source behind an AI summary, or about what happens when
  the AI fails. [S10, S11]

### 2.9 Terminology and tone

**Observed**

- Marketing tone is confident and outcome-led: "Run Your Dental Practice Like a True CEO"
  [S3], "Discover hidden opportunities" and "Detect revenue leaks" [S2], and many percentage
  claims [S1, S4].
- In-product labels are short and domain-specific ("Appt Request", "Tx Pending", "AR Days").
  [S7, S9]
- Help-guide advice is direct and imperative ("Launch a post-visit follow-up campaign for new
  patients"). [S9]
- Queue item text is one plain sentence ("… requested a call back for his appointment"). [S7]
- Times in queues are relative ("44 minutes ago", "an hour"). [S7]

### 2.10 Visual patterns (only what the screenshots show)

- Page background: light grey in Practice IQ; mostly white in the Desktop App. [S7, S9]
- Navigation: dark navy (left rail in the Desktop App, top bar in Practice IQ). [S7, S9]
- Accent: teal is the main data colour in Practice IQ (bars, gauges, highlighted numbers).
  [S9]
- Cards: white, rounded corners, thin border (Desktop App) or light shadow (Practice IQ).
  [S7, S9]
- Round initials avatars in several colours. [S7]
- Pill-shaped chips, tags and buttons. [S7]
- Sans-serif type throughout. Large numbers for metrics; small grey labels. We cannot name the
  typeface from the screenshots. [S7, S9]
- Generous white space in Practice IQ; the metric tile grid in the Desktop App is packed
  edge to edge. [S7, S9]
- Exact colour values, font sizes, spacing values and icon sets are not published. This
  document does not state them.

## 3. Product philosophy visible in the sources

**Observed**

- "What is measured will ultimately improve." [S3]
- "view the information that's most important to you, in a single view". [S2]
- "replaces scattered tools with one seamless, innovative platform". [S1]
- Daily review is encouraged: "Review this dashboard daily to detect issues early and take
  proactive steps". [S9]
- AI is framed around speed: "instant clarity", "no digging required". [S9, S10]

**Interpretation**

- **What is prioritised:** money and volume (production, collections, revenue lost), then
  patient retention, then the day's queue of events.
- **How dashboards help decisions:** by comparing numbers to goals, past periods and other
  practices, and by rules of thumb that map a number to an action.
- **Overload:** PbN both creates and manages it. It offers 400+ KPIs and 13 desktop sections,
  and manages them with role dashboards, filters and help articles. Users still report
  overload (section 4).
- **Actionable insight:** mostly shown as lists of people or items to act on, grouped by type
  or due date, with in-product buttons to act.
- **Contrast with Customer Pulse:** PbN is mostly metric- and date-led. Customer Pulse is
  meant to read the notes of each relationship and explain the situation. PRD FR-3.7 says
  recency alone never decides the state. So PbN's date-based urgency does not transfer.

## 4. User feedback (secondary sources)

Used only to inform trade-offs. These sources are weaker than the official ones: few reviews,
unknown collection methods, and we could not read G2 (HTTP 403).

Capterra (S12) was read only through a fetch tool that returns a summary. A direct download was
blocked, so its wording and rating could not be re-checked. S12 points below are paraphrased,
not quoted. Software Finder (S13) quotes were checked against the page text.

**What users find clear or useful**

- One place for many tools: "Everything we need is in one place" (Software Finder). [S13]
- Tasks replacing "sticky notes all over the office". [S13]
- Insights that change decisions. An office manager on Capterra says it changed how they look
  at their numbers and make decisions. [S12]
- Responsive support. [S12, S13]

**What users find overwhelming or hard**

- Choosing what matters: a manager on Capterra found it overwhelming at first to decide which
  reports matter most. [S12]
- Crowded screens: one review on Software Finder describes "too many options packed onto one
  page". [S13]
- Learning curve and wish for tailored onboarding. [S12, S13]
- Data trust: reviews say some numbers synced from Dentrix are not accurate or do not match.
  [S13]
- Settings that could be more intuitive (phone routing). [S12]

**Interpretation for trade-offs**

- The overload complaints are about choosing among many reports. A product with one list and
  one detail view avoids that by design.
- The data-trust complaint matters for AI. If users doubt synced numbers, they will doubt an AI
  assessment more. Showing where each statement comes from (PRD FR-3.6) is the direct answer.

## 5. Relevance to Customer Pulse

Classification key: **Adopt** — use as is. **Adapt** — use the idea, changed to fit the PRD.
**Avoid** — do not use. **Not relevant** — outside the PRD's scope.

| # | PbN pattern | Class | Why |
| --- | --- | --- | --- |
| P1 | Work queue kept apart from metrics (Daily Dashboard vs Practice IQ) | Adapt | Customer Pulse has no metrics board. The idea to keep: the list answers "who needs me" (UJ1), not "how are we doing". |
| P2 | One plain summary sentence above the detail (Practice IQ welcome line) | Adapt | A short plain line can orient the owner. It must not add new AI text; any count would only restate the assessments already shown. It must not become a greeting or a KPI. Whether to have one is a UX decision. |
| P3 | Filter chips with "Select All" | Adapt | FR-1.3 needs the owner to find all `Action needed` relationships. A small state filter is one option; grouping or ordering is another. The PRD leaves list order to UX. Chips need text, not only a colour dot. |
| P4 | Group header rows in a table ("Overdue" band) | Adapt | Grouping the list by assessment state is another way to meet FR-1.3. Groups must be by state, never by date. |
| P5 | Queue card: avatar, type tag, one-sentence reason | Adapt | Maps well to a list row with name, status, state and short reason (FR-1.1, FR-1.2). Avatars add little value; the state label and reason matter most. |
| P6 | Tick / cross to mark "Completed" or "Ignored"; "Pending/Ignored/Completed" tabs | Avoid | PRD section 7 excludes correcting, dismissing or snoozing an assessment, and the MVP is read-only. |
| P7 | "Action Needed" as a label | Adapt | Customer Pulse already uses `Action needed` (PRD FR-3.2). The meaning differs: PbN uses it for system events a person closes; ours is a judgement on the whole history. Copy must make our meaning clear. |
| P8 | Due-date urgency ("Overdue", "Due Today", "Due Tomorrow") | Avoid | FR-3.7 and AC-7: dates passing never change the state. There are no tasks or due dates in scope. |
| P9 | Big summary counts (for example "Overdue 270") | Avoid | Large alarm counts add pressure without telling the owner who to open first. A small, plain count per state may be fine if UX needs one. |
| P10 | Red count badges on navigation ("99+") | Avoid | Notifications are a non-goal. Badges add noise to a small product (a list and one detail view, PRD section 6). |
| P11 | Solid-colour metric tile grid | Avoid | Customer Pulse is not a metrics dashboard, and the tile colours carry unexplained meaning. |
| P12 | 400+ KPIs, custom and role dashboards, "Compare to", percentile markers | Not relevant | Single owner, single workspace, no reports (PRD sections 3 and 7). |
| P13 | Practice switcher and Enterprise Dashboard | Not relevant | One workspace only. |
| P14 | Two-pane list and detail (Communication Center) | Adapt | Fits UJ1 → UJ2 on wide screens. Mobile-first rules in `frontend/AGENTS.md` mean it must also work as two separate pages. Layout is a UX decision. |
| P15 | Date divider in a thread ("Today") | Adapt | Grouping history under date headings suits our data: interactions on the same date can sit under one date without implying their order (PRD section 8). Use real dates, not "Today". |
| P16 | Relative times ("44 minutes ago") | Avoid | Our dates have no time of day, and "today" is not defined in the data. Relative dates would suggest precision and a recency meaning we do not have. Use plain dates. |
| P17 | Detail header: identity, status, key facts first | Adopt | Matches FR-2.1 (name, status, created date) and FR-4.1 (facts never wait for the assessment). Exact placement is a UX decision. |
| P18 | Tabs for detail sections (8 tabs) | Adapt | Our detail has four parts: facts, contacts, history and assessment (FR-2). Tabs could hide the assessment or the evidence behind it. A single page is likely enough; UX decides. |
| P19 | Label/value blocks with "-" for empty | Adapt | Label/value is fine for facts. Replace "-" with a clear message where the PRD asks for one ("no contacts", "no interaction history"). |
| P20 | Coloured left borders and coloured status text with no stated meaning | Avoid | Colour must never be the only signal (`frontend/AGENTS.md`). Every state needs a text label. |
| P21 | Coloured type tags on items | Adapt | A small text tag for interaction type (email, call, meeting, note) aids scanning. Keep colour secondary. |
| P22 | "ADD TASK", "CREATE NOTE", call button, message composer | Avoid | MVP is read-only and sends nothing (PRD sections 6 and 7). No buttons that suggest actions Customer Pulse cannot take. |
| P23 | Bulk actions, row checkboxes, "Edit Multiple" | Avoid | No editing in scope. |
| P24 | Table paging ("Show 10 entries") | Not relevant | The seeded list is small. Revisit only if data grows. |
| P25 | "If You See… → Suggested Action" rule table | Adapt | The pairing "situation → suggested next step" matches FR-3.5. But ours must come from each relationship's own history, not thresholds, and be traceable (FR-3.6). |
| P26 | AI call summary: purpose, outcome, action items, concerns, follow-up | Adapt | Similar shape to our reason, summary and open items (FR-3.4). The PRD adds what PbN's public pages do not show: a way to trace each statement to its interactions (FR-3.6), and an unavailable fallback (FR-4.2). How tracing looks is a UX decision. |
| P27 | AI drafting of messages and replies | Not relevant | Drafting is a future opportunity (PRD section 15), not MVP. |
| P28 | Opportunity lists, campaigns, auto-assigned follow-ups | Avoid | Pipelines, tasks and sending are non-goals. |
| P29 | Filters with 40+ options, saved searches, natural-language search | Not relevant | Search is a future opportunity (PRD section 15). |
| P30 | Freshness indicator ("Last Update" with green dot) | Adapt | The idea of telling the owner how current something is could help the assessment loading and unavailable states (FR-4.1, FR-4.2). A green dot alone is not enough. When assessments are made is a technical design decision. |
| P31 | Icon-only navigation with hover tooltips | Avoid | The MVP scope is a list and one detail view (PRD section 6). Icon-only navigation hides meaning and is weak for keyboard and touch users. |
| P32 | Domain short forms ("Tx", "MTD", "Hyg Pts Re-appntd") | Avoid | Our user is one owner, not trained staff. Plain words, as `AGENTS.md` asks. |
| P33 | One plain sentence per item | Adopt | Matches the PRD's "short reason" (FR-1.2). |
| P34 | Confident, outcome-led marketing tone | Avoid | The product must not claim more than the history supports (PRD principles 2 and 6). Calm, factual copy. |
| P35 | Help text with "Definition" per metric | Adapt | We have few terms, but each state (`Action needed`, `Waiting`, `No action needed`, Assessment unavailable) could have one plain line of meaning the owner can find. Whether, where and how is a UX decision. |
| P36 | Light background, white rounded cards, one accent colour, generous space (Practice IQ) | Adapt | A calm base that suits our goal. Specific colours and spacing are for the UX design, not copied. |

## 6. Customer Pulse design principles

Derived from the research above and the frozen PRD. These guide the UX design. They do not
define screens.

1. **Answer "who needs me" before anything else.** The list leads with the assessment state and
   short reason. Facts support it; they do not compete with it. (UJ1, FR-1.2, FR-1.3)
2. **Keep the answers visibly different.** `Action needed`, `Waiting` and `No action needed`
   each have their own text label. Assessment unavailable looks like a missing answer, never
   like a fourth state or like "nothing to do". Colour only supports the text. (Principles 1
   and 6, FR-4.2)
3. **Put the why next to the what.** Every reason, open item and suggested step sits close to
   the interactions behind it, so the owner can check it without searching. (FR-3.6, UJ3)
4. **Facts never wait.** Name, status, contacts and history show without waiting for the
   assessment and stand alone. The
   assessment area shows its own loading or unavailable message. (Principle 5, FR-4.1)
5. **Calm over complete.** No metric tiles, alarm counts, badges or relative times. Show a few
   things per row, in plain words. The PbN feedback shows that more options do not make
   decisions easier.
6. **Urgency comes from the history, not the calendar.** No overdue styling, no date-based
   highlighting. A passed date changes nothing on its own. (FR-3.7, AC-7)
7. **Suggest, do not act.** A suggested next step is text for the owner to judge. No buttons
   that imply Customer Pulse will send, create, complete or dismiss anything. (Principle 4,
   section 7)
8. **Be honest about what the data cannot say.** Same-date interactions show no implied order.
   No sender or direction is shown as fact. Empty and missing data get a clear message, not a
   dash. (Section 8, section 11)

## 7. Review of this document

Checked before finishing:

- **Unsupported visual claims:** visual details come only from the seven screenshots opened
  (S7-a to S7-f, S9-a). Colour names are approximate descriptions, not values. Where a colour's
  meaning is not documented, the text says so.
- **Accidental requirements:** section 5 uses "could", "one option" and "UX decides" where the
  PRD leaves a choice to UX design. No new feature is proposed. P2, P3, P4, P30 and P35 are
  options, not commitments.
- **Copied patterns that do not fit:** date urgency, dismiss/complete controls, badges, metric
  tiles, in-app actions and campaigns are all marked Avoid.
- **Trade-offs noted:** P3 vs P4 (filter vs grouping for FR-1.3); P14 (two-pane vs mobile);
  P18 (tabs vs one page); P9 (count vs no count); principle 5 (calm vs showing everything).
- **Source strength:** product behaviour comes from official pages and the official help centre.
  Secondary sources are used only for user feedback. G2 could not be read.

## 8. Sources

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
  Screenshots viewed from this page (images hosted by the help centre, no alt text):
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

## 9. Research gaps

- **How PbN shows AI output** in the product: no public screenshot of an AI summary, its
  sources, or its failure state. This is the area closest to Customer Pulse's core.
- **Revenue IQ opportunity lists**: described in text only; we did not see how a reason is
  shown per person.
- **Current look**: Desktop App screenshots are from 2024 and may be out of date.
- **Mobile and narrow screens**: no evidence seen.
- **Accessibility**: no public information on keyboard use, contrast or screen readers.
- **Colour meanings**: tile colours, left borders and green dots are not explained.
- **Empty, loading and error states**: only one seen ("No data available in table").
- **User fit**: PbN users are dental teams; the feedback may not reflect a single owner
  managing a handful of relationships.
- **Feedback quality**: small review counts, unknown collection method, G2 unreadable,
  Capterra wording not re-checkable.
