#!/bin/bash
set -e

# CI Newsletter - GCP Cloud Run Deployment Script
# This script deploys both frontend and backend to Google Cloud Run

# Configuration
PROJECT_ID="${PROJECT_ID:-fsa-amadeus-471508}"
REGION="${REGION:-europe-west4}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-your-service-account@fsa-amadeus-471508.iam.gserviceaccount.com}"

# Service names
BACKEND_SERVICE="ci-newsletter-backend"
FRONTEND_SERVICE="ci-newsletter-frontend"

# Image names
BACKEND_IMAGE="gcr.io/${PROJECT_ID}/${BACKEND_SERVICE}"
FRONTEND_IMAGE="gcr.io/${PROJECT_ID}/${FRONTEND_SERVICE}"

echo "🚀 Deploying CI Newsletter to GCP Cloud Run"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo ""

# Ensure we're using the correct project
echo "📋 Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Build and push backend
echo "🔨 Building backend image..."
cd server
gcloud builds submit --tag ${BACKEND_IMAGE}
cd ..

# Deploy backend (initial deployment with wildcard CORS for Cloud Run)
echo "🚀 Deploying backend to Cloud Run..."
gcloud run deploy ${BACKEND_SERVICE} \
  --image ${BACKEND_IMAGE} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --service-account ${SERVICE_ACCOUNT} \
  --set-env-vars "PROJECT_ID=${PROJECT_ID},LOCATION=${REGION},REGION=${REGION},FIRESTORE_DATABASE_ID=(default),COMPOSE_WEEKLY_SIM_WEIGHT=0.3,MODEL_FLASH=gemini-2.5-flash,MODEL_PRO=gemini-2.5-flash,CORS_ORIGINS=https://*.run.app|http://localhost:*" \
  --port 5001 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 10

# Get backend URL
BACKEND_URL=$(gcloud run services describe ${BACKEND_SERVICE} --region ${REGION} --format 'value(status.url)')
echo "✅ Backend deployed at: ${BACKEND_URL}"

# Build and push frontend with backend URL
echo "🔨 Building frontend image with backend URL..."
cd client
gcloud builds submit \
  --substitutions=_VITE_API_URL="${BACKEND_URL}/api",_IMAGE_NAME="${FRONTEND_IMAGE}"
cd ..

# Deploy frontend
echo "🚀 Deploying frontend to Cloud Run..."
gcloud run deploy ${FRONTEND_SERVICE} \
  --image ${FRONTEND_IMAGE} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --min-instances 0 \
  --max-instances 5

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe ${FRONTEND_SERVICE} --region ${REGION} --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Frontend: ${FRONTEND_URL}"
echo "🔧 Backend:  ${BACKEND_URL}"
echo ""
echo "📝 Next steps:"
echo "  - Test the application at ${FRONTEND_URL}"
echo "  - Configure custom domain if needed"
echo "  - Set up Cloud Scheduler for cron jobs"
echo ""
