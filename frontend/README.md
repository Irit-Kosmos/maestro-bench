# MAESTRO-bench frontend

Nuxt 4 + Nuxt UI single-page application for the MAESTRO-bench API. See the
[root README](../README.md) for the full project setup.

## Development

```bash
pnpm install
cp .env.example .env   # NUXT_PUBLIC_BACK_URL, defaults to http://localhost:8000
pnpm dev               # http://localhost:3000
```

## Other commands

```bash
pnpm lint        # ESLint (@antfu/eslint-config)
pnpm lint:fix
pnpm build       # production build in .output/
pnpm preview
```

## Layout

- `app/pages/` – one route per resource (experiments, datasets, agents, prompts, models)
- `app/components/` – auto-imported components, grouped by feature
- `app/composables/` – API calls and page logic (`useMyLazyFetch` wraps `useLazyFetch` with the backend base URL)
- `app/types/index.ts` – TypeScript mirror of the backend schemas
