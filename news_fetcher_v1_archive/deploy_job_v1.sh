# **1. Configuration (Update these values)**
REGION="europe-west1" # Updated region 
IMAGE_NAME="news_fetcher"
JOB_NAME="news-fetcher-job" 

# Get Project ID (excellent error handling!)
if [[ -z "$PROJECT_ID" ]]; then
  echo "Error: PROJECT_ID environment variable is not set."
  echo "Please set it using: export PROJECT_ID='your-project-id'" 
  exit 1
fi

# Ensure gcloud is installed (good check!)
if ! command -v gcloud &> /dev/null; then
  echo "Error: gcloud CLI not found. Please install and authenticate."
  exit 1
fi

# **2. Build the Docker Image**
docker build -t $IMAGE_NAME -f cloud_run_job/Dockerfile .

# # **3. Tag the Image for Artifact Registry (Adjust for europe-west1)**
FULL_IMAGE_NAME="europe-west1-docker.pkg.dev/${PROJECT_ID}/containers/${IMAGE_NAME}" 
docker tag $IMAGE_NAME $FULL_IMAGE_NAME:latest

# # **4. Push to Artifact Registry (Authenticate to correct location)**
gcloud auth configure-docker europe-west1-docker.pkg.dev 
docker push $FULL_IMAGE_NAME:latest

# **5. Create/Update Cloud Run Job**
gcloud run jobs create $JOB_NAME \
  --image=$FULL_IMAGE_NAME:latest \
  --region=$REGION \
  --project=$PROJECT_ID \
  --max-retries=3 

echo "Deployment complete! Check the Cloud Run Jobs console for progress."
