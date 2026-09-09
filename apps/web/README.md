# Web

Next.js frontend for the e-commerce operations assistant. It provides demo scenarios, a question interface, request traces, and pages explaining the architecture and evaluation results.

Follow [Setup and deployment](../../docs/DEPLOY.md) to configure both apps and prepare the API. The [project overview](../../README.md) introduces the workflows.

## Run locally

Run from the repository root:

```bash
pnpm install
pnpm --filter web dev
```

Open `http://localhost:3000`. Live questions and scenarios require the API to be running. The architecture and evaluation pages use content committed to the repository.

Configure `apps/web/.env` from [.env.example](.env.example). `NEXT_PUBLIC_API_URL` points to the API. The server-only `INTERNAL_PROXY_SECRET` must match the backend setting.

Requests to `/api/*` pass through [middleware.ts](src/middleware.ts), which adds the shared-secret header. Keep that secret out of client code.

## Check a change

From the repository root:

```bash
pnpm --filter web test
pnpm --filter web lint
pnpm --filter web build
```

The build downloads Google Fonts. API contract changes also require [regenerating the shared types](../../docs/DEPLOY.md#regenerate-frontend-types).

## Find the source

| Area | Location |
|---|---|
| Pages | [src/app](src/app/) |
| Shared interface components | [src/components](src/components/) |
| API client | [src/lib/api.ts](src/lib/api.ts) |
| Saved evaluation content | [src/lib/evals.ts](src/lib/evals.ts) |
| Generated API types | [packages/shared](../../packages/shared/) |

Hosting settings and deployment verification are in [Deploy the frontend](../../docs/DEPLOY.md#deploy-the-frontend).
