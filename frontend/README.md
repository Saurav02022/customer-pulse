# Customer Pulse Frontend

Next.js web app for Customer Pulse. It shows the relationship list and detail views, and requests
grounded assessments from the backend. The whole-project overview is in the
[root README](../README.md).

## Stack

- Next.js 16 (App Router)
- React 19
- TypeScript (strict)
- Vitest and React Testing Library

## Requirements

- Node **v24.18.0** (`.nvmrc`)
- npm **11.16.0** (`packageManager`)

## Setup

```bash
cd frontend
nvm use
npm ci
cp .env.example .env.local   # optional
```

## Environment

| Variable | Default |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` |

It points the browser at the backend. It is inlined into the browser bundle, so it must never hold
a secret.

## Run locally

```bash
npm run dev
```

Open <http://localhost:3000>. Use `localhost`, not `127.0.0.1`, unless you add that origin to the
backend's `CORS_ORIGINS`.

## Production commands

```bash
npm run build
npm run start
```

## Routes

| Route | View |
| --- | --- |
| `/` | The relationship list, grouped by state. |
| `/relationships/[id]` | One relationship's contacts, interaction history and assessment. |

## Frontend structure

The relationship UI — API client, assessment request scheduler, list and detail components — lives
under `features/relationships/`.

## Assessment UI behavior

- CRM facts load independently and are shown whether or not the assessment works.
- Assessment requests go through the shared client scheduler, with at most two active at a time.
- Rows can regroup as assessment results arrive.
- A temporary failure can be retried from the detail view.
- An unavailable result is not a business state.
- There is no polling.

## Tests

```bash
npm test
npm run lint
npx next typegen
npx tsc --noEmit
```

Run `npx next typegen` before `tsc` so the generated route types exist. The frontend tests do not
require real Gemini access.

## Repository guidance

- [`AGENTS.md`](AGENTS.md) — rules for working in `frontend/`.
- [`CLAUDE.md`](CLAUDE.md) — same rules, loaded by Claude Code.
- [`../README.md`](../README.md) — whole-project overview.
