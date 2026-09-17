# Customer Pulse

A small CRM for a business owner with a few prospects and customers. It turns each
relationship's interaction history into a grounded assessment of whether anything needs doing
now. The CRM facts themselves — contacts, dates and notes — are always shown directly, whether or
not the AI assessment works.

## What it does

- **Relationship list.** Every relationship with its status, latest interaction and assessment,
  grouped by state and sorted by name.
- **Relationship detail.** Contacts, the full interaction history, and the assessment with its
  reason, summary, open items and next step.
- **Three business states:** Action needed, Waiting, No action needed.
- **Assessment unavailable.** Shown when the product cannot give a trustworthy assessment. It is
  not a fourth state.
- **Evidence.** Every statement in an assessment links to the interactions it is based on, and
  "Show in history" jumps to them.
- **Stored assessments.** Validated results are saved under a fingerprint of their inputs, so an
  unchanged relationship is not sent to the model again.
- **Read-only.** The app works on seeded data. It does not create, edit or send anything.

## Architecture

| Part | Stack |
| --- | --- |
| Frontend | Next.js 16 (App Router), React 19, TypeScript (strict), Tailwind CSS 4; Vitest and React Testing Library |
| Backend | FastAPI, Pydantic 2, SQLAlchemy 2 on SQLite, pydantic-settings; pytest and Ruff |
| AI | Google Gemini (`gemini-3.8-flash`) through `google-genai`, structured JSON output |

```
Browser (Next.js)
  │  GET /api/relationships                  facts + stored outcome, no AI call
  │  GET /api/relationships/{id}             facts only
  │  GET /api/relationships/{id}/assessment  at most 2 at a time
  ▼
FastAPI
  └─ assessment route
       ├─ decided in code?   no interactions / only empty notes → unavailable, no AI call
       ├─ stored result for this fingerprint? → return it
       └─ otherwise: model input → Gemini → strict parse → grounding checks → store → return
```

The browser calls FastAPI directly; there is no Next.js API proxy. Facts load first and never
wait for an assessment.

## Requirements

- Node **v24.18.0** (`.nvmrc`), npm **11.16.0** (`packageManager`; `engine-strict` is on)
- Python **3.12.13** (`.python-version`)
- A Google Gemini API key for assessments

## Backend setup

Backend-specific setup, API and operation notes are in [`backend/README.md`](backend/README.md).

```bash
cd backend
python -m venv .venv          # with Python 3.12.13
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then set your key in `backend/.env`:

| Variable | Required | Default |
| --- | --- | --- |
| `GEMINI_API_KEY` | Yes | none; the app will not start without it |
| `GEMINI_MODEL` | No | `gemini-3.8-flash` |
| `DATABASE_URL` | No | `sqlite:///./customer_pulse.db` (relative to `backend/`) |
| `CORS_ORIGINS` | No | `http://localhost:3000` (comma-separated browser origins) |

`backend/.env` is ignored by Git. Never commit it.

### Create and seed the database

```bash
python -m app.seed
```

This creates any missing tables and loads the CRM facts from `backend/seed/*.csv`. Every row is
validated before anything is written. The command is safe to run again:

- rows that already match are left alone;
- a stored row that differs from the seed stops the load and changes nothing;
- stored assessments are never touched.

### Run the backend

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The app refuses to start if the tables are missing or `GEMINI_API_KEY` is not set. `GET /`
returns `{"status": "ok"}`.

## Frontend setup

Frontend-specific setup, routes and UI notes are in [`frontend/README.md`](frontend/README.md).

```bash
cd frontend
nvm use
npm ci
cp .env.example .env.local   # optional
npm run dev
```

Open <http://localhost:3000>. Use `localhost`, not `127.0.0.1`, unless you add that origin to
`CORS_ORIGINS`.

| Variable | Default |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` |

It is inlined into the browser bundle, so it must never hold a secret.

Production build:

```bash
npm run build
npm run start
```

## Checks

Backend (from `backend/`, with `.venv` active):

```bash
pip check
ruff check .
ruff format --check .
pytest -q
```

Frontend (from `frontend/`, on Node v24.18.0):

```bash
npm test
npm run lint
npx next typegen
npx tsc --noEmit
```

All tests use fakes. None call Gemini or need a key. There is no backend type checker.

## Assessment states

| State | Meaning |
| --- | --- |
| **Action needed** | The history shows a concrete action to consider now, such as an unanswered question or conflicting requests to clarify. |
| **Waiting** | The next step depends on a future event or decision named in the history. Any suggestion applies only after it. |
| **No action needed** | The history positively shows nothing is open now, for example an issue confirmed as resolved. |

**Assessment unavailable** is shown instead of a state when:

- the relationship has no interactions, or only empty notes;
- the model declines because the history is not clear enough;
- a reply fails validation ("Cause not known");
- the provider times out or errors (the detail view offers **Try again**).

Missing or weak evidence never becomes No action needed.

## How assessments are kept trustworthy

- **Facts do not depend on AI.** The list and detail routes read the database only.
- **Opaque handles.** The model sees hashed handles instead of real ids, so ids cannot suggest an
  order. Ids never appear in the text.
- **Notes are data.** Text in a note is never followed as an instruction.
- **Same-date interactions have no order.** They are sent as an unordered group, with no current
  date, and the model is told not to invent a sequence.
- **Strict contract.** The reply is parsed into a Pydantic union that allows exactly the
  fields of each state. Nothing is repaired.
- **Grounding.** Every claim must cite real, non-empty notes of that relationship, and each open
  item's contact must belong to a cited interaction. Any failure rejects the whole reply.
- **Failures are not states.** Timeouts and provider errors return 503; untrusted replies return
  502. Neither is stored or shown as a state.
- **Fingerprinted storage.** Only validated results are stored. The fingerprint covers the model
  input, prompt version, prompt and schema text, provider and model, so any change starts a new
  assessment.

## AI evaluation

The prompt (`assessment-v3`) was measured with the plan in
[`docs/AI_EVALUATION.md`](docs/AI_EVALUATION.md). Results are in
[`docs/AI_EVALUATION_RESULTS.md`](docs/AI_EVALUATION_RESULTS.md).

Formal run: 22 cases (12 seeded, 10 synthetic) × 3 runs = 66 results.

- 0 structured-output failures and 0 grounding failures
- Synthetic cases (declines, prompt injection, same-date order, conflicts): 30 / 30
- Seeded runs passing the per-run rule: 33 / 36

**The strict acceptance gate was not fully met.** Two issues were seen:

- One seeded relationship (pricing sent, no reply) was declined as "not enough evidence" in 2
  of 3 runs instead of Action needed.
- One result stated an order between two same-date interactions that the notes do not support.

`assessment-v3` was frozen at that point, rather than tuned further against the same fixed
cases.

The harness is in `backend/eval/`. It is run only by hand, from `backend/` with `.venv` active
and a key in `.env`, and it makes 66 or more real Gemini calls:

```bash
python -m eval.run_acceptance
```

## Known limitations

- An assessment can be well-formed and cite real notes but still misjudge the state or word
  something too strongly. It is a suggestion; the cited history is the source of truth.
- Evaluation results apply to this model and prompt version only.
- Local MVP: one SQLite file, one process, seeded data only.
- No sign-in, users or multiple workspaces.
- No editing, importing or sending; no reminders or tasks.
- No background jobs. Assessments are generated on request, at most two at a time from the
  browser.

## Repository map

| Path | Contents |
| --- | --- |
| `backend/app/` | FastAPI app, settings, database models, relationship routes, seed command |
| `backend/app/assessment/` | Contract, model input and handles, prompt, Gemini provider, grounding, lifecycle and route |
| `backend/seed/` | Seeded CRM facts as CSV |
| `backend/eval/` | AI evaluation cases, harness and runners |
| `backend/tests/` | Backend tests |
| `frontend/app/` | Next.js routes and layout |
| `frontend/features/relationships/` | API client, assessment request pool, list and detail components, tests |
| `docs/` | PRD, UX spec, technical design, development guide, AI evaluation plan and results |
