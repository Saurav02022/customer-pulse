<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Frontend — agent instructions

Rules for `frontend/`. The root `AGENTS.md` still applies. The block above is managed by Next.js;
leave it as it is and add rules below it.

## Stack

Next.js 16 (App Router, `app/` folder), React 19, TypeScript in strict mode, Tailwind CSS 4,
ESLint 9. npm is the package manager (`package-lock.json`); Node 24 is pinned by the root
`.nvmrc` and `engines`. Import alias: `@/*` points to `frontend/*`.

## Commands (run in `frontend/`)

- Install: `npm ci`. Commit a `package-lock.json` change only when `package.json` changed.
- Lint: `npm run lint`
- Type-check: `npx next typegen && npx tsc --noEmit`. Plain `tsc` fails on a fresh checkout,
  because Next.js generates route types such as `LayoutProps`.
- Build: `npm run build`, only as the production-build rule in `docs/DEVELOPMENT_GUIDE.md`
  allows.
- Tests: `npm test`. Vitest and React Testing Library are installed and configured. Do not add
  any other frontend test runner or framework without approval.

## Components, data and state

- Server Components by default. Add `"use client"` only where you need state, effects, event
  handlers or browser APIs, and keep that client part as small as possible.
- One clear job per component. Split when data loading, interaction and layout start changing
  for different reasons. No shared folders or component libraries before a second real use
  needs them.
- Keep API calls out of presentational components. Load data in server components, route
  handlers or a small data-access module, and pass typed props down.
- Type every API response and narrow data from the network with type guards, not `as`.
- Prefer server data, URL state and local component state. No global state library without a
  clear need.
- Read the backend URL and other settings from environment variables. Only `NEXT_PUBLIC_*`
  values reach the browser, so never put secrets in them.

## UI

- Semantic HTML: real `button`, `a`, `form`, `label`, `table` and list elements, headings in
  order.
- Everything works with a keyboard. Keep focus visible, label every input, give meaningful
  images `alt` text, keep text contrast readable, and never use colour as the only signal.
- Mobile-first with Tailwind; check narrow and wide screens. Reuse `app/globals.css` and
  Tailwind before writing new CSS.
- Where data loads or an action runs, handle the loading, empty, error and success states.
  Error messages say what happened and what the user can do next.
- Before adding a package, check whether HTML, CSS, React or Next.js already covers it.

## Tests

- When the test runner exists, test what users see and do: rendered content, interactions and
  the loading, empty and error states. Do not test internal implementation details.
