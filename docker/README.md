# Docker Configuration

This directory contains all Docker and deployment-related files.

## Files

- **`docker-compose.yml`** - Production Docker Compose configuration
- **`docker-compose.dev.yml`** - Development overrides with hot-reload
- **`cloudbuild.yaml`** - Google Cloud Build CI/CD configuration
- **`deploy-to-gcp.sh`** - Automated deployment script for GCP Cloud Run
- **`.dockerignore`** - Files to exclude from Docker build context

## Usage

### Local Development with Docker

```bash
# From project root
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up
```

### Deploy to GCP

```bash
# From project root
./docker/deploy-to-gcp.sh
```

### Manual Cloud Build

```bash
# From project root
gcloud builds submit --config=docker/cloudbuild.yaml
```

## Individual Dockerfiles

- **Backend**: `server/Dockerfile`
- **Frontend**: `client/Dockerfile`
- **Frontend Dev**: `client/Dockerfile.dev`
- **Cloud Run Job**: `cloud_run_job/Dockerfile`
