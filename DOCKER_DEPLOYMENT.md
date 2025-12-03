# CI Newsletter - Docker Deployment Guide

## 🐳 Docker Setup

This application is fully containerized with Docker for easy deployment to Google Cloud Platform (GCP).

### Architecture

- **Frontend**: React + Vite (served via Nginx)
- **Backend**: Python Flask API
- **Database**: Google Firestore
- **Storage**: Google Cloud Storage

---

## 📦 Local Development with Docker

### Prerequisites

- Docker and Docker Compose installed
- Google Cloud service account JSON file
- `.env` file with required environment variables

### Quick Start

1. **Start both frontend and backend** (from repo root):
   ```bash
   docker compose -f docker/docker-compose.yml up
   ```

2. **Access the application**:
   - Frontend: http://localhost:8080
   - Backend API: http://localhost:5001

3. **Development mode with hot-reload**:
   ```bash
   docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up
   ```
   - Frontend dev server: http://localhost:5173
   - Backend: http://localhost:5001

### Useful Commands

```bash
# Build images
docker compose -f docker/docker-compose.yml build

# Start in detached mode
docker compose -f docker/docker-compose.yml up -d

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Stop services
docker compose -f docker/docker-compose.yml down

# Remove volumes
docker compose -f docker/docker-compose.yml down -v

# Rebuild and start
docker compose -f docker/docker-compose.yml up --build
```

---

## ☁️ Deploy to Google Cloud Run

### Prerequisites

1. Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
2. Authenticate: `gcloud auth login`
3. Set your project: `gcloud config set project YOUR_PROJECT_ID`
4. Enable required APIs:
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable containerregistry.googleapis.com
   ```

### Option 1: Automated Deployment Script

The easiest way to deploy:

```bash
# Set environment variables (or edit the script)
export PROJECT_ID=YOUR_PROJECT_ID
export REGION=europe-west1
export SERVICE_ACCOUNT=YOUR_SA@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Run deployment
./docker/deploy-to-gcp.sh
```

This script will:
1. Build both frontend and backend images
2. Push them to Google Container Registry
3. Deploy to Cloud Run
4. Configure environment variables
5. Return the URLs for both services

### Option 2: Manual Deployment

#### Deploy Backend

```bash
cd server

# Build and submit
gcloud builds submit --tag gcr.io/$PROJECT_ID/ci-newsletter-backend

# Deploy to Cloud Run
gcloud run deploy ci-newsletter-backend \
  --image gcr.io/$PROJECT_ID/ci-newsletter-backend \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --service-account $SERVICE_ACCOUNT \
  --set-env-vars "PROJECT_ID=$PROJECT_ID,REGION=$REGION,FIRESTORE_DATABASE_ID=(default),COMPOSE_WEEKLY_SIM_WEIGHT=0.3" \
  --port 5001 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300
```

#### Deploy Frontend

```bash
cd client

# Get backend URL first
BACKEND_URL=$(gcloud run services describe ci-newsletter-backend --region $REGION --format 'value(status.url)')

# Build with backend URL
gcloud builds submit --tag gcr.io/$PROJECT_ID/ci-newsletter-frontend \
  --substitutions=_VITE_API_URL="${BACKEND_URL}/api"

# Deploy to Cloud Run
gcloud run deploy ci-newsletter-frontend \
  --image gcr.io/$PROJECT_ID/ci-newsletter-frontend \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1
```

### Option 3: Automated CI/CD with Cloud Build

Set up continuous deployment from your git repository:

```bash
# Submit build using docker/cloudbuild.yaml
gcloud builds submit --config docker/cloudbuild.yaml

# Or connect to GitHub/Cloud Source Repositories for automatic triggers
gcloud beta builds triggers create github \
  --repo-name=YOUR_REPO_NAME \
  --repo-owner=YOUR_GITHUB_USER \
  --branch-pattern="^main$" \
  --build-config=docker/cloudbuild.yaml
```

---

## 🔧 Configuration

### Environment Variables

**Backend** (`.env`):
```env
PROJECT_ID=$PROJECT_ID
REGION=europe-west1
FIRESTORE_DATABASE_ID=(default)
PORT=5001
COMPOSE_WEEKLY_SIM_WEIGHT=0.3
GOOGLE_APPLICATION_CREDENTIALS=./service-account-credentials.json
```

**Frontend** (build-time):
```env
VITE_API_URL=http://localhost:5001/api
```

### Service Account Permissions

Ensure your service account has:
- `roles/firestore.user` - Read/write Firestore
- `roles/storage.objectAdmin` - Access Cloud Storage
- `roles/aiplatform.user` - Use Vertex AI
- `roles/bigquery.dataViewer` - Read BigQuery data

---

## 📊 Monitoring and Logs

### View logs in Cloud Run

```bash
# Backend logs
gcloud run services logs read ci-newsletter-backend --region europe-west1

# Frontend logs
gcloud run services logs read ci-newsletter-frontend --region europe-west1

# Follow logs
gcloud run services logs tail ci-newsletter-backend --region europe-west1
```

### Access Cloud Run console

https://console.cloud.google.com/run?project=$PROJECT_ID

---

## 🚀 Production Best Practices

1. **Custom Domain**: Configure a custom domain for better branding
   ```bash
   gcloud run domain-mappings create --service ci-newsletter-frontend --domain ci.example.com
   ```

2. **HTTPS**: Automatically enabled by Cloud Run

3. **Scaling**:
   - Backend: 0-10 instances (configured in deploy script)
   - Frontend: 0-5 instances
   - Adjust based on traffic patterns

4. **Cost Optimization**:
   - Min instances = 0 to avoid idle costs
   - Use appropriate memory/CPU allocations
   - Monitor usage in Cloud Console

5. **Security**:
   - Keep service account credentials secure
   - Use Secret Manager for sensitive data
   - Enable VPC connector for private resources

---

## 🔄 Update Deployment

To update after code changes:

```bash
# Quick update
./docker/deploy-to-gcp.sh

# Or for specific service
cd server && gcloud builds submit --tag gcr.io/$PROJECT_ID/ci-newsletter-backend
gcloud run deploy ci-newsletter-backend --image gcr.io/$PROJECT_ID/ci-newsletter-backend
```

---

## 🐛 Troubleshooting

**Container fails to start:**
- Check logs: `gcloud run services logs read <service-name>`
- Verify environment variables
- Ensure service account has correct permissions

**Frontend can't reach backend:**
- Verify VITE_API_URL is set correctly during build
- Check CORS configuration in backend

**Authentication errors:**
- Ensure service account JSON is valid
- Check IAM permissions in GCP Console

---

## 📚 Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Container Registry](https://cloud.google.com/container-registry/docs)
- [Cloud Build](https://cloud.google.com/build/docs)
