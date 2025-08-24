#!/bin/bash

# Trivia Factory Deployment Script for Google Cloud
# This script sets up the complete pipeline infrastructure

set -e

# Configuration
PROJECT_ID="mythic-groove-469801-b7"
REGION="us-central1"
ZONE="us-central1-a"
BUCKET_NAME="trivia-factory-prod"
SERVICE_NAME="trivia-factory"
IMAGE_NAME="gcr.io/${PROJECT_ID}/trivia-factory"

echo "🚀 Deploying Trivia Factory to Google Cloud..."

# 1. Set project and enable APIs
echo "📋 Setting up Google Cloud project..."
gcloud config set project ${PROJECT_ID}
gcloud services enable compute.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable texttospeech.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# 2. Create GCS bucket with lifecycle policies
echo "🪣 Creating GCS bucket with lifecycle policies..."
gsutil mb -p ${PROJECT_ID} -c STANDARD -l ${REGION} gs://${BUCKET_NAME} || echo "Bucket already exists"

# Set lifecycle policy for cost optimization
cat > lifecycle.json << 'LIFECYCLE'
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {
        "age": 7,
        "matchesStorageClass": ["STANDARD", "NEARLINE"]
      }
    },
    {
      "action": {"type": "Delete"},
      "condition": {
        "age": 30,
        "matchesStorageClass": ["COLDLINE"]
      }
    }
  ]
}
LIFECYCLE

gsutil lifecycle set lifecycle.json gs://${BUCKET_NAME}

# 3. Create bucket structure
echo "📁 Setting up bucket structure..."
gsutil -m cp -r assets/ gs://${BUCKET_NAME}/
gsutil -m cp -r config/ gs://${BUCKET_NAME}/

# 4. Build and push Docker image
echo "🐳 Building and pushing Docker image..."
gcloud builds submit --tag ${IMAGE_NAME} .

# 5. Create preemptible instance template for T4 workers
echo "⚡ Creating preemptible instance template..."
gcloud compute instance-templates create trivia-factory-worker \
    --machine-type=n1-standard-4 \
    --accelerator=type=nvidia-tesla-t4,count=1 \
    --maintenance-policy=TERMINATE \
    --preemptible \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=50GB \
    --boot-disk-type=pd-standard \
    --metadata=startup-script='#!/bin/bash
        # Install Docker and NVIDIA drivers
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        usermod -aG docker $USER
        
        # Install NVIDIA drivers
        apt-get update
        apt-get install -y nvidia-driver-470
        
        # Pull and run trivia factory worker
        docker pull gcr.io/mythic-groove-469801-b7/trivia-factory
        docker run --gpus all -d \
            -e GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json \
            -v /path/to/service-account.json:/path/to/service-account.json \
            gcr.io/mythic-groove-469801-b7/trivia-factory' \
    --tags=trivia-factory-worker

# 6. Create managed instance group for auto-scaling
echo "📊 Creating managed instance group..."
gcloud compute instance-groups managed create trivia-factory-workers \
    --base-instance-name=trivia-worker \
    --template=trivia-factory-worker \
    --size=0 \
    --zone=${ZONE}

# Set auto-scaling policy
gcloud compute instance-groups managed set-autoscaling trivia-factory-workers \
    --zone=${ZONE} \
    --min-num-replicas=0 \
    --max-num-replicas=10 \
    --target-cpu-utilization=0.7 \
    --cool-down-period=300

# 7. Deploy main pipeline service
echo "🌐 Deploying main pipeline service..."
gcloud run deploy ${SERVICE_NAME} \
    --image=${IMAGE_NAME} \
    --platform=managed \
    --region=${REGION} \
    --allow-unauthenticated \
    --port=8080 \
    --memory=2Gi \
    --cpu=2 \
    --max-instances=5 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_REGION=${REGION},GCS_BUCKET_NAME=${BUCKET_NAME}"

# 8. Create Cloud Scheduler for cleanup jobs
echo "⏰ Setting up Cloud Scheduler for cleanup..."
gcloud scheduler jobs create http trivia-cleanup \
    --schedule="0 2 * * *" \
    --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/cleanup" \
    --http-method=POST \
    --time-zone="UTC"

# 9. Set up monitoring and alerting
echo "📊 Setting up monitoring..."
gcloud monitoring dashboards create --config-from-file=- << 'DASHBOARD'
{
  "displayName": "Trivia Factory Pipeline",
  "gridLayout": {
    "columns": "2",
    "widgets": [
      {
        "title": "Active Jobs",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "metric.type=\"custom.googleapis.com/trivia/jobs/active\""
              }
            }
          }]
        }
      },
      {
        "title": "Video Generation Rate",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "metric.type=\"custom.googleapis.com/trivia/videos/generated\""
              }
            }
          }]
        }
      }
    ]
  }
}
DASHBOARD

echo "✅ Trivia Factory deployment completed!"
echo ""
echo "🌐 Main Service URL: https://${SERVICE_NAME}-$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')"
echo "🪣 GCS Bucket: gs://${BUCKET_NAME}"
echo "⚡ Worker Template: trivia-factory-worker"
echo "📊 Auto-scaling Group: trivia-factory-workers"
echo ""
echo "�� Next steps:"
echo "1. Set up service account credentials"
echo "2. Configure Gemini API key"
echo "3. Upload video templates to GCS"
echo "4. Test the pipeline with a sample job"
