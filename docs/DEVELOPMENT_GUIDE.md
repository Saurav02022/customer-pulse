# Customer Pulse — development guide v0.1

Status: **Draft for review.**

How implementation work on Customer Pulse is done. This guide does not change product
behaviour, UX or architecture. It points to the documents that own those decisions instead of
repeating them. "TD §9.3" means section 9.3 of `docs/TECHNICAL_DESIGN.md`. "AE §15" means
section 15 of `docs/AI_EVALUATION.md`.

## 1. Purpose and document hierarchy

This guide is the playbook for building Customer Pulse: how to start a task, what to check,
how to test, when to stop and ask, and when a stage is done.

### Sources of authority

Each source answers a different question. None silently overrides another.

- **Mandatory operating constraints.** The applicable `AGENTS.md` files and other active
  higher-level instructions set how work must be done. A nested `frontend/AGENTS.md` or
  `backend/AGENTS.md` adds rules for its folder on top of the root rules. A task does not
  silently override these constraints.
- **Requested scope.** The current task says what work is wanted. If that work would break a
  repository rule or change an approved product or architecture decision, stop and report the
  conflict (section 20).
- **Intended behaviour.** Approved documents in `docs/` define how the product and system
  should behave: PRD, UX specification, technical design, AI evaluation plan, and other
  approved project docs.
- **Supporting source material.** `.context/` gives source facts where relevant. It is never a
  runtime dependency.
- **Current implementation.** Existing code and tests show what is built today. They may lag
  the approved design. When code and an approved doc disagree, do not silently pick one. If the
  task is explicitly building that approved change, follow the doc. Otherwise, report the
  mismatch.

### What each document owns

| Document | Owns |
| --- | --- |
| `docs/PRD.md` (frozen) | Product behaviour: what Customer Pulse does and does not do |
| `docs/UX_SPEC.md` | Approved user experience: views, states, wording, accessibility |
| `docs/TECHNICAL_DESIGN.md` | Architecture, API, data model, AI contract, technical boundaries, build order (TD §22) |
| `docs/AI_EVALUATION.md` | AI quality expectations, golden cases and the acceptance gate |
| `docs/DEVELOPMENT_GUIDE.md` | How implementation is carried out |
| `docs/UI_RESEARCH.md` | Evidence behind the UX. Not a source of requirements |

If two approved documents seem to conflict, stop and report the conflict. Do not pick one
silently. The same applies to a clash between an approved document and an `AGENTS.md` rule.

## 2. Default development workflow

Every implementation task follows these steps:

1. Read the task and the relevant approved documents.
2. Check `git status` and read the existing code before editing.
3. Write down the expected behaviour and the acceptance criteria that apply (PRD AC-*, UX
   checklist items, TD §17 test list).
4. Name the boundaries the change touches: frontend, backend, data, AI, tests.
5. Check whether the task needs a decision that is not already approved.
6. If a real product or architecture decision is missing, stop and ask.
7. Plan the smallest complete change.
8. Build it in small, coherent steps.
9. Add or update meaningful tests.
10. Run the checks for the changed area (section 12).
11. Read the final diff for unrelated or accidental changes.
12. Give the completion report (section 21).
13. After approval, commit and push the stage before starting the next one.

Do not start another meaningful task while the current stage is unfinished. Build stages
follow TD §22, one reviewed commit per step.

## 3. Before writing code

Answer these first. Short answers are fine.

- What user or system behaviour is changing?
- Which approved requirement supports it? Name the section.
- What is explicitly out of scope? (PRD §7, UX §13, and the task itself.)
- What existing code already solves part of the problem?
- What could fail?
- How will we verify the change?

If no approved requirement supports the change, do not build it. Do not write code because a
feature seems useful, and do not invent requirements, business rules or data behaviour.

## 4. Keep solutions simple

Use the smallest design that correctly solves the approved problem.

- No abstraction before there is a real need. Name the caller that needs it today.
- No infrastructure to look production-ready. TD §12 and §21 list what is deliberately not added.
- Clear code over clever code.
- No generic frameworks "for later".
- No one-use factories, managers, wrappers, repositories or services unless they mark a real
  boundary. `AssessmentProvider` (TD §10) is one: it has two implementations and tests need a fake.
- Extract an abstraction when duplication is real, when tests need a seam, or when there is a
  real integration boundary.

**Trade-off.** Simple code is sometimes rewritten later when needs grow. That rewrite is
usually cheaper than carrying a guessed abstraction that turns out to be wrong. Flexibility is
added where the approved design already expects change (provider, model, prompt version), and
nowhere else.

## 5. Respect system boundaries

The full design is in TD §3–§5. In short:

**Frontend**

- presentation and user interaction;
- the approved loading, empty, error and Assessment unavailable states;
- calling the backend API and narrowing its responses;
- small UI scheduling concerns that are approved: the assessment request pool of 2 (TD §11.2),
  grouping and alphabetical order in the browser (TD §4).

**Backend**

- business rules, including the latest-interaction summary;
- validation of seed data, requests and model output;
- persistence;
- AI orchestration: model input, fingerprint, provider call, contract and grounding checks;
- secrets and provider integration.

**AI**

- interprets interaction notes only within the contract (TD §8);
- never changes product records;
- never carries out actions outside Customer Pulse;
- has no tools and no write path (TD §9.5).

Rules that code can decide stay in code. Do not push a deterministic rule into the model just
because AI is available. Examples that are code, not AI: no interactions → `no_interactions`,
all notes empty → `insufficient_evidence` (TD §9.4), latest-interaction summary, history order,
fingerprint.

## 6. Frontend development practices

Detailed rules and commands are in `frontend/AGENTS.md`. Cross-project rules:

- Build from the approved UX, not personal preference. Draft wording in UX_SPEC is the starting
  copy.
- Keep every approved state: loading, empty, error, not found, "Assessing…" and each
  Assessment unavailable cause (UX §7, §10). A failed load never looks like an empty state.
- Keep client state small. Only the assessment component needs client state (TD §4).
- Do not repeat backend business logic in the browser. Show what the API returns.
- Type every API boundary. Narrow responses with type guards in `frontend/lib/api.ts`.
- Never use `as`, `any` or `@ts-ignore` just to quiet TypeScript.
- Format dates from the `YYYY-MM-DD` string, never through `new Date()` (TD §4).
- Render notes and AI text as plain text.
- Accessibility is part of normal work, not a later pass (UX §12).
- State, status and type are always words. Colour may support meaning, never carry it alone.
- Keep responsive behaviour as UX §11 describes, and check narrow and wide screens.
- Do not make a component generic before a second real use exists.

Visual styling is not decided by the approved documents. Keep it simple and consistent with
`app/globals.css` and Tailwind, and do not treat a styling choice as a product decision.

## 7. Backend development practices

Detailed rules and commands are in `backend/AGENTS.md`. Cross-project rules:

- Keep HTTP concerns in routes and decisions in plain functions (layout in TD §5).
- Validate data where it enters: seed rows, request paths, model replies, stored rows on read.
- Return intentional errors with the status and cause in TD §7. Never swallow a failure.
- Keep routes small: parse, call, shape the response.
- Use one transaction when several writes must succeed together (seed load, TD §6).
- Do not make code async just because FastAPI allows it. Fact routes and seeding are sync
  (TD §12).
- Use async for external network I/O where the design says so: the assessment route and the
  Gemini call.
- Do not block the event loop. Sync database work inside the async route goes through
  `run_in_threadpool` (TD §12).
- Keep provider-specific code in `assessment/gemini.py`, behind `AssessmentProvider`.
- A model result enters trusted state only after it passes the contract and G1–G6. A failed
  result is never stored and never partly shown (TD §9.3, §11.1).

## 8. Data and persistence practices

Follow TD §6: SQLite, sync SQLAlchemy, seed data as CSV in `backend/seed/`, no migration
framework.

- Keep the relational constraints: checks on status and type, the composite foreign key, and
  `PRAGMA foreign_keys=ON` on every connection.
- Do not silently repair bad seed data. A bad row aborts the load and names the file, row and
  field. The old data stays.
- Setup problems must be visible: the backend refuses to start without tables.
- Add no schema field without a product or technical reason in an approved document.
- Prefer ORM or query code when it is clearer. Raw SQL is fine when it is genuinely simpler,
  such as `INSERT … ON CONFLICT DO NOTHING`. Always use bound parameters.
- Keep queries easy to read and test. Load related data on purpose to avoid N+1 queries.
- Do not add migration tooling until an approved document calls for it (TD §6).
- Facts are never written outside the seed command (PRD AC-14).

`.context/` is never a runtime, test or build data source. Seed data lives in `backend/seed/`.

## 9. AI implementation workflow

Build AI work in this order. It matches TD §22 steps 7–13.

1. Confirm the structured contract (TD §8).
2. Build deterministic validation: the Pydantic union and model input.
3. Build `FakeProvider` for tests.
4. Build the grounding checks G1–G6 (TD §9.3).
5. Test failure behaviour: timeout, provider error, malformed reply, bad handle, failed
   grounding.
6. Integrate the real provider (TD §10).
7. Run a small, manual real-provider smoke test.
8. Build and run the evaluation harness when that stage comes (AE §17).
9. Compare behaviour with the evaluation plan before tuning prompts or models (AE §13).

Do not start by changing prompts over and over until outputs look good. A prompt change is
accepted only through the evaluation (AE §13).

Rules:

- Every prompt or schema change bumps `PROMPT_VERSION`. `prompt_sha` is part of the fingerprint.
- The model id comes only from `settings.gemini_model`. No other code names a model.
- Interaction notes are untrusted data. Instructions live only in the system instruction.
- Every AI claim must stay traceable to evidence handles that map to real, non-empty notes.
- Keep these outcomes apart everywhere — in types, status codes, logs and UI:

| Outcome | What it is | Stored? | API |
| --- | --- | --- | --- |
| Valid insufficient-evidence answer | The model declined; a valid result | Yes | 200 `unavailable` / `insufficient_evidence` |
| Malformed or contract-breaking reply | Model output we cannot trust | No | 502 `invalid_output` |
| Failed grounding | Model output we cannot trust | No | 502 `invalid_output` |
| Provider timeout or error | Technical failure | No | 503 `provider_timeout` / `provider_error` |

Never merge these into one "failed" case, and never turn any of them into a business state.

## 10. Dependency policy

Before adding a dependency:

- say what problem it solves;
- check whether the platform or existing code already solves it;
- prefer official, maintained packages (for example `google-genai`, TD §10);
- use official documentation for version-sensitive details;
- add the fewest packages that do the job;
- pin exact versions in `backend/requirements.txt`; commit `frontend/package-lock.json` changes
  only when `package.json` changed (TD §2);
- do not upgrade unrelated dependencies;
- read the package and lockfile diff before committing;
- check licence and security only when the dependency or its use makes that relevant.

Approved tooling and libraries are listed in TD §10 and §17. A new framework, service or major
infrastructure dependency needs explicit approval.

Do not add a package to save a few lines of plain code.

## 11. Testing rules

Tests protect behaviour, not implementation details.

Use the smallest level that fits:

| Level | Use for |
| --- | --- |
| Unit tests | Deterministic logic: seed validation, latest-interaction summary, model input, fingerprint, contract, grounding |
| Backend API and integration tests | Routes through `TestClient`, persistence with a temp SQLite file, lifecycle with `FakeProvider` |
| Frontend behaviour tests | What the owner sees and does: grouping, states, messages, "Based on", request limit |
| Fake AI provider | All automated product tests |
| Real provider calls | Only the manual smoke test and evaluation runs (AE §18) |

The planned test cases are listed in TD §17. Cover the empty, zero, duplicate, not-found and
failure cases, not only the happy path.

For bugs:

1. Reproduce the failure where practical.
2. Add a regression test and watch it fail.
3. Fix the root cause.

Do not:

- delete or weaken a test to get a green suite;
- mock so much that the test no longer checks real behaviour;
- make real paid AI calls in `pytest`, frontend tests or CI.

Keep fixtures small, readable and intentional. Use seeded or clearly synthetic data. Evaluation
fixtures stay out of `backend/seed/` (AE §8).

## 12. Verification matrix

Run what fits the change. Do not run unrelated commands to fill a list. Commands and their
current availability are in the folder `AGENTS.md` files.

| Changed area | Normally run |
| --- | --- |
| Documentation only | Read against the approved docs for consistency; `git diff` |
| Frontend | Tests (once Vitest is set up); `npm run lint`; `npx next typegen && npx tsc --noEmit`; `npm run build` (see "Production build" below) |
| Backend | `ruff check` and `ruff format --check` (once Ruff is set up); `pytest`; an import or startup check where useful |
| AI contract or provider | Backend tests, including fake-provider, contract and grounding tests; a real-provider smoke test only when explicitly approved |
| Cross-stack feature | Backend checks, frontend checks, and the relevant manual flow checks against the UX checklist |
| Dependencies | The checks for the affected folder, plus a read of the lockfile or requirements diff |

Until TD §22 step 2 lands, Ruff and Vitest are not installed. Say so instead of claiming those
checks ran.

**Production build.** Run `npm run build` for frontend changes only when the active
instructions and the task allow it. A task or owner request does not lift a higher-level
restriction. If the agent doing the work may not run builds, it does not run one. It reports
that the build was not run and gives the owner the exact command:
`cd frontend && npm run build`. A successful build the owner runs by hand counts as
verification for the stage. Documentation-only changes need no build.

If a needed check cannot run, report exactly which one and why.

## 13. Error handling

- Every failure has an intended owner and boundary. TD §13 maps each one to its UX.
- Catch broad exceptions only to re-raise or map them on purpose.
- Keep useful diagnostic context. Never include secrets.
- Keep user, data, model and provider failures apart.
- Never turn a technical failure into a business state.
- Error messages are clear and safe. No stack traces, SQL, paths or secrets in responses.
- Retry only failures that can be retried: timeout, 429, 5xx, connection error.
- Every retry has a fixed limit. The Gemini call retries once (TD §10).

## 14. Logging and debugging

Log enough to understand important failures. Use the standard `logging` module, one line per
event (TD §15).

Log:

- operation ids, such as `attempt_id` and `customer_id`;
- provider, model and prompt version;
- timing;
- a safe failure category and validation result (for example `G1 open_items[0].evidence[1]`).

Do not log:

- API keys or other secrets;
- prompts, raw replies or note text;
- names, emails or full interaction histories when an id is enough.

A log line should help answer: what failed, where, for which operation, why, and how long it
took. To inspect a bad reply, use a local script that prints to the terminal only (TD §15).

## 15. Security and configuration

- Secrets live in environment settings, never in source code.
- The Gemini key stays in the backend. It never reaches the browser or a `NEXT_PUBLIC_*` value.
- `.env` files stay gitignored.
- When configuration is introduced, commit `.env.example` with names or placeholder values only.
- Required settings are checked at startup, with a clear message (TD §14).
- The MVP is local and private. FastAPI binds to `127.0.0.1`. Do not assume or prepare a public
  deployment (TD §16, §20).
- All note content sent to the model is untrusted.
- Send the model only the fields in TD §9.2.

## 16. Code quality

Use:

- clear names;
- functions and components that each do one thing;
- early validation;
- explicit types where they help the reader;
- comments only where the reason is not clear from the code.

Avoid:

- comments that repeat the code;
- large functions doing unrelated work;
- boolean arguments whose meaning is unclear at the call site;
- hidden side effects;
- duplicated business rules;
- magic strings or numbers for a real shared concept (state names, causes, limits);
- optimising before it is needed.

Write comments and docs in simple English. Leave no tool or generation notes in code comments.

## 17. Refactoring policy

Refactor when:

- the current behaviour cannot be built safely without it;
- duplication has become real;
- tests show an awkward boundary;
- the existing design makes the requested change risky.

Do not clean up unrelated code during a feature stage. If you find unrelated technical debt,
report it and leave it for a separate stage, unless it blocks correctness. This keeps each
commit reviewable.

## 18. Performance and concurrency

Do not optimise without evidence. For this MVP, correctness and clarity come first.

- Avoid obvious N+1 queries and repeated expensive work.
- AI work follows the bounded design: one relationship per request, at most 2 requests at a time
  from the browser (TD §11.2).
- Every external call has a timeout (TD §12).
- Concurrency must not create duplicate trusted state or results that depend on timing. Storage
  uses `ON CONFLICT DO NOTHING`, then re-reads (TD §11.1).
- No shared mutable state between backend requests.

Do not add caching layers, queues, workers or distributed coordination unless an approved need
appears.

## 19. Definition of done

A stage is done only when all of these hold:

- the requested behaviour is complete;
- approved requirements and UX are kept;
- relevant tests are added or updated, and they pass;
- lint, type and format checks for the changed area pass, or the report says why they could not
  run;
- relevant manual checks are done where needed;
- no known critical failure is hidden;
- no unrelated changes are included;
- no secrets are present;
- comments and docs are updated only where needed;
- the final diff has been read;
- the completion report is given;
- the approved stage is committed and pushed.

Code that compiles is not done.

## 20. Stop-and-ask conditions

Stop and ask, instead of guessing, when the work would:

- change frozen PRD behaviour;
- change approved UX behaviour;
- change a major technical-design decision;
- add a major dependency, framework or infrastructure service;
- change the database or domain schema for a reason not already approved;
- expose the application publicly;
- change authentication or security assumptions;
- weaken AI grounding or evaluation requirements;
- need a destructive Git operation;
- work around a failing test instead of understanding it;
- choose between product behaviours that differ in a real way.

Do not escalate small details that the approved documents already bound: a private helper name,
a file split inside the TD §5 layout, test structure, the exact layout breakpoint (UX §11), or
styling within the UX rules. Decide them and explain the choice in the completion report.

## 21. Completion report

Every task ends with a report of what actually happened, not what was intended:

- what changed;
- why;
- important decisions and trade-offs;
- files changed;
- checks and tests run, with their exact results;
- checks not run, and why;
- known limits and follow-up items;
- `git status`;
- commit and push details, when done.
