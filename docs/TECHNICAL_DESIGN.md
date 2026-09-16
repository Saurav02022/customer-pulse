# Customer Pulse — technical design v0.2

Status: **Approved for MVP implementation.**

How the MVP is built. Behaviour comes from `docs/PRD.md` (v0.3, frozen) and `docs/UX_SPEC.md`
(v0.2, approved); this document changes neither and refers to them instead of repeating them.

## 1. Technical goals

1. One of the three business states is shown only after contract and evidence checks pass.
   Otherwise: Assessment unavailable (a fallback, not a state), with its cause kept.
2. Every AI claim points at real, non-empty notes of the same relationship.
3. Facts, contacts and history never depend on the AI.
4. No date or recency logic in the assessment path.
5. The AI provider is swappable, and tests use a fake.
6. Smallest working setup: Next.js, FastAPI, one SQLite file, one AI provider.

## 2. Current repository and runtime versions

- `frontend/`: Next.js 16.3.5, React 19.2.8, TypeScript strict, Tailwind 4, ESLint 9, npm.
  Placeholder page, no test runner.
- `backend/`: FastAPI 0.141.1, Pydantic 2.13, Uvicorn, only `GET /`. Installed but unused:
  `pydantic-settings`, SQLAlchemy 2.0.54, httpx, pytest. No linter.
- No data in the repo. Sample rows exist only in `.context/` (untracked).

**Lockfile churn (seen 2026-09-16).** This machine runs Node v25.2.1 (not LTS) with npm 11.8.0.
Regenerating `frontend/package-lock.json` on a scratch copy rewrote about 180 lines with no
`package.json` change. `npm install --dry-run` wants to remove 4 packages. Nothing in the repo
pins Node or npm.

**Decision: Node 24 LTS and Python 3.12**, fixed before any dependency work (step 1):

- add root `.nvmrc` and root `.python-version`, plus `engines` and an exact npm `packageManager`;
- choose the npm version after Node 24 is installed;
- regenerate the lockfile **once**, then use `npm ci`;
- a lockfile diff is allowed only when `package.json` changes.

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

- **The browser calls FastAPI directly, with no Next.js proxy.** The Gemini key stays in FastAPI
  either way, and the backend URL is not a secret. A proxy adds an app hop and a failure point
  for no gain. Cost: CORS config.
- **CORS** allows the configured frontend origin for GET. It is a browser rule, not
  authentication and not a security boundary.
- A later deployment can put both under one domain at the infrastructure level, still without a
  proxy.

## 4. Frontend responsibilities

- Routes `/` and `/relationships/[id]`, so the open relationship survives back, forward and
  reload.
- Facts load in server components through `frontend/lib/api.ts`. Responses are narrowed with
  type guards, not `as`.
- One client component handles assessments for both views. It:
  - requests the missing assessments, one relationship per request, at most two at a time
    (§11.2);
  - moves rows out of "Assessing…";
  - updates the detail in place and announces it;
  - shows "Try again" only for temporary failures.
  Plain `Suspense` streaming cannot move rows between sections or retry one item.
- Grouping and alphabetical order happen in the browser, because results arrive one by one.
- "Based on" resolves interaction ids against the loaded history and shows original notes only.
- Dates are formatted from the `YYYY-MM-DD` string, never `new Date()`, which can shift the day.
- Notes and AI text render as plain text.

## 5. Backend responsibilities and layout

The backend seeds and serves facts (no AI). It computes the latest-interaction summary. It runs
the assessment lifecycle and all AI checks, and it owns the Gemini key.

```
backend/app/
  main.py  settings.py  db.py  relationships.py  seed.py
  assessment/
    contract.py      result models (§8)
    model_input.py   model input, handles, fingerprint (§9, §11)
    grounding.py     evidence checks (§9)
    provider.py      AssessmentProvider protocol + errors
    gemini.py        Gemini implementation
    service.py       get_or_create_assessment()
backend/seed/        customers.csv, contacts.csv, interactions.csv
backend/tests/
```

## 6. Persistence

**Decision: SQLite with sync SQLAlchemy. Seed data committed as CSV in `backend/seed/`. No
migration framework.**

- **Why:** one file, no server, real constraints and transactions. SQLAlchemy is already
  installed.
- **Limit:** SQLite is not for multi-instance production, so the backend runs as one instance.
- **Later:** PostgreSQL is the likely next step if the product grows. Migrations (Alembic) come
  in once the schema must change while keeping existing data. For now, the seed command creates
  the tables.
- **`.context/`** stays local-only. Nothing at runtime, in tests or in the build reads it.
- **Rejected:**
  - in-memory data: assessments lost on restart, and shared mutable state;
  - JSON files: no atomic writes;
  - PostgreSQL now: a separate service with no MVP need.

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
- `assessments` stores **only validated outcomes**: a grounded business assessment, or a valid
  insufficient-evidence answer (§11.1). Technical and validation failures are never stored.
  Rows use real ids. Each row is re-validated on read, and a row that fails is treated as
  missing.
- **Seeding:** `python -m app.seed` validates every CSV row with Pydantic, then replaces the fact
  tables in one transaction. A bad row aborts the load with the file, row and field named, and
  the old data stays.
- **Startup check:** the backend refuses to start if the tables are missing, and says to run the
  seed command.

## 7. API

Read-only. No create, update or delete routes. Error bodies never contain stack traces, SQL,
paths or secrets. `GET /` stays the health check.

### `GET /api/relationships`: list (no AI)

```json
{ "relationships": [ {
    "id": "cust_009", "name": "Parkview Dental Studio", "status": "prospect",
    "latest_interaction": { "date": "2026-08-20", "count": 2, "types": ["email", "note"] },
    "assessment": { "status": "assessed", "state": "action_needed", "reason": "…" }
} ] }
```

- Sorted by name, case-insensitive. An empty database returns `[]`.
- `latest_interaction` is `null` with no interactions. `types` is the distinct set of types on
  the latest date, in id order.
- `assessment` is one of:
  - `assessed`: a stored assessment whose fingerprint matches the current inputs;
  - `unavailable` with `insufficient_evidence`: a stored, matching insufficient-evidence
    outcome, or all notes empty (§9.4);
  - `unavailable` with `no_interactions`: decided in code (§9.4);
  - `null`: nothing valid stored for the current inputs. The frontend shows "Assessing…" and
    calls the assessment route.
- This route never waits for Gemini. Errors: 500.

### `GET /api/relationships/{id}`: detail facts (no AI)

```json
{ "id": "cust_001", "name": "…", "status": "prospect", "created_at": "2026-05-12",
  "contacts": [ { "id": "contact_001", "name": "…", "email": "…", "role": "Owner" } ],
  "interactions": [ { "id": "int_005", "type": "note", "occurred_at": "2026-08-29",
                      "contact_id": "contact_001", "notes": "…" } ] }
```

- Interactions come newest date first. Id order is used only as a stable display order within a
  date.
- Errors: 404 and 500. Facts and history come in one response, so UX "part of the detail fails"
  applies only to the assessment area.

### `GET /api/relationships/{id}/assessment`: get or generate

Assesses **one** relationship per request, with at most one Gemini call. No request body.
**Retry is the same GET.** Technical failures are never stored, so repeating the call tries
again. A stored outcome (business assessment or insufficient evidence) is returned without a
Gemini call while its fingerprint matches.

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

- `waiting_for` appears only for `waiting`.
- `next_action` is required for `action_needed`, optional for `waiting`, and absent for
  `no_action_needed`.
- Storing a validated outcome writes derived data only. Facts are never written (AC-14).

## 8. AI assessment contract

The reply is parsed into a tagged union. `Assessment unavailable` is not in the union. It is the
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

- **State rules live in the types.** These replies cannot parse:
  - `Action needed` without an action;
  - `Waiting` without `waiting_for`;
  - `No action needed` with open items or an action.
- **Explicit decline.** The model can answer `insufficient_evidence` instead of being forced into
  a state. That answer is a valid outcome that maps to Assessment unavailable. It is not a
  fourth state and not an invalid reply.
- **No confidence score.** The UX has no use for one, and a model's own score is not calibrated.
- **The schema sent to the model is flat** (all fields nullable). Our code drops nulls and parses
  into the union. Providers support only part of JSON Schema, and a later provider may not
  enforce a schema at all, so the union is always enforced on our side. The prompt does not
  repeat the JSON structure; the schema defines it. The prompt explains meaning and rules only.
- **Handles, not text copies.** Contacts and evidence are handles. The UI shows names and notes
  from the database.
- **The Waiting condition** is shown in the detail's next-step position, before any
  `next_action`, with its own "Based on" (allowed by UX §7).
- **Prompt rules that code cannot check** (measured later):
  - `no_action_needed` needs notes that positively show nothing is needed;
  - a Waiting `next_action` must not act before the event;
  - a Waiting `reason` names what it waits for, so the list row shows it;
  - never state who sent an interaction;
  - never use dates or input position to decide state or urgency;
  - `next_action` must come from the history.

## 9. Grounding and evidence validation

### 9.1 Opaque evidence handles

The model never sees ids such as `int_039` and `int_040`, because their numbers suggest an order.

- Each interaction gets a handle: `e_` plus 10 hex characters of `sha256(interaction_id)`.
  Contacts get `c_` handles the same way.
- Handles are stable and carry no order.
- The backend keeps a per-request map from handle to real id and translates the reply back.
- A handle clash within one relationship raises an error. That is a bug, not a model failure.

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

- **Same date:** interactions on one date form an explicit **unordered group**, listed by handle.
- **Order:** the system instruction says order comes only from `date` values. Input position,
  handles and ids never say what happened first.
- **No current date** is sent, and the model is told not to assume one.
- **Empty notes** are sent as `null`, so they cannot be cited.
- **Only needed fields** are sent. Customer name and emails are not.

### 9.3 Checks after the contract parses

Any failure rejects the **whole** assessment as `invalid_output`. Nothing is partly shown or
repaired. This may lower availability, but a half-trusted recommendation is never shown.

| # | Check |
| --- | --- |
| G1 | Every evidence handle is in this request's map. A handle from another relationship cannot resolve. |
| G2 | No cited interaction has empty notes. |
| G3 | Every claim keeps at least one handle after duplicates are removed. |
| G4 | Every open-item contact handle exists and is the contact of an interaction cited by that item. |
| G5 | No text contains an id or a handle. |
| G6 | Length limits: reason ≤ 200 characters, other claims ≤ 300. |

Code proves that every claim cites real notes of this relationship. Whether a note truly supports
the sentence is measured in the AI evaluation.

### 9.4 Decided in code, no AI call

- No interactions → `no_interactions`. Gemini is never called. This fallback comes from the
  data, not from AI.
- Every note empty → `insufficient_evidence`, since nothing could be cited.

### 9.5 Notes are data

- Instructions live only in the system instruction.
- The input is one JSON document of relationship records, to be read as evidence only. Text in a
  note that looks like an instruction is still just a note.
- The model has no tools and no write path.
- The contract and grounding limit what a manipulated reply can show.
- The risk is reduced, not removed. The AC-10 note is a named evaluation case.

## 10. AI provider

**Decision: Google Gemini through the official `google-genai` SDK. Baseline model
`gemini-3.8-flash`, read only from the `GEMINI_MODEL` setting.**

- **Why Gemini:** the work is structured classification and summarising, not agent work. Gemini
  supports schema-constrained JSON output, and the SDK accepts Pydantic-derived schemas.
- **Why 3.8 Flash:** it is the current stable Flash model and supports structured output. With
  12 seeded relationships, starting from the current Flash quality matters more than saving
  cost early.
- **Trade-off:** 3.8 Flash costs more per call than 2.5 Flash. MVP call volume is tiny, and
  stored outcomes are reused. The evaluation compares quality, grounding, latency and cost
  before deciding whether a cheaper model is enough.
- **If the key does not serve 3.8 Flash:** set `GEMINI_MODEL` to another available model. No
  business logic changes. There is no automatic provider or model fallback in the MVP.
- **Why one provider:** simpler to build and debug. Comparing providers is deferred to the
  evaluation.
- **Later evaluation candidates only:** `gemini-2.5-flash` and DeepSeek. They are compared on
  correctness, grounding, structured-output reliability, latency and cost. Neither is in MVP
  scope.
- **Not added:** Anthropic SDK, LangChain, LlamaIndex or any orchestration framework. This is one
  call with no tools.

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

**Gemini details:**

- Use the official `google-genai` package only. No legacy Gemini SDKs.
- Use the SDK's async client (`client.aio`) for the call.
- Request structured JSON through the current `response_format` / JSON Schema mechanism of the
  Gemini API. Send the flat schema from §8, the system instruction and a low temperature.
- Pydantic stays our validation boundary, whatever the SDK returns.
- Step 9 pins an exact `google-genai` version and confirms the call shape against that version's
  docs. Before building the full provider, it runs one small structured-output smoke test by
  hand.
- Wrap each call in `asyncio.timeout(30)`.
- Retry once, only for a timeout, 429, 5xx or connection error.

| Gemini result | Maps to |
| --- | --- |
| Timeout after retry | 503 `provider_timeout` |
| 429, 5xx or connection error after retry | 503 `provider_error` |
| 400, 401, 403, 404 (bad key, model or request) | Setup error: logged, 500 |
| Empty, blocked or truncated reply | 502 `invalid_output` |

## 11. Assessment lifecycle

### 11.1 Flow: generate → validate → persist when appropriate → reuse

`get_or_create_assessment(customer_id)` handles one relationship:

1. Load facts (404 if missing). If §9.4 applies, return with no AI call.
2. Build the model input and fingerprint. If a stored row matches, return it.
3. Make one async Gemini call.
4. Parse the contract, run G1–G6, and map handles to real ids.
5. Store or not, by outcome:

| Outcome | Stored? | Returned |
| --- | --- | --- |
| **A. Valid business assessment** (passed contract and grounding) | Yes, with the fingerprint | 200 `assessed` |
| **B. Valid insufficient-evidence answer** (passed the contract) | Yes, with the fingerprint | 200 `unavailable / insufficient_evidence` |
| **C. Technical or validation failure** (timeout, provider error, malformed reply, bad handle, grounding failure) | **No** | 502 / 503 (§7) |

- **Storing A or B:** `INSERT … ON CONFLICT DO NOTHING`, then re-read and return the stored row.
  Racing requests therefore return the same result.
- **Outcome B** is Assessment unavailable, not a business state. It stays stable until the
  fingerprint changes, and no automatic retry happens while the evidence is unchanged.
  Trade-off: a thin history is not re-examined, which avoids paid calls with nothing new to
  reason over.
- **Outcome C** is logged and returned. A later request, or "Try again" where the UX allows it,
  tries again.
- No time-based states and no scheduled refresh.

### 11.2 Bounded concurrency

1. The list page renders facts and any stored outcomes at once.
2. Rows with `assessment: null` show "Assessing…".
3. The frontend requests those rows' assessments, **at most 2 at a time**. This is a small
   promise pool in the client component.
4. Each request covers one relationship. FastAPI makes one async Gemini call for it.
5. As each response arrives, that row moves to its group or to the unavailable section.

- **Why 2:** 12 relationships finish in about six rounds instead of twelve, with a light load on
  the API. Change it only if the Gemini limits checked during implementation justify it.
- **What the limit is:** work scheduling only, not business logic.
- **What it avoids:** shared mutable state in the backend (`backend/AGENTS.md`). Row-by-row
  updates also stay simple.
- **Known limit:** several browser tabs each run their own pool. So can a detail view opened
  while the list is still assessing. They can make extra calls for the same relationship; the
  first stored row wins. This is acceptable for a local, single-user MVP.
- **Later:** a public or multi-user deployment needs backend rate and concurrency controls.
- **Not added:** queues, Redis, workers, SSE, WebSockets, streaming.

### 11.3 Staleness: deterministic fingerprint

A valid assessment never expires with time. It goes stale only when its inputs change.

```
fingerprint = sha256(canonical_json({          # sorted keys, fixed separators
    "prompt_version": PROMPT_VERSION,
    "prompt_sha":     sha256(system_instruction + response_schema),
    "provider":       provider.name,
    "model":          provider.model,
    "input":          model_input,              # exactly what §9.2 sends
}))
```

- `prompt_sha` catches a prompt edit made without a version bump.
- Fields the model never sees (email, customer name) do not make a result stale.
- Stale rows are simply never read.
- **Trade-off:** a few metadata columns and one hash per request, instead of an arbitrary TTL.

## 12. Async and concurrency

| Part | Choice | Why |
| --- | --- | --- |
| Fact routes, seed | sync `def`, sync SQLAlchemy | Short local reads; simplest code |
| Assessment route | `async def` | Waits seconds on Gemini without blocking the server |
| DB calls in that route | `await run_in_threadpool(...)` (Starlette) | Sync DB work must not block the event loop |
| Gemini | async SDK client, one call per request | Parallelism is bounded by the frontend (§11.2) |

- **Not added:** async SQLAlchemy, workers, Redis, queues, brokers.
- **Trade-off:** two styles in one service, but the database code stays simple.
- **Timeouts:**
  - Gemini: 30 s per try, with one retry;
  - frontend fact fetches: 10 s;
  - browser assessment fetch: 75 s, which covers one call plus one retry. Typical calls take
    seconds.

## 13. Failure handling mapped to the UX

No failure ever becomes `Action needed`, `Waiting` or `No action needed`. Facts, contacts and
history stay visible through every assessment failure.

| Failure | Backend | UX |
| --- | --- | --- |
| Gemini timeout | 503 `provider_timeout` | Temporary-problem message; "Try again" in detail |
| Gemini API error, rate limit, connection | 503 `provider_error` | Temporary-problem message; "Try again" |
| Browser can't reach the assessment route (network, CORS, timeout) | — | Temporary-problem message; "Try again" |
| Malformed or contract-breaking reply; empty or blocked reply | 502 `invalid_output` | "Cause not known" message |
| Unknown handle, or a handle from another relationship | 502 `invalid_output` (G1) | "Cause not known" message |
| Gemini setup error (key or model) | 500, logged | "Cause not known" message |
| Response fails the frontend type guard | — | "Cause not known" message |
| Model says insufficient evidence (stored); all notes empty | 200 `insufficient_evidence` | "Not enough clear context" messages; no "Try again" |
| No interaction history | 200 `no_interactions` | "No interaction history" messages |
| Malformed seed data | Seed aborts, old data kept | Not a UI state |
| Database not seeded | Backend refuses to start | List load error |
| List or detail API failure | 5xx / network | Load error with "Try again", never an empty state |
| Relationship missing | 404 | "This relationship could not be found." |

"Try again" appears only for temporary failures (UX §7).

- **Invalid replies:** not stored, so a later page load tries again.
- **Insufficient evidence** (stored) and **no interactions** (from the data): neither is retried
  until the fingerprint changes.

## 14. Configuration and secrets

| Backend env (`pydantic-settings`, `backend/.env`) | Required | Default |
| --- | --- | --- |
| `GEMINI_API_KEY` | yes | — |
| `GEMINI_MODEL` | no | `gemini-3.8-flash` |
| `DATABASE_URL` | no | `sqlite:///./customer_pulse.db` |
| `CORS_ORIGINS` | no | `http://localhost:3000` |

- **Frontend:** `NEXT_PUBLIC_API_BASE_URL`, which is not a secret. The frontend never receives
  the Gemini key.
- **Missing key:** startup fails with a clear message (`backend/AGENTS.md`). That is better than
  showing "temporary problem" on every row. Tests use a dummy key and the fake provider.
- **Code constants:** timeouts, retry count and `PROMPT_VERSION` in the backend; the concurrency
  limit of 2 in the frontend. Nothing needs them per environment yet.
- **Model id:** read only from `settings.gemini_model`. No other code names a model.
- **Env files:** `.env` is gitignored. The `.env.example` files list names only.

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

**Never logged:** keys, secrets, prompts, raw replies, note text, names, emails. To debug a bad
reply, a local script re-runs one relationship and prints the reply to the terminal only.

## 16. Security and privacy

- **Local and private MVP.** FastAPI binds to `127.0.0.1`. The assessment endpoint makes paid
  calls with no sign-in, so it must never be publicly reachable.
- **Seeded data only.** No real customer data while there is no sign-in.
- **Read-only API.**
- **Untrusted AI input and output** (§9.5), rendered as plain text.
- **Minimal data to Gemini:** only the fields in §9.2.
- **Pinned dependencies.**

## 17. Testing and tooling

- **Approved:** pytest (exists), Ruff (`ruff check`, `ruff format --check`), Vitest, React
  Testing Library with jsdom.
- **Not added:** mypy. Pydantic, type hints, Ruff and focused tests cover this scope. Add static
  type checking if the Python code grows.
- Every step ships its own tests. No test calls Gemini.

**Backend.** Each test gets a temp SQLite file. Async tests use the anyio pytest plugin, which is
already installed. `FakeProvider` returns scripted replies or errors and counts calls.

- **Seed:** a valid load works. A bad status or type, a duplicate id, or a contact from another
  customer is rejected. A failed load keeps the old data.
- **Facts:** the latest-interaction summary for one, several and zero interactions; history
  order; an empty list; 404.
- **Model input:**
  - no current date;
  - same-date groups are unordered and sorted by handle;
  - handles are not ids and don't follow id order;
  - no emails;
  - an injection note stays inside the data.
- **Fingerprint:**
  - changes with notes, status, contacts sent, prompt version, prompt text or model;
  - stays the same for email or name changes and for passing time.
- **Contract:** each state's rules; extra fields are rejected.
- **Grounding:** G1–G6, including a handle from another relationship and an empty-note citation.
- **Lifecycle:**
  - no interactions → no Gemini call;
  - a valid assessment is stored and reused (fake called once);
  - a valid insufficient-evidence answer is stored and reused, and is re-assessed only after the
    fingerprint changes;
  - timeout, provider error, malformed reply, bad handle and grounding failure each store
    nothing, map to the right status and cause, and are retried on the next request;
  - a racing insert returns the stored row;
  - fact tables are unchanged afterwards (AC-14).

**Frontend.** Tests cover what the owner sees:

- **List:** grouping and order, the count line with zeros, the "Assessing…" and unavailable
  sections, rows moving when results arrive, and never more than 2 assessment requests at once.
- **Rows:** the latest-interaction text for one and for several interactions on a date.
- **Dates and history:** dates show without a day shift; each date heading and the same-date note
  appear.
- **Evidence:** "Based on" shows original notes, and is absent when unavailable.
- **Messages:** each backend response shows the right message; "Try again" appears only for
  temporary failures; load errors never look like empty states.

Vitest cannot render async Server Components, so page logic lives in plain functions and client
components. Lint and the type-check from `frontend/AGENTS.md` still run.

## 18. Boundary for `docs/AI_EVALUATION.md`

**Later, not now.** That document will cover:

- state correctness and next-action correctness;
- grounding correctness and the unsupported-claim rate;
- insufficient-evidence behaviour and structured-output reliability;
- same-date chronology safety and no sender claims;
- latency and cost;
- provider and model comparison: the `gemini-3.8-flash` baseline against `gemini-2.5-flash`
  and DeepSeek candidates;
- numeric targets (PRD QR-1) and the gate for prompt or model changes.

Its test cases are the 12 seeded relationships, labelled by a person, plus crafted ones:
- an injection note;
- thin or empty notes;
- a date that has passed;
- same-date conflicts;
- two contacts.

**Hooks this design provides:**

- swappable `AssessmentProvider` implementations;
- a deterministic model input;
- contract and grounding checks that can be reused as hard gates;
- `provider`, `model` and `prompt_version` on every stored result and log line.

A harness can run the same seeded cases through `get_or_create_assessment` for any provider or
model.

## 19. Local run model

Two terminals. SQLite is a local file. Only FastAPI talks to Gemini.

```bash
cd backend && source .venv/bin/activate && pip install -r requirements.txt
```

```bash
cd backend && python -m app.seed && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend && nvm use && npm ci && npm run dev
```

- **Backend setup:** create the venv once with Python 3.12, and set `GEMINI_API_KEY` in
  `backend/.env`.
- **Frontend setup:** `frontend/.env.local` sets
  `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`.
- **No Docker:** pinned runtimes and two commands are enough.

## 20. Deployment direction

The MVP is local and private. No public deployment is designed. A future public deployment
needs:

- access control, especially on the assessment endpoint;
- rate or spend limits on AI calls;
- PostgreSQL if there is more than one backend instance.

None of this is in the MVP.

## 21. Rejected alternatives

| Alternative | Why not |
| --- | --- |
| Next.js proxy / BFF | Extra hop and failure point; the key is already server-side |
| All-sync backend | Slow model calls would hold server threads |
| Async SQLAlchemy | Adds complexity for short local reads |
| Generate on every request / all at seed time | Repeated cost / no retry path and no loading state |
| Workers, queues, Redis, brokers, SSE, WebSockets | A frontend limit of 2 covers 12 relationships |
| Shared backend semaphore | Shared mutable state across requests (`backend/AGENTS.md`) |
| Storing technical or validation failures | A broken reply would be reused as if trustworthy |
| Not storing insufficient-evidence answers | Paid calls repeat with no new evidence |
| Automatic model or provider fallback | Mixes in a model the evaluation did not cover |
| TTL expiry | Passing time must not change results |
| Showing the valid parts of a rejected result | Mixes trusted and untrusted claims |
| One AI call for all relationships | Mixes histories; one failure breaks every row |
| Real ids or list position visible as order | Invents same-date chronology |
| Confidence scores | No UX use; not calibrated |
| Second "verifier" model call | Doubles cost and latency; revisit if the eval shows unsupported claims |
| Gemini + DeepSeek now | Double integration work; deferred to the eval |
| Orchestration frameworks, vector DB, tool calling | One call over one history needs none |

## 22. Implementation sequence

One reviewed commit per step. Each step ships its tests.

1. Runtimes: Node 24 / npm pin, Python 3.12, one lockfile regeneration.
2. Development and test tooling: Ruff, Vitest and React Testing Library.
3. Seed CSV files and the validated loader.
4. Persistence: tables, sessions, startup check.
5. Read-only APIs (list and detail) and CORS.
6. Frontend list and detail from facts only, with loading, empty, error and not-found states.
7. AI contract, model input, handles, fingerprint, fake provider.
8. Grounding checks. They come before storage, so nothing unchecked is ever persisted.
9. Gemini provider: `google-genai` pinned, call shape confirmed, a manual structured-output
   smoke test, then the provider and its error mapping.
10. Assessment lifecycle: service, outcome storage, route, logging.
11. Frontend assessment states: request pool of 2, "Based on", unavailable causes, "Try again",
    announcements.
12. Cross-cutting test pass against the UX acceptance checklist.
13. `AI_EVALUATION.md` and the evaluation harness.
14. Polish and README.

## 23. Open decisions

**No architecture decisions remain open.**

These checks happen during implementation:

1. **Step 1:** install Node 24 LTS, then pin the npm version that ships with it.
2. **Step 9:** confirm the Gemini key serves `gemini-3.8-flash`, and note its rate limits. If
   the model is not served, set `GEMINI_MODEL` to an available one. If the limits allow more,
   revisit the frontend limit of 2.
3. **Step 9:** pin the exact `google-genai` version and confirm the call shape with the smoke
   test.
