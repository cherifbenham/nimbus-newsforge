# CI Newsletter – Local Run & GCP Deployment Guide

This document walks through everything needed to run the CI Newsletter system locally and to deploy it onto Google Cloud Platform (GCP). It consolidates the scripts, environment variables, and workflows that already exist in the repo so that you have a single reference for setup, deployment, and troubleshooting. Use the root `README.md` for a high-level overview; this file is the detailed runbook when you need exact commands or checklists.

## 1. Prerequisites

Install or provision the following tools/services before running anything:

- **Node.js 18+** and **npm** for the Vite/React frontend (`client/`).
- **Python 3.12+** plus `python3 -m venv` for the Flask backend (`server/`).
- **Docker** and **Docker Compose v2** if you plan to run locally via containers or deploy using the provided scripts.
- **Google Cloud SDK (gcloud)** authenticated against your project (`gcloud auth login`).
- **Google Cloud services enabled** in the target project:
  - Vertex AI API
  - Firestore API
  - BigQuery API
  - Cloud Storage API
  - Cloud Run Admin API
  - Artifact Registry (or Container Registry if you keep using GCR)
  - Cloud Build API
  - Cloud Scheduler API (only if you plan to run scheduled fetch jobs)
- **Service account** with the minimum roles below, plus the JSON key stored locally for development or uploaded to Secret Manager for production:
  - `roles/run.admin`
  - `roles/artifactregistry.writer`
  - `roles/storage.objectAdmin`
  - `roles/aiplatform.user`
  - `roles/bigquery.dataViewer`
  - `roles/firestore.user`

## 2. Repository Setup

1. **Clone and enter the repo**
   ```bash
   git clone <your-fork-url>
   cd ama_ci_newsletter
   ```
2. **Create `.venv` for backend work** (if you will run the backend locally):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r server/requirements.txt
   ```
3. **Create `.env` in the repo root**. Copy the sample below and edit the values for your own project/region/credentials. Anything left blank will default to what the code expects.
   ```env
   PROJECT_ID=your-gcp-project
   REGION=europe-west4
   LOCATION=europe-west4
   FIRESTORE_DATABASE_ID=(default)
   MODEL_FLASH=gemini-2.5-flash
   MODEL_PRO=gemini-2.5-flash
   PORT=5001
   CORS_ORIGINS=http://localhost:*
   GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
   VITE_API_URL=http://localhost:5001/api
   BQ_DATASET=competitive_intel
   MEDIA_BUCKET=ci-newsletter-media
   DISCOVERY_PROJECT_ID=${PROJECT_ID}
   DISCOVERY_LOCATION=global
   DISCOVERY_ENGINE_ID=<discovery-engine-id>
   COMPOSE_WEEKLY_SIM_WEIGHT=0.3
   COMPOSE_WEEKLY_FALLBACK=1      # set to 0 when you want Gemini-generated insights
   COMPOSE_WEEKLY_PROMPT_LOCAL_ONLY=0
   ```
4. **Place your service-account JSON** somewhere under the repo (or elsewhere on disk) and make sure `GOOGLE_APPLICATION_CREDENTIALS` points to it. The helper scripts will automatically resolve relative paths.
5. **Provision backing resources** (doing this once per project):
   - Firestore database in Native mode.
   - Cloud Storage bucket for newsletters/media (`MEDIA_BUCKET`).
   - BigQuery dataset (defaults to `competitive_intel`). Use `scripts/create_bq_tables.sh` if you need to initialize the tables.
   - Discovery Engine datasource/serving config to power the search UI.

## 3. Running Locally

### 3.1 Fast path via helper script

The `scripts/start_dev.sh` script wires up the Python backend and the Vite frontend for you. It reads `.env`, ensures dependencies are installed, and writes logs under `logs/`.

```bash
./scripts/start_dev.sh        # optional: --fresh to kill old processes, --no-fallback to disable heuristic insights
```

What the script does:
- Loads `.env` (normalizing keys like `PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`).
- Activates `.venv`, installs backend dependencies if missing, and launches `server/app.py` on `PORT` (default `5001`).
- Installs frontend dependencies (if needed) and starts `npm run dev -- --host --port 5173`.

**Stop everything** with:
```bash
./scripts/stop_dev.sh
```

### 3.2 Manual backend + frontend

#### Backend
```bash
source .venv/bin/activate
pip install -r server/requirements.txt
export FLASK_APP=server/app.py
export PORT=5001
python server/app.py
```
The API becomes available at `http://localhost:5001/api`. Hit `http://localhost:5001/api/health` to confirm.

#### Frontend
```bash
cd client
npm install
npm run dev -- --host --port 5173
```
Access the UI at `http://localhost:5173`. The frontend uses `VITE_API_URL` at build time (default `http://localhost:5001/api`).

### 3.3 Docker-based local run

Use Docker if you want closer parity with production or do not want to install Node/Python globally.

- **Hot reload** (backend + frontend dev servers):
  ```bash
  docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build
  ```
  Visits: frontend `http://localhost:5173`, backend `http://localhost:5001`.

- **Prod-like containers** (Nginx + Gunicorn):
  ```bash
  docker compose -f docker/docker-compose.yml up --build -d
  ```
  Frontend on `http://localhost:8080`, backend still listening on `5001`.

Ensure the `.env` file and service-account JSON are mounted/available inside the containers. The compose files already forward `./.env` and the credentials file if you keep the same names.

### 3.4 Data import & scheduled jobs locally

- **Firestore bootstrap**: `python scripts/init_firestore_prod.py` seeds prompt documents and configuration scaffolding.
- **Sync BigQuery ➜ Firestore**: `python scripts/sync_bq_to_firestore.py` populates Firestore collections from BigQuery tables for testing search/digest features.
- **Compose Weekly helpers**: `python scripts/excelfy_compose_weekly.py` converts Compose Weekly output into spreadsheets for review.

These scripts expect the same `.env`/credential context as the backend.

## 4. Deploying to Google Cloud Run

### 4.1 One-time project setup

Run these commands once per project to enable everything Cloud Run and Cloud Build need (replace `$PROJECT_ID` accordingly):

```bash
gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com firestore.googleapis.com bigquery.googleapis.com storage.googleapis.com discoveryengine.googleapis.com cloudscheduler.googleapis.com
```

If you use Artifact Registry instead of the legacy Container Registry, create a repository first:
```bash
gcloud artifacts repositories create containers \
  --repository-format=docker \
  --location=europe-west1 \
  --description="CI newsletter images"
```

Also create or reuse a deploy-focused service account, add the roles listed in §1, and grant Cloud Build the `Service Account User` role on it if you use CI/CD.

### 4.2 Deploy via `docker/deploy-to-gcp.sh`

This script automates building images with Cloud Build and deploying both services. Export the variables you want to override (defaults are baked into the script) and run it from the repo root:

```bash
export PROJECT_ID=<project>
export REGION=europe-west4
export SERVICE_ACCOUNT=<sa>@$PROJECT_ID.iam.gserviceaccount.com
chmod +x docker/deploy-to-gcp.sh
./docker/deploy-to-gcp.sh
```

The script performs:
1. `gcloud config set project $PROJECT_ID`.
2. Cloud Build submission for the backend (`server/`) → image `gcr.io/$PROJECT_ID/ci-newsletter-backend`.
3. Cloud Run deploy of the backend with all required env vars, 1 GiB memory, max 10 instances, and wide CORS for `*.run.app` + localhost.
4. Reads the backend URL and passes it as `_VITE_API_URL` to the frontend Cloud Build (ensuring the final static app points at the deployed API).
5. Deploys the frontend to Cloud Run (512 MiB, port 8080).
6. Prints both service URLs.

If you need extra env vars (e.g., `MEDIA_BUCKET`, `DISCOVERY_*` IDs), edit the `--set-env-vars` block inside `docker/deploy-to-gcp.sh` before running.

### 4.3 Manual Cloud Run deployment (no script)

**Backend**
```bash
cd server
gcloud builds submit --tag gcr.io/$PROJECT_ID/ci-newsletter-backend

gcloud run deploy ci-newsletter-backend \
  --image gcr.io/$PROJECT_ID/ci-newsletter-backend \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --service-account $SERVICE_ACCOUNT \
  --port 5001 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 --max-instances 10 \
  --set-env-vars "PROJECT_ID=$PROJECT_ID,REGION=$REGION,LOCATION=$REGION,FIRESTORE_DATABASE_ID=(default),MODEL_FLASH=gemini-2.5-flash,MODEL_PRO=gemini-2.5-flash,COMPOSE_WEEKLY_SIM_WEIGHT=0.3,BQ_DATASET=competitive_intel,CORS_ORIGINS=https://*.run.app"
```
Capture the backend URL:
```bash
BACKEND_URL=$(gcloud run services describe ci-newsletter-backend --region $REGION --format 'value(status.url)')
```

**Frontend**
```bash
cd client
# Build with backend URL baked in
gcloud builds submit --tag gcr.io/$PROJECT_ID/ci-newsletter-frontend \
  --substitutions=_VITE_API_URL="${BACKEND_URL}/api"

gcloud run deploy ci-newsletter-frontend \
  --image gcr.io/$PROJECT_ID/ci-newsletter-frontend \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1
```
Once live, you can tighten CORS by updating the backend:
```bash
gcloud run services update ci-newsletter-backend \
  --region $REGION \
  --update-env-vars CORS_ORIGINS=$(gcloud run services describe ci-newsletter-frontend --region $REGION --format 'value(status.url)')
```

### 4.4 Cloud Build CI/CD pipeline

`docker/cloudbuild.yaml` builds both services and deploys them, mirroring the script. Trigger it manually or via GitHub/Cloud Source triggers:

```bash
gcloud builds submit --config docker/cloudbuild.yaml
```

To create a GitHub trigger:
```bash
gcloud beta builds triggers create github \
  --name="ci-newsletter-main" \
  --repo-name=<repo-name> \
  --repo-owner=<repo-owner> \
  --branch-pattern="^main$" \
  --build-config=docker/cloudbuild.yaml
```
Configure the trigger to supply `_VITE_API_URL` or let the build step compute it (as in the script).

### 4.5 Automated fetch job (Cloud Run Job + Scheduler)

Use `cloud_run_job/` if you want a scheduled ingestion job.

1. Set variables at the top of `cloud_run_job/deploy_job.sh` (project, region, job/image name).
2. Run the script:
   ```bash
   export PROJECT_ID=<project>
   ./cloud_run_job/deploy_job.sh
   ```
   It builds the job image, pushes it to Artifact Registry (`europe-west1-docker.pkg.dev/$PROJECT_ID/containers/...`), and creates/updates the Cloud Run Job.
3. Trigger manually:
   ```bash
   gcloud run jobs execute news-fetcher-job-v2 --region=$REGION
   ```
4. Hook up Cloud Scheduler to the job for automated runs:
   ```bash
   gcloud scheduler jobs create http ci-newsletter-fetch \
     --schedule="0 6 * * *" \
     --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/news-fetcher-job-v2:run" \
     --http-method=POST \
     --oauth-service-account-email=$SERVICE_ACCOUNT \
     --oauth-token-scope=https://www.googleapis.com/auth/cloud-platform
   ```

Ensure the job image has the same `.env`/secret configuration as the backend (use Secret Manager or pass env vars through `gcloud run jobs update`).

### 4.6 Post-deployment checklist

- Visit the frontend URL and go through Daily/Weekly/Compose Weekly flows.
- Hit `https://<backend-url>/api/health` and `/api/health/deps` to confirm Firestore, BigQuery, and Vertex AI connectivity.
- Grant the Cloud Run runtime service account access to any Firestore collections, GCS buckets, or BigQuery datasets it needs.
- Upload prompt templates/config into Firestore using `scripts/init_firestore_prod.py` if the project has no data yet.
- Update Vertex AI quotas or region settings if you plan to use models outside `us-central1`/`europe-west4`.

## 5. Monitoring & Troubleshooting

- **Logs**:
  ```bash
  gcloud run services logs read ci-newsletter-backend --region $REGION
  gcloud run services logs tail ci-newsletter-backend --region $REGION
  gcloud run services logs read ci-newsletter-frontend --region $REGION
  ```
- **Health checks**: `/api/health` (basic) and `/api/health/deps` (checks Firestore, BigQuery, Vertex AI).
- **Common issues**:
  - *CORS errors*: confirm `CORS_ORIGINS` includes your frontend Run URL.
  - *Vertex AI auth failures*: verify `MODEL_FLASH` / `MODEL_PRO` exist in `REGION` and the service account has `roles/aiplatform.user`.
  - *Discovery Engine search errors*: double-check `DISCOVERY_ENGINE_ID`, `DISCOVERY_LOCATION`, and that the data store is deployed.
  - *Firestore missing documents*: rerun `scripts/init_firestore_prod.py` or seed data manually.

## 6. Environment Variable Reference

| Variable | Description |
| --- | --- |
| `PROJECT_ID` | Target GCP project ID used across Firestore, BigQuery, Cloud Run, Vertex AI, etc. |
| `REGION` / `LOCATION` | Region where Vertex AI, Cloud Run, and other services deploy (`europe-west4` by default). |
| `FIRESTORE_DATABASE_ID` | Firestore database name (`(default)` unless you created a named database). |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path (absolute or relative) to the service-account JSON key for local runs. |
| `MODEL_FLASH`, `MODEL_PRO` | Gemini model versions used for Compose Weekly insights and template generation. |
| `PORT` | Backend listening port in local dev. |
| `CORS_ORIGINS` | Comma/semicolon-separated origins allowed to call the API (supports wildcards like `https://*.run.app`). |
| `VITE_API_URL` | Build-time frontend env var that points to the backend API base (e.g., `http://localhost:5001/api`). |
| `COMPOSE_WEEKLY_SIM_WEIGHT` | Float between 0 and 1 to adjust similarity scoring weight. |
| `COMPOSE_WEEKLY_FALLBACK` | `1`=`use lightweight local heuristics`, `0`=`call Gemini` for Compose Weekly insights. |
| `COMPOSE_WEEKLY_PROMPT_LOCAL_ONLY` | When `true`, prevents prompt definitions from being written back to Firestore. |
| `BQ_DATASET` | BigQuery dataset where news items are stored/read. |
| `MEDIA_BUCKET` | Cloud Storage bucket for attachments and rendered newsletters. |
| `DISCOVERY_PROJECT_ID`, `DISCOVERY_LOCATION`, `DISCOVERY_ENGINE_ID` | Configuration for Google Discovery Engine search. |

Keep this file updated whenever you add new configuration knobs, scripts, or deployment options to make onboarding painless.
