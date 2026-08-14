---
name: eigi-frontend-standards
description: Shared Eigi frontend engineering standards for creating, modifying, reviewing, or testing frontend web apps in any Eigi repo. Use for React, Next.js, Vite, Vue, Svelte, or similar client apps that need consistent folder structure, component boundaries, API clients, styling, state, environment handling, gitignore hygiene, and frontend tests.
---

# Eigi Frontend Standards

Use this skill to build frontend web apps that follow Eigi conventions. Inspect the target repo first and follow its framework, package manager, design system, and naming patterns. If no stronger local convention exists, use the standards below.

For detailed folder and file responsibilities, read [references/folder-structure.md](references/folder-structure.md) before creating a new frontend structure or moving files between layers.

## Core Flow

Prefer this layering for frontend work:

```text
route/page -> feature component -> shared UI/hooks -> API client -> backend API
```

- Build the requested web app experience directly; do not create a marketing landing page unless the requirement asks for one.
- Keep route/page files focused on layout, data boundaries, metadata, and route params.
- Put workflow-specific UI in feature modules.
- Put reusable primitives in shared components.
- Put backend calls in typed API client modules, not scattered through UI components.
- Put reusable state, effects, and browser behavior in hooks/stores.

## Component Standards

- Use small typed components with explicit props and predictable names.
- Add loading, empty, error, disabled, and success states for user-facing workflows.
- Keep shared UI components domain-neutral; keep business rules inside feature modules.
- Do not hardcode secrets, API keys, or environment-specific URLs in components.
- Use accessible labels, semantic HTML, keyboard-safe controls, and visible focus states.
- Keep text responsive and prevent overlap on mobile and desktop.

## API and Environment Rules

- Centralize HTTP calls in `lib/api`, `services`, or the repo's equivalent API layer.
- Read base URLs and public client config from environment variables.
- Use only frontend-safe public env prefixes required by the framework, such as `NEXT_PUBLIC_` or `VITE_`.
- Never expose server-only secrets in frontend code, bundled assets, logs, or examples.
- Normalize API errors into UI-safe messages; do not render raw exception strings to users.

## Styling and UX

- Follow the existing design system, tokens, CSS framework, or component library.
- Prefer consistent spacing, typography, color tokens, and component variants over one-off styles.
- Use icons for common actions when the existing stack has an icon library.
- Make common workflows fast to scan and operate; avoid decorative layouts for operational tools.
- Verify responsive behavior for mobile and desktop when changing layout.

## Repository Hygiene

When creating a frontend structure, add or update `.gitignore` even if the repo is not Git-initialized yet. It must exclude `.git`, environment files, dependency folders, build outputs, caches, logs, coverage, local tool output, and editor/OS noise. See [references/folder-structure.md](references/folder-structure.md) for the compact frontend template.

## Testing

Add focused tests for the behavior you changed:

- Component rendering and state transitions.
- Form validation and disabled/loading behavior.
- API success, empty, error, and unauthorized states with mocked clients.
- Routing and permission gates when applicable.
- Critical user flows with the repo's E2E tool when the change affects navigation or checkout-style workflows.

Run the repo's existing lint, typecheck, unit, and E2E commands when available, or explain why they could not be run.

## Finish Checklist

- Inspect nearby frontend files and follow local framework/package-manager conventions.
- Read [references/folder-structure.md](references/folder-structure.md) before adding frontend files.
- Keep route/page files thin and feature components responsible for workflows.
- Put backend calls in a central API/client layer.
- Add loading, empty, error, and permission states where user-facing.
- Add or update `.gitignore` for `.git`, env files, `node_modules`, build outputs, caches, logs, and generated artifacts.
- Add focused tests and run lint/typecheck/tests, or explain what could not be run.
