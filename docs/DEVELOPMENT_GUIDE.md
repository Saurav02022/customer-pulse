# Customer Pulse — development guide v0.1

Status: **Draft for review.**

How implementation work on Customer Pulse is done: what to read first, where the boundaries
are, what to test, which checks to run, when to stop and ask, and when a stage is done. It does
not change product behaviour, UX or architecture; it points to the documents that own them.
"TD → Assessment lifecycle" points to that section of `docs/TECHNICAL_DESIGN.md` by heading;
"AE →" does the same for `docs/AI_EVALUATION.md`.

## 1. Sources of authority

Each source answers a different question. None silently overrides another.

- **Operating constraints.** The applicable `AGENTS.md` files and any active higher-level
  instructions. A nested `frontend/AGENTS.md` or `backend/AGENTS.md` adds rules for its folder
  on top of the root rules. A task never overrides these.
- **Requested scope.** The current task says what work is wanted. If that work would break a
  repository rule or change an approved decision, stop and report the conflict (section 12).
- **Intended behaviour.** The approved documents in `docs/`.
- **Supporting source material.** `.context/` gives source facts. It is never a runtime, test
  or build dependency.
- **Current implementation.** Code and tests show what is built today and may lag the approved
  design. When they disagree with an approved document, do not silently pick one: if the task
  is building that approved change, follow the document; otherwise report the mismatch.

| Document | Owns |
| --- | --- |
| `docs/PRD.md` (frozen) | Product behaviour: what Customer Pulse does and does not do |
| `docs/UX_SPEC.md` | User experience: views, states, wording, accessibility |
| `docs/TECHNICAL_DESIGN.md` | Architecture, API, data model, AI contract, failure handling, build order |
| `docs/AI_EVALUATION.md` | AI quality: golden cases, hard checks, rubric, acceptance gate, regressions |
| `docs/DEVELOPMENT_GUIDE.md` | How implementation is carried out |
| `docs/UI_RESEARCH.md` | Evidence behind the UX. Not a source of requirements |

If two approved documents seem to conflict, or an approved document clashes with an `AGENTS.md`
rule, stop and report it.

## 2. Before writing code

1. Read the task and the approved documents it touches. Check `git status` and read the
   existing code.
2. Write down, briefly: what behaviour changes; which approved requirement supports it (PRD
   AC-*, a UX checklist item, a TD test); what is out of scope; what existing code already
   solves part of it; what could fail; how the change will be verified.
3. Name the boundaries the change touches: frontend, backend, data, AI, tests.
4. If the task needs a product or architecture decision that is not already approved, stop and
   ask (section 12).

If no approved requirement supports the change, do not build it. Build stages follow the
implementation sequence in the technical design, one reviewed commit per step, and a stage is
finished (section 11) before the next one starts.

## 3. Boundaries

The full design is in the technical design. In short:

- **Frontend** presents and interacts: the approved loading, empty, error and Assessment
  unavailable states; calling the API and narrowing its responses; and two approved scheduling
  concerns, the assessment request pool of 2 and grouping with alphabetical order in the
  browser.
- **Backend** decides: business rules including the latest-interaction summary; validation of
  seed data, requests and model output; persistence; AI orchestration (model input,
  fingerprint, provider call, contract and grounding checks); secrets and provider integration.
- **AI** interprets interaction notes only within the contract. It never changes records, never
  acts outside Customer Pulse, and has no tools and no write path.

Rules that code can decide stay in code. Do not push a deterministic rule into the model
because AI is available. Code, not AI: no interactions → `no_interactions`; all notes empty →
`insufficient_evidence`; the latest-interaction summary; history order; the fingerprint.

## 4. Practices that cross folders

Folder rules and commands are in `frontend/AGENTS.md` and `backend/AGENTS.md`. On top of them:

**Frontend**

- Build from the approved UX. Draft wording in the UX spec is the starting copy. Visual styling
  is not decided by any approved document: keep it simple and consistent with `app/globals.css`
  and Tailwind, and do not treat a styling choice as a product decision.
- Keep every approved state, including "Assessing…" and each Assessment unavailable cause. A
  failed load never looks like an empty state.
- Keep client state minimal. Use it for assessment scheduling and status where the design
  approves it, and for UI interaction state the approved UX requires, such as focus and scroll
  restoration on back. Never move backend business state or business rules into frontend
  state. Show what the API returns.
- Narrow API responses with type guards in `frontend/lib/api.ts`. Never `as`, `any` or
  `@ts-ignore` to quiet TypeScript.
- Format dates from the `YYYY-MM-DD` string, never through `new Date()`. Render notes and AI
  text as plain text.
- State, status and type are always words; colour may support meaning, never carry it alone.
  Accessibility is part of the work, not a later pass.

**Backend**

- HTTP concerns in routes, decisions in plain functions, in the layout the technical design
  gives.
- Validate where data enters: seed rows, request paths, model replies, stored rows on read.
- Return the status and cause the API section defines. Never swallow a failure.
- Fact routes and seeding are sync. The assessment route and the Gemini call are async, and
  sync database work inside that route goes through `run_in_threadpool`. Do not make code async
  because FastAPI allows it.
- Provider-specific code lives in `assessment/gemini.py`, behind `AssessmentProvider`.
- A model result is trusted only after it passes the contract and G1–G6. A failed result is
  never stored and never partly shown.

**Data**

- SQLite, sync SQLAlchemy, seed CSV in `backend/seed/`, no migration framework. Keep the
  constraints: status and type checks, the composite foreign key, `PRAGMA foreign_keys=ON`.
- Never repair bad seed data silently. A bad row aborts the load, names the file, row and
  field, and leaves the old data.
- No schema field without a reason in an approved document. Facts are never written outside
  the seed command (PRD AC-14).
- ORM or query code when clearer; raw SQL when genuinely simpler, such as
  `INSERT … ON CONFLICT DO NOTHING`. Always bound parameters. Load related data on purpose.

## 5. AI work

Build in this order, which matches implementation steps 7 to 13:

1. The structured contract (the Pydantic union) and the model input.
2. `FakeProvider` for tests.
3. Grounding checks G1–G6.
4. Failure behaviour: timeout, provider error, malformed reply, bad handle, failed grounding.
5. The real provider, then a small manual smoke test.
6. The evaluation harness, and comparison against the evaluation plan before tuning prompts or
   models.

Do not iterate on prompts until outputs look good. A prompt change is accepted only through the
evaluation (AE → Prompt versions and regressions). Every prompt or schema change bumps
`PROMPT_VERSION`; `prompt_sha` in the fingerprint is the safety net. The model id comes only
from `settings.gemini_model`. Interaction notes are untrusted data; instructions live only in
the system instruction.

Keep these outcomes apart everywhere, in types, status codes, logs and UI, and never turn any of
them into a business state:

- a valid insufficient-evidence answer: the model declined; stored; Assessment unavailable;
- a malformed or contract-breaking reply, or failed grounding: output we cannot trust; not
  stored; `invalid_output`;
- a provider timeout or error: technical failure; not stored; `provider_timeout` or
  `provider_error`.

## 6. Dependencies

Before adding one: say what problem it solves and why the platform or existing code does not;
prefer the official, maintained package; use official documentation for version-sensitive
details; pin exact versions in `backend/requirements.txt`; commit `frontend/package-lock.json`
changes only when `package.json` changed; do not upgrade unrelated packages; read the lockfile
or requirements diff before committing. A new framework, service or infrastructure dependency
needs explicit approval. Do not add a package to save a few lines of plain code.

## 7. Tests

Tests protect behaviour, not implementation details. Use the smallest level that fits:

| Level | Use for |
| --- | --- |
| Unit tests | Deterministic logic: seed validation, latest-interaction summary, model input, fingerprint, contract, grounding |
| Backend API and integration tests | Routes through `TestClient`, persistence with a temp SQLite file, lifecycle with `FakeProvider` |
| Frontend behaviour tests | What the owner sees and does: grouping, states, messages, "Based on", request limit |
| Fake AI provider | All automated product tests |
| Real provider calls | Only the manual smoke test and evaluation runs (AE → When evaluations run) |

The planned cases are listed in TD → Testing and tooling. Cover empty, zero, duplicate,
not-found and failure cases, not only the happy path. For a bug: reproduce it, add a regression
test and watch it fail, then fix the root cause. Keep fixtures small and clearly seeded or
synthetic; evaluation fixtures stay out of `backend/seed/`.

## 8. Verification matrix

Run what fits the change. Do not run unrelated commands to fill a list. Commands and their
current availability are in the folder `AGENTS.md` files; until implementation step 2 lands,
Ruff and Vitest are not installed, so say so instead of claiming those checks ran.

| Changed area | Normally run |
| --- | --- |
| Documentation only | Read against the approved docs for consistency; `git diff` |
| Frontend | Tests (once Vitest is set up); `npm run lint`; `npx next typegen && npx tsc --noEmit`; `npm run build` (see "Production build") |
| Backend | `ruff check` and `ruff format --check` (once Ruff is set up); `pytest`; an import or startup check where useful |
| AI contract or provider | Backend tests, including fake-provider, contract and grounding tests; a real-provider smoke test only when explicitly approved |
| Cross-stack feature | Backend checks, frontend checks, and the relevant manual flow checks against the UX checklist |
| Dependencies | The checks for the affected folder, plus a read of the lockfile or requirements diff |

**Production build.** Run `npm run build` for frontend changes only when the active
instructions and the task allow it. A task or owner request does not lift a higher-level
restriction: if the agent doing the work may not run builds, it does not run one. It reports
that the build was not run and gives the owner the exact command, `cd frontend && npm run
build`. A successful build the owner runs by hand counts as verification for the stage.
Documentation-only changes need no build.

If a needed check cannot run, report exactly which one and why.

## 9. Failures, logs and secrets

- Every failure has an owner and a boundary (TD → Failure handling). Keep
  user, data, model and provider failures apart, and never turn a technical failure into a
  business state.
- Catch broad exceptions only to re-raise or map them on purpose. Responses never contain stack
  traces, SQL, paths or secrets.
- Retry only what can be retried (timeout, 429, 5xx, connection error), with a fixed limit.
- Log one line per event with the fields in TD → Logging: operation ids, provider, model,
  prompt version, timing, and a safe failure category. Never keys, prompts, raw replies, note
  text, names or emails. Inspect a bad reply with a local script that prints to the terminal
  only.
- Secrets live in environment settings. The Gemini key stays in the backend and never reaches a
  `NEXT_PUBLIC_*` value. `.env` stays gitignored; `.env.example` lists names or placeholders
  only. Required settings are checked at startup.
- The MVP is local and private. FastAPI binds to `127.0.0.1`. Do not prepare a public
  deployment.

## 10. Keep it small

Use the smallest design that correctly solves the approved problem. No abstraction before a
caller needs it today; `AssessmentProvider` earns its place because it has two implementations
and tests need a fake. No infrastructure to look production-ready: the technical design lists
what is deliberately not added. Simple code is sometimes rewritten when needs grow; that
rewrite is usually cheaper than carrying a guessed abstraction. Flexibility goes only where the
design already expects change: provider, model, prompt version.

Refactor when the change cannot be built safely without it, duplication has become real, or
tests show an awkward boundary. Do not clean up unrelated code during a feature stage; report
it for a separate stage unless it blocks correctness. Do not optimise without evidence, and do
not add caching layers, queues or workers without an approved need. Concurrency must not create
duplicate trusted state: storage uses `ON CONFLICT DO NOTHING`, then re-reads.

Clear names, one job per function or component, early validation, comments only where the
reason is not clear from the code, no magic strings for shared concepts (state names, causes,
limits). Simple English in comments and docs, and no tool or generation notes in code.

## 11. Definition of done

A stage is done only when:

- the requested behaviour is complete and the approved requirements and UX are kept;
- relevant tests are added or updated and pass;
- lint, type and format checks for the changed area pass, or the report says why they could
  not run;
- relevant manual checks are done where needed;
- no known failure is hidden, no unrelated changes are included, and no secrets are present;
- comments and docs are updated only where needed;
- the final diff has been read;
- the completion report (section 13) is given;
- the approved stage is committed and pushed.

Code that compiles is not done.

## 12. Stop and ask

Stop and ask, instead of guessing, when the work would:

- change frozen PRD behaviour, approved UX behaviour, or a major technical-design decision;
- add a major dependency, framework or infrastructure service;
- change the database or domain schema for a reason not already approved;
- expose the application publicly, or change authentication or security assumptions;
- weaken AI grounding or evaluation requirements;
- need a destructive Git operation;
- work around a failing test instead of understanding it;
- choose between product behaviours that differ in a real way.

Do not escalate details the approved documents already bound: a private helper name, a file
split inside the backend layout, test structure, the exact layout breakpoint, or styling within
the UX rules. Decide them and explain the choice in the completion report.

## 13. Completion report

Every task ends with a report of what actually happened, not what was intended: what changed
and why; important decisions and trade-offs; files changed; checks and tests run, with their
exact results; checks not run, and why; known limits and follow-up items; `git status`; and
commit and push details, when done.
