# Customer Pulse — agent instructions

Customer Pulse is a real product at MVP stage. Build it as software real users will depend on.

These rules apply to the whole repository. `frontend/AGENTS.md` and `backend/AGENTS.md` add
rules for their own folder. If two rules conflict, stop and ask.

## Repository

- `frontend/` — Next.js web app. Rules and commands: `frontend/AGENTS.md`.
- `backend/` — Python FastAPI service. Rules and commands: `backend/AGENTS.md`.
- There is no root-level tooling. Run commands from inside the folder they belong to.

## Documents

- Approved documents in `docs/` hold the current product and design decisions. Where an
  approved doc deliberately settles something the source material left open, the approved doc
  wins.
- `.context/PRODUCT_CONTEXT.md` holds the source product facts and sample data;
  `.context/ENGINEERING_CONTEXT.md` holds supporting engineering expectations. `.context/` is
  local-only. Keep it untracked and never read it at runtime, in tests or in a build.
- Before product, UX, architecture, AI or backend work, read the approved docs and context
  files the work touches. Before implementation, refactoring or bug-fix work, also read the
  relevant sections of `docs/DEVELOPMENT_GUIDE.md`. It sets the implementation workflow and the
  definition of done.
- Never put hiring, interview, assignment, recruiter or source-document context in product
  code, UI, public docs, commit messages or any user-facing text.

## Default workflow

1. Understand the outcome the user wants and the constraints.
2. Read the relevant code, config, tests and `git status` / `git log` before editing.
3. List ambiguity, risks and which boundaries the change touches. Ask when a decision would
   otherwise be a guess.
4. For non-trivial work, think through the design first: components and boundaries at a high
   level; APIs, data models, control flow and failure handling at a low level. Write a design
   document only when it adds value or is asked for.
5. Make the smallest complete change that fits existing patterns.
6. Add or update meaningful tests for the behaviour you changed.
7. Run the lint, type-check, test and build commands that exist for the folders you touched.
   If a check does not exist, say so. Never claim a check passed unless you ran it. For builds,
   follow the production-build rule in `docs/DEVELOPMENT_GUIDE.md`.
8. Review the final diff for correctness, needless complexity, security and privacy issues,
   regressions and unrelated changes.
9. Report what changed, key decisions and trade-offs, and the checks you ran with their result.
10. Commit and push only as the Git workflow below allows.

## Git workflow

- Run `git status` before you start, so you know which changes already exist.
- Work in small, coherent stages. One commit is one meaningful product, documentation or
  engineering change, not every small edit.
- Before a commit: check `git status`, read the relevant diff, leave unrelated and existing
  changes out, and run the checks for the changed area.
- At the end of a task, give the completion report and wait for approval before you commit or
  push, unless the task asked for the commit or push.
- Once a stage is approved, commit and push it before you start the next stage.
- Use a short conventional prefix where it fits: `docs:`, `feat:`, `fix:`, `refactor:`, `test:`,
  `chore:`. The message says what actually changed, in plain engineering words.
- Commit messages never mention AI tools, hiring, interviews, recruiters, assignments or similar
  process context. Add no tool or co-author attribution unless asked.
- Never commit secrets, `.context/` or other ignored files, generated junk or unrelated changes.
- Never force-push, rewrite history, reset, delete others' work or run any other destructive Git
  command unless the user asks for it.

## Scope and decisions

- Do not invent requirements, business rules, APIs, dependencies, architecture or data
  behaviour. If the repository cannot answer an important question, ask.
- Choose the simplest design that correctly solves the current problem. No speculative
  features. Add a dependency, service, abstraction, pattern or new file only when there is a
  clear need today, and say what the need is.
- Keep frontend, backend, data and AI concerns in separate, clear places. One side uses another
  only through its public contract. If you change a contract between frontend and backend,
  update both sides in the same change. Where a boundary is not decided yet, ask.
- Keep changes small and focused. No drive-by refactors or formatting of untouched code.

## Engineering bar

- Correctness first, then clarity. No clever code. Clear names, small units that each do one
  thing.
- Explicit contracts. Validate data where it crosses a boundary.
- Handle errors on purpose. Never swallow a failure silently.
- Keep secrets and sensitive customer data out of source code, logs, test fixtures and error
  messages.
- Use plain application logic when AI is not needed. When AI is used: ask for structured output,
  validate it, have a clear fallback, keep prompts and behaviour testable, and never show claims
  the input data does not support.
- When concurrency or distributed behaviour matters, think about timeouts, retries, idempotency,
  race conditions, partial failure, consistency and observability before choosing a solution.
- On important production paths, make failures easy to debug with useful logs. Do not add new
  infrastructure for it without a clear need.
- Never hardcode values or fake data to make a test or screen pass. Never weaken, skip or delete
  tests just to get a green check.

## Writing

Use simple English in code comments, docs, explanations, commit messages and user-facing copy.
Use a plain word when one works. Short sentences. Call the product "Customer Pulse".
