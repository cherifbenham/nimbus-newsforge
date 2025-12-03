# CI Newsletter Frontend

React + TypeScript + Vite application that powers the CI Newsletter UI (Daily News, Weekly Digest, Compose Weekly, Search, and Setup screens).

## Requirements

- Node.js 18+
- npm 9+
- A running backend API (`http://localhost:5001/api` when developing locally)

## Commands

```
# Install dependencies (first run)
npm install

# Start Vite dev server on http://localhost:5173
npm run dev

# Type-check/lint
npm run lint

# Production build (outputs to dist/)
npm run build

# Preview production build locally
npm run preview
```

## Environment Variables

Only build-time variables prefixed with `VITE_` are available inside the app.

| Variable | Description |
| --- | --- |
| `VITE_API_URL` | Base URL for the Flask backend (defaults to `http://localhost:5001/api`). |

For Cloud Run deployments, `docker/deploy-to-gcp.sh` sets `_VITE_API_URL` during the Cloud Build step so the production bundle targets the deployed backend service automatically.

## Key Source Files

- `src/backend/ApiHelper.tsx` – Centralized API client used across pages.
- `src/pages/ComposeWeekly.tsx` – Compose Weekly workflow, AI scoring, and exports.
- `src/pages/WeeklyDigest.tsx` & `src/pages/DailyNewsletter.tsx` – Digest/news views.
- `src/pages/Setup.tsx` – Prompt editors and configuration controls.

Refer to the root `README.md`/`instructions.md` for full-stack setup and deployment guides.
