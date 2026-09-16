# Customer Pulse — technical design v0.2

Status: **Approved for MVP implementation.**

How the MVP is built. Behaviour comes from `docs/PRD.md` (v0.3, frozen) and `docs/UX_SPEC.md`
(v0.2). This document changes neither; it refers to them instead of repeating them.

## 1. Goals

1. A business state is shown only after contract and grounding checks pass. Otherwise the API
   answers Assessment unavailable, a fallback with its cause kept, not a fourth state.
2. Every AI claim points at real, non-empty notes of the same relationship.
3. Facts, contacts and history never depend on the AI.
4. No date or recency logic anywhere in the assessment path.
5. The AI provider is swappable, and tests use a fake.
6. Smallest working setup: Next.js, FastAPI, one SQLite file, one AI provider. No queues,
   workers, Redis, vector database or orchestration framework.

## 2. Repository and runtimes

- `frontend/`: Next.js 16.3.5, React 19.2.8, TypeScript strict, Tailwind 4, ESLint 9, npm.
  Placeholder page, no test runner yet.
- `backend/`: FastAPI 0.141.1, Pydantic 2.13, Uvicorn, only `GET /`. Installed but unused so
  far: `pydantic-settings`, SQLAlchemy 2.0.54, httpx, pytest. No linter yet.
- No data in the repo. Sample rows exist only in `.context/` (untracked) until the seed step
  commits them under `backend/seed/`.

Runtimes are pinned: Node 24 LTS through the root `.nvmrc`, `engines` and an exact
`packageManager` with `engine-strict`, and Python 3.12 through the root `.python-version`.
Install the frontend with `npm ci`. A `package-lock.json` diff is allowed only when
`package.json` changes. The pin came first because regenerating the lockfile under an unpinned
Node and npm rewrote about 180 lines with no `package.json` change.

## 3. Architecture

```
Browser ── Next.js frontend (localhost:3000)
   │          server components fetch facts ──────┐
   │ client component fetches assessments         │
   └───────────── HTTP (CORS: known origin) ──────┤
                                                  ▼
                FastAPI backend (127.0.0.1:8000) — owns GEMINI_API_KEY
                  ├─ relationship routes   sync, no AI
                  └─ assessment route      async
                       ├─ model input + fingerprint   deterministic
                       ├─ provider interface ── HTTPS ──▶ Gemini API
                       ├─ contract + grounding checks deterministic
                       └─ store validated results
                  ▼
                SQLite file: facts + validated assessments
```

The browser calls FastAPI directly. There is no Next.js proxy: the Gemini key stays in FastAPI
either way, the backend URL is not a secret, and a proxy would add a hop and a failure point.
The cost is CORS configuration. CORS allows the configured frontend origin for GET. It is a
browser rule, not authentication and not a security boundary. A later deployment can put both
under one domain at the infrastructure level, still without a proxy.

## 4. Frontend responsibilities

- Routes `/` and `/relationships/[id]`, so the open relationship survives back, forward and
  reload.
- Facts load in server components through `frontend/lib/api.ts`. Responses are narrowed with
  type guards, not `as`.
- One client component handles assessments for both views. It requests the missing
  assessments, one relationship per request, at most two at a time (section 11.2); moves rows
  out of "Assessing…"; updates the detail in place and announces it; and shows "Try again"
  only for temporary failures. Plain `Suspense` streaming cannot move rows between sections or
  retry one item, which is why this is a client component.
- Grouping and alphabetical order happen in the browser, because results arrive one by one.
- "Based on" resolves interaction ids against the loaded history and shows original notes only.
- Dates are formatted from the `YYYY-MM-DD` string, never through `new Date()`, which can
  shift the day.
- Notes and AI text render as plain text.

## 5. Backend responsibilities and layout

The backend seeds and serves facts with no AI, computes the latest-interaction summary, runs
the assessment lifecycle with all AI checks, and owns the Gemini key.

```
backend/app/
  main.py  settings.py  db.py  relationships.py  seed.py
  assessment/
    contract.py      result models (section 8)
    model_input.py   model input, handles, fingerprint (sections 9 and 11)
    grounding.py     evidence checks (section 9)
    provider.py      AssessmentProvider protocol + errors
    gemini.py        Gemini implementation
    service.py       get_or_create_assessment()
backend/seed/        customers.csv, contacts.csv, interactions.csv
backend/tests/
```

## 6. Persistence

SQLite with sync SQLAlchemy. Seed data committed as CSV in `backend/seed/`. No migration
framework.

SQLite is one file with real constraints and transactions, needs no server, and SQLAlchemy is
already installed. Its limit is that it is not for multi-instance production, so the backend
runs as one instance. If the product grows past that, PostgreSQL is the likely next step; today
it would be a separate service with no need behind it. Alembic comes in once the schema must
change while keeping existing data. For now the seed command creates the tables. In-memory data
was rejected because assessments would be lost on restart, JSON files because they have no
atomic writes.

```
customers     id PK, name, status CHECK IN ('prospect','customer'), created_at DATE
contacts      id PK, customer_id FK, name, email, role, UNIQUE (id, customer_id)
interactions  id PK, customer_id FK, contact_id, type CHECK IN ('email','call','meeting','note'),
              occurred_at DATE, notes TEXT NOT NULL DEFAULT '',
              FK (contact_id, customer_id) → contacts (id, customer_id),
              INDEX (customer_id, occurred_at)
assessments   customer_id FK, fingerprint, result_json, provider, model, prompt_version,
              created_at, PRIMARY KEY (customer_id, fingerprint)
```

- The composite foreign key rejects an interaction whose contact belongs to another customer.
  `PRAGMA foreign_keys=ON` is set on every connection.
- `assessments` stores only validated outcomes: a grounded business assessment, or a valid
  insufficient-evidence answer (section 11.1). Technical and validation failures are never
  stored. Rows use real ids. Each row is re-validated on read; a row that fails is treated as
  missing.
- **Seeding:** `python -m app.seed` validates every CSV row with Pydantic, then replaces the
  fact tables in one transaction. A bad row aborts the load with the file, row and field named,
  and the old data stays.
- **Startup check:** the backend refuses to start if the tables are missing and says to run the
  seed command.
- `.context/` stays local-only. Nothing at runtime, in tests or in the build reads it.

## 7. API

Read-only: no create, update or delete routes. Error bodies never contain stack traces, SQL,
paths or secrets. `GET /` stays the health check.

### `GET /api/relationships` — list, no AI

```json
{ "relationships": [ {
    "id": "cust_009", "name": "Parkview Dental Studio", "status": "prospect",
    "latest_interaction": { "date": "2026-08-20", "count": 2, "types": ["email", "note"] },
    "assessment": { "status": "assessed", "state": "action_needed", "reason": "…" }
} ] }
```

- Sorted by name, case-insensitive. An empty database returns `[]`.
- `latest_interaction` is `null` with no interactions. `types` is the distinct set of types on
  the latest date, listed in id order. That order exists only so the presentation is stable.
  It is not chronology: ids do not say when an interaction happened, and no consumer may read
  the list, or any id order within a date, as first, last, before or after.
- `assessment` is one of:
  - `assessed`: a stored assessment whose fingerprint matches the current inputs;
  - `unavailable` with `insufficient_evidence`: a stored, matching insufficient-evidence
    outcome, or all notes empty (section 9.4);
  - `unavailable` with `no_interactions`: decided in code (section 9.4);
  - `null`: nothing valid stored for the current inputs. The frontend shows "Assessing…" and
    calls the assessment route.
- This route never waits for Gemini. Errors: 500.

### `GET /api/relationships/{id}` — detail facts, no AI

```json
{ "id": "cust_001", "name": "…", "status": "prospect", "created_at": "2026-05-12",
  "contacts": [ { "id": "contact_001", "name": "…", "email": "…", "role": "Owner" } ],
  "interactions": [ { "id": "int_005", "type": "note", "occurred_at": "2026-08-29",
                      "contact_id": "contact_001", "notes": "…" } ] }
```

- Interactions come newest date first. Id order is used only as a stable display order within
  a date.
- Errors: 404 and 500. Facts and history come in one response, so the UX case "part of the
  detail fails" applies only to the assessment area.

### `GET /api/relationships/{id}/assessment` — get or generate

Assesses one relationship per request, with at most one Gemini call and no request body.
Retry is the same GET: technical failures are never stored, so repeating the call tries again.
A stored outcome (business assessment or insufficient evidence) is returned without a Gemini
call while its fingerprint matches.

| Status | Body |
| --- | --- |
| 200 | `{"status": "assessed", …}` (below) |
| 200 | `{"status": "unavailable", "cause": "no_interactions" \| "insufficient_evidence"}` |
| 404 | `{"detail": "Relationship not found"}` |
| 502 | `{"detail": "…", "cause": "invalid_output"}`: reply malformed, broke the contract, or failed grounding |
| 503 | `{"detail": "…", "cause": "provider_timeout" \| "provider_error"}` |
| 500 | `{"detail": "Internal error"}`: bug or setup error |

```json
{ "status": "assessed", "state": "waiting",
  "summary":     { "text": "…", "evidence": ["int_045", "int_049"] },
  "reason":      { "text": "…", "evidence": ["int_049", "int_050"] },
  "open_items":  [ { "text": "…", "contact_ids": ["contact_012"], "evidence": ["int_048"] } ],
  "waiting_for": { "text": "…", "evidence": ["int_049"] },
  "next_action": null }
```

`waiting_for` appears only for `waiting`. `next_action` is required for `action_needed`,
optional for `waiting`, absent for `no_action_needed`. Storing a validated outcome writes
derived data only; facts are never written (PRD AC-14).

## 8. AI assessment contract

The reply is parsed into a tagged union. Assessment unavailable is not in the union; it is the
API's answer when no valid assessment exists.

```python
class Claim(BaseModel):           # all models: extra="forbid"
    text: str                     # plain text, length-limited
    evidence: list[str]           # opaque evidence handles, min 1
class OpenItem(Claim):
    contacts: list[str]           # contact handles, min 1

class InsufficientEvidence(BaseModel):
    outcome: Literal["insufficient_evidence"]
class _Assessed(BaseModel):
    outcome: Literal["assessed"]; summary: Claim; reason: Claim
class ActionNeeded(_Assessed):
    state: Literal["action_needed"]; open_items: list[OpenItem]
    next_action: Claim                                  # required
class Waiting(_Assessed):
    state: Literal["waiting"]; open_items: list[OpenItem]
    waiting_for: Claim                                  # required
    next_action: Claim | None                           # applies only after the awaited event
class NoActionNeeded(_Assessed):
    state: Literal["no_action_needed"]
    open_items: list[OpenItem] = Field(max_length=0)    # no next_action field at all

ModelResult = InsufficientEvidence | ActionNeeded | Waiting | NoActionNeeded
```

- **State rules live in the types.** `Action needed` without an action, `Waiting` without
  `waiting_for`, and `No action needed` with open items or an action cannot parse.
- **Explicit decline.** The model can answer `insufficient_evidence` instead of being forced
  into a state. That is a valid outcome that maps to Assessment unavailable. It is not a fourth
  state and not an invalid reply.
- **No confidence score.** The UX has no use for one, and a model's own score is not
  calibrated.
- **The schema sent to the model is flat**, all fields nullable. Our code drops nulls and parses
  into the union. Providers support only part of JSON Schema, and a later provider may not
  enforce a schema at all, so the union is always enforced on our side. The prompt explains
  meaning and rules only; the schema defines the structure.
- **Handles, not text copies.** Contacts and evidence are handles. The UI shows names and notes
  from the database.
- **The Waiting condition** is shown in the detail's next-step position, before any
  `next_action`, with its own "Based on". The UX spec allows either placement.
- **Prompt rules that code cannot check**, measured in the AI evaluation: `no_action_needed`
  needs notes that positively show nothing is needed; a Waiting `next_action` must not act
  before the event; a Waiting `reason` names what it waits for, so the list row shows it; never
  state who sent an interaction; never use dates or input position to decide state or urgency;
  `next_action` must come from the history.

## 9. Grounding and evidence validation

### 9.1 Opaque evidence handles

The model never sees ids such as `int_039` and `int_040`, because their numbers suggest an
order. Each interaction gets a handle: `e_` plus 10 hex characters of `sha256(interaction_id)`.
Contacts get `c_` handles the same way. Handles are stable and carry no order. The backend
keeps a per-request map from handle to real id and translates the reply back. A handle clash
within one relationship raises an error; that is a bug, not a model failure.

### 9.2 Model input

```json
{ "relationship_status": "prospect",
  "contacts": [ { "handle": "c_1a2b3c4d5e", "name": "Chris Evans", "role": "Dentist" } ],
  "interaction_dates": [ {
      "date": "2026-08-20", "same_date_group": "unordered",
      "interactions": [
        { "handle": "e_0f9e8d7c6b", "type": "note",  "contact": "c_1a2b3c4d5e", "notes": "…" },
        { "handle": "e_5b6a798012", "type": "email", "contact": "c_1a2b3c4d5e", "notes": "…" } ] } ] }
```

- Interactions on one date form an explicit unordered group, listed by handle.
- The system instruction says order comes only from `date` values. Input position, handles and
  ids never say what happened first.
- No current date is sent, and the model is told not to assume one.
- Empty notes are sent as `null`, so they cannot be cited.
- Only needed fields are sent. Customer name and emails are not.

### 9.3 Checks after the contract parses

Any failure rejects the whole assessment as `invalid_output`. Nothing is partly shown or
repaired. This may lower availability, but a half-trusted recommendation is never shown.

| # | Check |
| --- | --- |
| G1 | Every evidence handle is in this request's map. A handle from another relationship cannot resolve. |
| G2 | No cited interaction has empty notes. |
| G3 | Every claim keeps at least one handle after duplicates are removed. |
| G4 | Every open-item contact handle exists and is the contact of an interaction cited by that item. |
| G5 | No text contains an id or a handle. |
| G6 | Length limits: reason ≤ 200 characters, other claims ≤ 300. |

Code proves that every claim cites real notes of this relationship. Whether a note truly
supports the sentence is measured in `docs/AI_EVALUATION.md`.

### 9.4 Decided in code, no AI call

- No interactions → `no_interactions`. Gemini is never called. This fallback comes from the
  data, not from AI.
- Every note empty → `insufficient_evidence`, since nothing could be cited.

### 9.5 Notes are data

Instructions live only in the system instruction. The input is one JSON document of
relationship records, to be read as evidence only; text in a note that looks like an
instruction is still just a note. The model has no tools and no write path, and the contract
and grounding limit what a manipulated reply can show. The risk is reduced, not removed. The
PRD AC-10 note is a named evaluation case.

## 10. AI provider

Google Gemini through the official `google-genai` SDK. Baseline model `gemini-3.8-flash`, read
only from the `GEMINI_MODEL` setting.

The work is structured classification and summarising, not agent work. Gemini supports
schema-constrained JSON output, and the SDK accepts Pydantic-derived schemas. 3.8 Flash is the
current stable Flash model with structured output. It costs more per call than 2.5 Flash, but
with 12 seeded relationships and stored outcomes reused, call volume is tiny, and starting from
current Flash quality matters more than saving cost early. The evaluation compares quality,
grounding, latency and cost before deciding whether a cheaper model is enough. One provider is
simpler to build and debug; a second one now would double the integration work. Later
evaluation candidates are `gemini-2.5-flash` and DeepSeek; neither is in MVP scope.

If the key does not serve 3.8 Flash, set `GEMINI_MODEL` to another available model. No business
logic changes. There is no automatic provider or model fallback, because that would mix in a
model the evaluation did not cover.

```python
class AssessmentProvider(Protocol):
    name: str                     # "gemini"
    model: str                    # from settings
    async def generate(self, system_instruction: str, input_json: str,
                       response_schema: dict) -> str: ...   # raw JSON text
    # raises ProviderTimeout, ProviderError, ProviderEmptyResponse
```

`GeminiProvider` and a test `FakeProvider` implement it. Providers only send and receive, so a
DeepSeek provider would be one new file and a setting, with no change to business logic.

Gemini details:

- The official `google-genai` package only, no legacy Gemini SDKs. Use the SDK's async client
  (`client.aio`).
- Request structured JSON through the current `response_format` / JSON Schema mechanism of the
  Gemini API. Send the flat schema from section 8, the system instruction and a low
  temperature. Pydantic stays our validation boundary whatever the SDK returns.
- Implementation step 9 pins an exact `google-genai` version, confirms the call shape against
  that version's docs, and runs one small structured-output smoke test by hand before building
  the full provider.
- Wrap each call in `asyncio.timeout(30)`. Retry once, only for a timeout, 429, 5xx or
  connection error. Result mapping is in section 13.

Not added: the Anthropic SDK, LangChain, LlamaIndex or any orchestration framework. This is one
call with no tools.

## 11. Assessment lifecycle

### 11.1 Generate, validate, persist when appropriate, reuse

`get_or_create_assessment(customer_id)` handles one relationship:

1. Load facts (404 if missing). If section 9.4 applies, return with no AI call.
2. Build the model input and fingerprint. If a stored row matches, return it.
3. Make one async Gemini call.
4. Parse the contract, run G1–G6, and map handles to real ids.
5. Store or not, by outcome:

| Outcome | Stored? | Returned |
| --- | --- | --- |
| **A. Valid business assessment** (passed contract and grounding) | Yes, with the fingerprint | 200 `assessed` |
| **B. Valid insufficient-evidence answer** (passed the contract) | Yes, with the fingerprint | 200 `unavailable / insufficient_evidence` |
| **C. Technical or validation failure** (timeout, provider error, malformed reply, bad handle, grounding failure) | **No** | 502 / 503 (section 7) |

Storing A or B is `INSERT … ON CONFLICT DO NOTHING`, then re-read and return the stored row, so
racing requests return the same result. Outcome B is Assessment unavailable, not a business
state; it stays stable until the fingerprint changes, and no automatic retry happens while the
evidence is unchanged. A thin history is therefore not re-examined, which avoids paid calls
with nothing new to reason over. Outcome C is logged and returned; a later request, or "Try
again" where the UX allows it, tries again. Storing a failure would let a broken reply be
reused as if trustworthy. There are no time-based states and no scheduled refresh.

### 11.2 Bounded concurrency

1. The list page renders facts and any stored outcomes at once.
2. Rows with `assessment: null` show "Assessing…".
3. The frontend requests those rows' assessments, at most 2 at a time, through a small promise
   pool in the client component.
4. Each request covers one relationship. FastAPI makes one async Gemini call for it.
5. As each response arrives, that row moves to its group or to the unavailable section.

Two at a time finishes 12 relationships in about six rounds instead of twelve with a light load
on the API. Change it only if the Gemini limits checked during implementation justify it. The
limit is work scheduling, not business logic, and it is not backend rate limiting. It lives in
the frontend to avoid shared mutable state in the backend (`backend/AGENTS.md`), and row-by-row
updates stay simple.

Known limit: several browser tabs each run their own pool, and so does a detail view opened
while the list is still assessing. They can make extra calls for the same relationship; the
first stored row wins. That is acceptable for a local, single-user MVP. A public or multi-user
deployment needs backend rate and concurrency controls.

### 11.3 Staleness: deterministic fingerprint

A valid assessment never expires with time. It goes stale only when its inputs change.

```
fingerprint = sha256(canonical_json({          # sorted keys, fixed separators
    "prompt_version": PROMPT_VERSION,
    "prompt_sha":     sha256(system_instruction + response_schema),
    "provider":       provider.name,
    "model":          provider.model,
    "input":          model_input,              # exactly what section 9.2 sends
}))
```

`prompt_sha` catches a prompt edit made without a version bump. Fields the model never sees
(email, customer name) do not make a result stale. Stale rows are simply never read. This costs
a few metadata columns and one hash per request; a TTL was rejected because passing time must
not change results.

## 12. Async and concurrency

| Part | Choice | Why |
| --- | --- | --- |
| Fact routes, seed | sync `def`, sync SQLAlchemy | Short local reads; simplest code |
| Assessment route | `async def` | Waits seconds on Gemini without blocking the server |
| DB calls in that route | `await run_in_threadpool(...)` (Starlette) | Sync DB work must not block the event loop |
| Gemini | async SDK client, one call per request | Parallelism is bounded by the frontend (section 11.2) |

Two styles in one service, but the database code stays simple. Async SQLAlchemy was rejected
as complexity for short local reads; an all-sync backend was rejected because model calls would
hold server threads.

Timeouts: Gemini 30 s per try with one retry; frontend fact fetches 10 s; browser assessment
fetch 75 s, which covers one call plus one retry. Typical calls take seconds.

## 13. Failure handling mapped to the UX

No failure ever becomes `Action needed`, `Waiting` or `No action needed`. Facts, contacts and
history stay visible through every assessment failure.

| Failure | Backend | UX |
| --- | --- | --- |
| Gemini timeout after retry | 503 `provider_timeout` | Temporary-problem message; "Try again" in detail |
| Gemini 429, 5xx or connection error after retry | 503 `provider_error` | Temporary-problem message; "Try again" |
| Browser cannot reach the assessment route (network, CORS, timeout) | — | Temporary-problem message; "Try again" |
| Malformed or contract-breaking reply; empty, blocked or truncated reply | 502 `invalid_output` | "Cause not known" message |
| Unknown handle, or a handle from another relationship | 502 `invalid_output` (G1) | "Cause not known" message |
| Gemini 400, 401, 403, 404: bad key, model or request | Setup error, logged, 500 | "Cause not known" message |
| Response fails the frontend type guard | — | "Cause not known" message |
| Model says insufficient evidence (stored); all notes empty | 200 `insufficient_evidence` | "Not enough clear context" messages; no "Try again" |
| No interaction history | 200 `no_interactions` | "No interaction history" messages |
| Malformed seed data | Seed aborts, old data kept | Not a UI state |
| Database not seeded | Backend refuses to start | List load error |
| List or detail API failure | 5xx / network | Load error with "Try again", never an empty state |
| Relationship missing | 404 | "This relationship could not be found." |

"Try again" appears only for temporary failures. Invalid replies are not stored, so a later page
load tries again. Insufficient evidence (stored) and no interactions (from the data) are not
retried until the fingerprint changes.

## 14. Configuration and secrets

| Backend env (`pydantic-settings`, `backend/.env`) | Required | Default |
| --- | --- | --- |
| `GEMINI_API_KEY` | yes | — |
| `GEMINI_MODEL` | no | `gemini-3.8-flash` |
| `DATABASE_URL` | no | `sqlite:///./customer_pulse.db` |
| `CORS_ORIGINS` | no | `http://localhost:3000` |

- Frontend: `NEXT_PUBLIC_API_BASE_URL`, which is not a secret. The frontend never receives the
  Gemini key.
- A missing key fails startup with a clear message. That is better than showing "temporary
  problem" on every row. Tests use a dummy key and the fake provider.
- Code constants: timeouts, retry count and `PROMPT_VERSION` in the backend; the concurrency
  limit of 2 in the frontend. Nothing needs them per environment yet.
- The model id is read only from `settings.gemini_model`. No other code names a model.
- `.env` is gitignored. The `.env.example` files list names only.

## 15. Logging and observability

Standard `logging`, one line per event, no monitoring stack. Each assessment attempt logs:

- ids: `attempt_id` (ties the lines together), `customer_id`, fingerprint prefix, cache hit or
  miss;
- `provider`, `model`, `prompt_version`;
- AI call duration, try number, and token counts when available;
- `outcome` (`assessed`, `insufficient_evidence`, `invalid_output`, `provider_timeout`,
  `provider_error`, `no_interactions`), and the state when assessed;
- the validation failure category: `json`, `contract`, or a grounding check id plus field path
  (for example `G1 open_items[0].evidence[1]`);
- safe error details: exception class and HTTP status.

Never logged: keys, secrets, prompts, raw replies, note text, names, emails. To debug a bad
reply, a local script re-runs one relationship and prints the reply to the terminal only.

## 16. Security, privacy and deployment

The MVP is local and private. FastAPI binds to `127.0.0.1`. The assessment endpoint makes paid
calls with no sign-in, so it must never be publicly reachable. Local deployment is not
production security: a future public deployment needs access control (especially on the
assessment endpoint), rate or spend limits on AI calls, and PostgreSQL if there is more than
one backend instance. None of that is designed here.

Also: seeded data only while there is no sign-in; a read-only API; AI input and output treated
as untrusted (section 9.5) and rendered as plain text; only the section 9.2 fields sent to
Gemini; pinned dependencies.

## 17. Testing and tooling

Approved: pytest (exists), Ruff (`ruff check`, `ruff format --check`), Vitest, React Testing
Library with jsdom. Not added: mypy. Pydantic, type hints, Ruff and focused tests cover this
scope; add static type checking if the Python code grows. Every implementation step ships its
own tests. No test calls Gemini.

**Backend.** Each test gets a temp SQLite file. Async tests use the anyio pytest plugin, which is
already installed. `FakeProvider` returns scripted replies or errors and counts calls.

- Seed: a valid load works; a bad status or type, a duplicate id, or a contact from another
  customer is rejected; a failed load keeps the old data.
- Facts: the latest-interaction summary for one, several and zero interactions; history order;
  an empty list; 404.
- Model input: no current date; same-date groups are unordered and sorted by handle; handles
  are not ids and do not follow id order; no emails; an injection note stays inside the data.
- Fingerprint: changes with notes, status, contacts sent, prompt version, prompt text or model;
  stays the same for email or name changes and for passing time.
- Contract: each state's rules; extra fields are rejected.
- Grounding: G1–G6, including a handle from another relationship and an empty-note citation.
- Lifecycle: no interactions → no Gemini call; a valid assessment is stored and reused (fake
  called once); a valid insufficient-evidence answer is stored and reused, and re-assessed only
  after the fingerprint changes; timeout, provider error, malformed reply, bad handle and
  grounding failure each store nothing, map to the right status and cause, and are retried on
  the next request; a racing insert returns the stored row; fact tables are unchanged
  afterwards (AC-14).

**Frontend.** Tests cover what the owner sees:

- List: grouping and order, the count line with zeros, the "Assessing…" and unavailable
  sections, rows moving when results arrive, never more than 2 assessment requests at once.
- Rows: the latest-interaction text for one and for several interactions on a date.
- Dates and history: dates show without a day shift; each date heading and the same-date note
  appear.
- Evidence: "Based on" shows original notes, and is absent when unavailable.
- Messages: each backend response shows the right message; "Try again" appears only for
  temporary failures; load errors never look like empty states.

Vitest cannot render async Server Components, so page logic lives in plain functions and client
components. Lint and the type-check from `frontend/AGENTS.md` still run.

## 18. Evaluation hooks

`docs/AI_EVALUATION.md` owns model quality, fixtures and the acceptance gate. This design gives
it: swappable `AssessmentProvider` implementations; a deterministic model input; contract and
grounding checks reusable as hard gates; and `provider`, `model` and `prompt_version` on every
stored result and log line. A harness can run the same seeded cases through
`get_or_create_assessment` for any provider or model.

## 19. Running locally

Two terminals. SQLite is a local file. Only FastAPI talks to Gemini. No Docker: pinned runtimes
and two commands are enough.

```bash
cd backend && source .venv/bin/activate && pip install -r requirements.txt
```

```bash
cd backend && python -m app.seed && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend && nvm use && npm ci && npm run dev
```

Create the venv once with Python 3.12 and set `GEMINI_API_KEY` in `backend/.env`.
`frontend/.env.local` sets `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`.

## 20. Alternatives considered

Alternatives already explained where the decision is made (persistence, provider, fingerprint,
async split, storing failures) are not repeated here.

| Alternative | Why not |
| --- | --- |
| Generate assessments on every request, or all at seed time | Repeated cost, or no retry path and no loading state |
| Workers, queues, Redis, brokers, SSE, WebSockets, streaming | A frontend limit of 2 covers 12 relationships |
| A shared backend semaphore instead of the frontend pool | Shared mutable state across requests |
| One AI call for all relationships | Mixes histories; one failure breaks every row |
| A second "verifier" model call | Doubles cost and latency; revisit if the evaluation shows unsupported claims |
| Orchestration frameworks, vector database, tool calling | One call over one history needs none |

## 21. Implementation sequence

One reviewed commit per step. Each step ships its tests.

1. Runtimes: Node 24 / npm pin, Python 3.12, one lockfile regeneration. Done.
2. Development and test tooling: Ruff, Vitest and React Testing Library.
3. Seed CSV files and the validated loader.
4. Persistence: tables, sessions, startup check.
5. Read-only APIs (list and detail) and CORS.
6. Frontend list and detail from facts only, with loading, empty, error and not-found states.
7. AI contract, model input, handles, fingerprint, fake provider.
8. Grounding checks. They come before storage, so nothing unchecked is ever persisted.
9. Gemini provider: `google-genai` pinned, call shape confirmed, a manual structured-output
   smoke test, then the provider and its error mapping. Also confirm the key serves
   `gemini-3.8-flash` and note its rate limits; if the limits allow more, revisit the frontend
   limit of 2.
10. Assessment lifecycle: service, outcome storage, route, logging.
11. Frontend assessment states: request pool of 2, "Based on", unavailable causes, "Try again",
    announcements.
12. Cross-cutting test pass against the UX acceptance checklist.
13. The evaluation harness (`docs/AI_EVALUATION.md`).
14. Polish and README.

No architecture decisions remain open.
