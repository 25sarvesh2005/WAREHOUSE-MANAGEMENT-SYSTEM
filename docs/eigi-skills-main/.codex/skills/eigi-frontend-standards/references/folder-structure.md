# Eigi Frontend Folder Structure

Use this reference when creating frontend app structure or deciding where UI code belongs. Follow the target repo first; use these conventions when the repo has no stronger pattern.

## Top-Level Frontend Files

- `.gitignore`: Required for every frontend structure, even before GitHub/Git initialization. Keep `.git`, secrets, dependencies, caches, build output, coverage, logs, and local tool files out of source control.
- `package.json`: Scripts, dependencies, package manager metadata, and project entry points. Keep lockfiles committed unless the repo explicitly does otherwise.
- `README.md`: Only create or edit when the repo already expects frontend setup docs or the user asks for it.
- Framework config: `next.config.*`, `vite.config.*`, `nuxt.config.*`, `svelte.config.*`, `astro.config.*`, or equivalent.
- Type/lint/test config: `tsconfig.json`, `eslint.config.*`, `.prettierrc`, `vitest.config.*`, `playwright.config.*`, or local equivalents.
- Env examples: `.env.example` documents required public frontend env vars. Never commit real `.env` values.

Use this compact frontend `.gitignore` baseline and extend it only for repo-specific generated files:

```gitignore
.git/
.env
.env.*
!.env.example
node_modules/
dist/
build/
.next/
out/
.nuxt/
.svelte-kit/
.vite/
.turbo/
.cache/
coverage/
playwright-report/
test-results/
storybook-static/
*.log
npm-debug.log*
yarn-debug.log*
pnpm-debug.log*
.DS_Store
.idea/
.vscode/
.vercel/
.netlify/
```

## `src/app`, `src/pages`, or `src/routes`

Use the framework's route directory for route declarations only.

Responsibilities:

- Define route-level layouts, pages, metadata, loaders, and route params.
- Wire feature components into the route.
- Keep route-level auth or permission redirects aligned with nearby code.
- Avoid embedding large workflow logic directly in page files.

## `src/features/`

Use feature folders for domain workflows such as onboarding, dashboard, settings, billing, chat, agents, inventory, or orders.

Responsibilities:

- Own feature-specific screens, panels, forms, tables, state, and orchestration.
- Call shared API clients or hooks; do not duplicate HTTP logic.
- Keep domain validation, permission checks, and workflow state close to the feature.
- Export a small public surface from each feature when other areas need it.

Suggested shape:

```text
src/features/resource/
  components/
  hooks/
  api.ts
  types.ts
  utils.ts
```

## `src/components/`

Use shared components for reusable UI.

Responsibilities:

- Keep primitives and reusable composition pieces domain-neutral.
- Accept explicit props and emit callbacks instead of importing feature state.
- Include loading, disabled, empty, and error variants when the component presents data or actions.
- Follow the repo's component library, styling system, and icon set.

Common subfolders:

- `ui/`: buttons, inputs, dialogs, menus, tabs, tables, badges, tooltips.
- `layout/`: shell, sidebar, topbar, page headers, responsive containers.
- `forms/`: reusable field wrappers and form controls.

## `src/lib`, `src/services`, or `src/api`

Use one central client layer for backend calls.

Responsibilities:

- Configure API base URLs, headers, auth token attachment, retries, and response parsing.
- Export typed request/response functions.
- Normalize transport errors into stable frontend error objects.
- Keep raw fetch/axios calls out of route and presentational components.

## `src/hooks/` and `src/stores/`

Use hooks and stores for reusable client behavior.

Responsibilities:

- Put browser APIs, subscriptions, shared async state, and reusable mutations in hooks.
- Put cross-page state in stores only when local component state or server cache is not enough.
- Keep store state serializable where practical.
- Provide cleanup for timers, listeners, sockets, and subscriptions.

## `src/styles/`, `src/assets/`, `src/types/`, `src/utils/`

- `styles/`: global CSS, design tokens, Tailwind entry files, theme configuration, and reset files.
- `assets/`: static app-owned images, icons, fonts, and media that are safe to bundle.
- `types/`: shared TypeScript types that are not owned by a single feature.
- `utils/`: pure helpers with no framework, DOM, network, or business workflow dependencies.

## `tests/`, `__tests__/`, or E2E Folders

Use the repo's existing test placement.

Responsibilities:

- Test components and hooks with mocked API clients.
- Test route-level flows when navigation or auth behavior changes.
- Keep E2E tests focused on critical paths.
- Avoid tests that require live secrets, production APIs, or network calls.
