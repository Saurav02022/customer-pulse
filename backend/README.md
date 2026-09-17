# Customer Pulse Backend

FastAPI service for Customer Pulse. It serves the CRM facts from a SQLite database and generates
grounded relationship assessments through Google Gemini. The whole-project overview is in the
[root README](../README.md).

## Stack

- Python 3.12
- FastAPI, Starlette, Uvicorn
- Pydantic 2 and pydantic-settings
- SQLAlchemy 2 on SQLite
- Google Gemini through `google-genai`, with structured JSON output
- pytest and Ruff

## Requirements

- Python **3.12.13** (`.python-version`)
- A Google Gemini API key for assessments

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Environment variables

Set these in `backend/.env`. Do not use a real key in a committed file; `backend/.env` is ignored
by Git.

| Variable | Required | Default |
| --- | --- | --- |
| `GEMINI_API_KEY` | Yes | none; the provider refuses to start without it |
| `GEMINI_MODEL` | No | `gemini-3.8-flash` |
| `DATABASE_URL` | No | `sqlite:///./customer_pulse.db` (relative to `backend/`) |
| `CORS_ORIGINS` | No | `http://localhost:3000` (comma-separated browser origins) |

## Initialize the database

```bash
python -m app.seed
```

This creates any missing tables and loads the CRM facts from `backend/seed/*.csv`. Every row is
validated before anything is written. The command is safe to run again: a row that already matches
the seed is left alone, a stored row that differs aborts the load without changing anything, and
stored assessments are never touched.

## Run the backend

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The app refuses to start if the tables are missing or `GEMINI_API_KEY` is not set.

## API

| Route | Description |
| --- | --- |
| `GET /` | Health check; returns `{"status": "ok"}`. |
| `GET /api/relationships` | All relationships with their facts and any stored assessment outcome. No AI call. |
| `GET /api/relationships/{id}` | One relationship with its contacts and full interaction history. No AI call. |
| `GET /api/relationships/{id}/assessment` | The assessment for one relationship, generated or served from storage. |

## AI assessment flow

CRM facts → model input (opaque handles, notes as data) → Gemini → strict structured contract →
grounding checks against the real notes → stored under a fingerprint of the inputs → returned.

The factual routes (`GET /` and the two relationship reads) never depend on Gemini. Only the
assessment route calls the model, and only when the result is not already decided in code or stored.

## Evaluation

- The reusable evaluation code lives in [`eval/`](eval/).
- The evaluation plan is in [`../docs/AI_EVALUATION.md`](../docs/AI_EVALUATION.md).
- The evaluation results are in [`../docs/AI_EVALUATION_RESULTS.md`](../docs/AI_EVALUATION_RESULTS.md).

The evaluation runners make real Gemini calls and are run only by hand.

## Tests

```bash
pip check
ruff check .
ruff format --check .
pytest -q
```

The normal automated tests use fakes. None of them call real Gemini or need a key.

## Repository guidance

- [`AGENTS.md`](AGENTS.md) — rules for working in `backend/`.
- [`CLAUDE.md`](CLAUDE.md) — same rules, loaded by Claude Code.
