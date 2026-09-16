# Backend — agent instructions

Rules for `backend/`. The root `AGENTS.md` still applies.

## Stack

Python FastAPI service, with Pydantic v2 and Uvicorn. The app lives in `app/main.py`.
`pydantic-settings`, SQLAlchemy 2, httpx and pytest are installed but not used in code yet.
`requirements.txt` holds exact pinned versions. The local virtualenv at `backend/.venv` uses
Python 3.12 and is not committed. The development runtime is pinned to Python 3.12 by the root
`.python-version`, which is the source of truth.

## Commands (run in `backend/` with `.venv` active)

- Install: `pip install -r requirements.txt`
- Tests: `pytest` (no tests exist yet)
- Lint and format: Ruff is the approved tool, but it is not installed or configured yet. Until
  the tooling stage adds it, Ruff checks cannot be required to pass; say they did not run. Once
  it is installed, run `ruff check` and `ruff format --check` like any other check.
- No type-checker is set up. Say so instead of claiming this check passed.
- When you add a dependency, add it to `requirements.txt` with an exact version.

## API contracts

- Every endpoint uses Pydantic models for its request body and its response (`response_model` or
  a typed return). Validate input at the edge and reject bad input with a clear message.
- Use correct status codes: 201 for create, 204 for no content, 400/422 for bad input,
  401/403 for auth, 404 for missing, 409 for conflict. Never return 200 with an error inside.
- Raise `HTTPException` or use a registered exception handler for expected errors. Responses must
  never expose stack traces, SQL, internal paths or secrets.
- Do not change an existing response shape without asking. `GET /` returns `{"status": "ok"}` as
  a cheap health check.

## Structure

- Route functions handle HTTP only: parse the request, call logic, shape the response.
- When logic grows past simple glue, move business rules into plain functions that are testable
  without HTTP. Keep database and external-service code out of route functions.

## Async

- An `async def` route must not call blocking code: sync database drivers, sync HTTP clients,
  `time.sleep` or heavy CPU work. Use a plain `def` route or an async client instead.
- Set an explicit timeout on every outbound call.
- Do not keep mutable global state that is shared between requests.

## Configuration and secrets

- Read settings from environment variables through one `pydantic-settings` class. `.env` files
  are gitignored; never commit them.
- Fail at startup with a clear message when a required setting is missing.

## Persistence

- The approved MVP persistence is SQLite with SQLAlchemy (`docs/TECHNICAL_DESIGN.md`). No
  migration framework is used for the MVP. Changing the persistence design needs an approved
  technical-design change first.
- One session per request through a dependency, always closed. Multi-step writes
  go in one transaction that commits or rolls back as a whole.
- Use bound parameters, never SQL built from strings. Load related data on purpose to avoid N+1
  queries, and add indexes for the queries you actually run.

## External services and AI

- Put each external service, including any AI model, behind a small typed function or module.
  Tests replace it with a fake. Tests never call real services or need real keys.
- Validate AI output against a Pydantic model before using it. If validation fails, return a
  clear fallback or error, never partial or guessed data.
- Retry only calls that are safe to repeat, with a small limit.

## Tests

- Test endpoints through FastAPI's `TestClient`. Test business logic directly.
- Cover bad input, not found, empty results, duplicates, denied access and integration failures,
  not only the happy path.
- Put tests in `backend/tests/` unless a test layout already exists.

## Logging and observability

- Use the standard `logging` module, not `print`.
- Log at boundaries: unexpected errors with request context, and outbound calls with target,
  duration and result.
