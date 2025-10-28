---
marp: true
theme: alten
paginate: true
header: " "
---

# Generative Newsletter — Tech Overview
Quick slide deck: goals, features, frontend, and improvements.

---

## 1) Objectives
- Collect trusted industry news on a schedule
- Generate Daily Newsletters and Weekly Digests
- Offer REST APIs to create and read content
- Provide a fast, searchable web app
- Deploy on GCP (Cloud Run, Firestore/BigQuery)

---

## 2) Architecture Overview
- Frontend: React + Vite + TypeScript (`client/`)
- Backend: Python (Flask) (`server/app.py`)
- Jobs: Cloud Run jobs (`cloud_run_job/`)
- Storage: Firestore / BigQuery helpers
- Static assets: Cloud Storage / Nginx (client Docker)

---

## 3) Backend — Main Features
- News fetching & enrichment: `news_fetcher.py`, `utils.py`
- Daily newsletter composition: `newsletter_generation.py`
- Weekly digest builder: `digest_generation.py`
- Search endpoints: `news_search.py`, `search_news.py`
- Data helpers: `firebase_helpers.py`, `bigquery_helpers.py`

---

## 4) Backend — API Overview
- Example: `POST /api/newsletters/email/compose`
- Newsletter CRUD and search endpoints
- JSON payloads; returns organized content (subject/body/sections)
- Implemented in `server/app.py` (Flask routes)

---

## 5) Frontend — Overview
- Entry: `src/main.tsx`, `src/App.tsx`
- Routing: `src/routes/AppRoutes.tsx`
- Pages: `DailyNewsletter.tsx`, `WeeklyDigest.tsx`, `SearchResults.tsx`
- Context: `src/context/NewsletterContext.tsx`
- API: `src/config/apiService.tsx`, `src/backend/ApiHelper.tsx`

---

## 6) Frontend — Key Components
- `NewsletterRenderer`, `DigestRenderer`
- `DailyNewsList`, `NewsList`, `NewsList2`
- `SearchBar`, `SearchResultsSection`
- Navigation: `Header`, `NavigationMenu`, `Sidebar`
- UX: Skeletons in `components/skeletons/`

---

## 7) Data Flow
1) Job fetches news → stores it with helpers
2) API builds newsletter/digest
3) Frontend calls the API with `apiService`
4) DTOs in `dto/InterfaceDefinition.tsx`
5) Components render lists, sections, pagination

---

## 8) Deploy & Ops
- Dockerfiles in `server/` and `client/`
- Cloud Run jobs in `cloud_run_job/` (`deploy_job.sh`, `main.py`)
- Config: `.env`, Secret Manager (suggested)
- Requirements: `server/requirements.txt`, `client/package.json`

---

## 9) Possible Improvements
- Backend: OpenAPI docs, Pub/Sub queues, tracing, tests/CI
- Frontend: React Query, RTL/Vitest, A11y/i18n, dark mode
- Shared: stronger typing, config management, error budgets

---

## 10) Quick Start
- API: `PORT=5001 python server/app.py`
- Web: `cd client && npm i && npm run dev`
- Build: `npm run build`
- Helper: `python pdf_to_txt.py`

---

## 11) Remaining Work — Web App
- Build a simple weekly editor to pick or upload top daily stories
- Support short notes so curators can explain why a story matters

---

## 12) Remaining Work — Automation
- Add CI-powered comments with context, impact, and custom tags
- Auto sort news into sections: general, competitors, finance, research, etc.
- Export HTML that drops straight into the newsletter tool
