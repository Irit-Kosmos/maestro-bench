# MAESTRO-bench frontend

Nuxt 4 + Nuxt UI single-page application for the MAESTRO-bench API. See the
[root README](../README.md) for the full project setup.

## Development

```bash
pnpm install
pnpm dev               # http://localhost:3000, expects the API on http://localhost:8000
```

## Other commands

```bash
pnpm lint        # ESLint (@antfu/eslint-config)
pnpm lint:fix
pnpm build       # production build in .output/
pnpm preview
```

## Layout

- `app/pages/` – one route per resource (experiments, batches, analyses, datasets, agents, prompts, models, settings)
- `app/components/` – auto-imported components, grouped by feature
- `app/composables/` – API calls and page logic (`useMyLazyFetch` wraps `useLazyFetch` with the backend base URL)
- `app/types/index.ts` – TypeScript mirror of the backend schemas

Navigation is keyboard-first: press `?` in the app for the shortcuts, `⌘K` for the command palette.

## License

Part of MAESTRO-bench, licensed under the GNU AGPL v3 or later. See the
[License section of the root README](../README.md#license).
