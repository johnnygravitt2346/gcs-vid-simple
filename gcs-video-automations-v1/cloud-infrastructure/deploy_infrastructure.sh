#!/bin/bash
# Deploy GPU Video Rendering Infrastructure
# This script creates the complete infrastructure for the scalable GPU rendering system

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
REGION=${REGION:-"us-central1"}
ZONE=${ZONE:-"us-central1-a"}
MACHINE_TYPE=${MACHINE_TYPE:-"n1-standard-8"}
GPU_TYPE=${GPU_TYPE:-"nvidia-tesla-t4"}
MIN_INSTANCES=${MIN_INSTANCES:-1}
MAX_INSTANCES=${MAX_INSTANCES:-20}
BUCKET_NAME=${BUCKET_NAME:-"trivia-automation"}
ASSETS_BUCKET_OVERRIDE=${ASSETS_BUCKET_OVERRIDE:-"trivia-automations-2"}
ASSETS_BASE_PATH_OVERRIDE=${ASSETS_BASE_PATH_OVERRIDE:-"channel-test/video-assets"}
SERVICE_ACCOUNT_EMAIL=${SERVICE_ACCOUNT_EMAIL:-"$(gcloud iam service-accounts list --filter="displayName:Compute Engine default service account" --format="value(email)" 2>/dev/null || true)"}

echo "🚀 Deploying GPU Video Rendering Infrastructure"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Zone: $ZONE"
echo "Machine Type: $MACHINE_TYPE"
echo "GPU: $GPU_TYPE"
echo "Instance Range: $MIN_INSTANCES - $MAX_INSTANCES"

# Check if gcloud is configured
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Error: gcloud not authenticated. Please run 'gcloud auth login' first."
    exit 1
fi

# Set project
echo "📋 Setting project to $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Enable required services (idempotent)
echo "🧩 Enabling required services"
gcloud services enable compute.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com || true

# Create GCS bucket if it doesn't exist
echo "🪣 Creating GCS bucket $BUCKET_NAME"
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME || echo "Bucket already exists"

# Create bucket structure
echo "📁 Creating bucket structure"
gsutil -m cp -r gs://trivia-automations-2/channel-test/video-assets gs://$BUCKET_NAME/ || echo "Assets already exist"

# Build and push Docker image (Cloud Build)
echo "🐳 Building and pushing Docker image via Cloud Build"
IMAGE_NAME="gcr.io/$PROJECT_ID/gpu-video-worker"
IMAGE_TAG="latest"

# Create a minimal build context to avoid uploading large local files
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PIPELINE_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
TMP_BUILD_DIR=$(mktemp -d -t gpu-worker-build-XXXXXXXX)

echo "📦 Creating minimal build context at $TMP_BUILD_DIR"
mkdir -p "$TMP_BUILD_DIR/core" "$TMP_BUILD_DIR/cloud-infrastructure"

# Copy only required files
rsync -a --exclude='__pycache__' --exclude='*.pyc' "$PIPELINE_DIR/core/" "$TMP_BUILD_DIR/core/"
cp "$PIPELINE_DIR/cloud-infrastructure/Dockerfile" "$TMP_BUILD_DIR/cloud-infrastructure/Dockerfile"
cp "$PIPELINE_DIR/cloud-infrastructure/cloud_worker.py" "$TMP_BUILD_DIR/cloud-infrastructure/cloud_worker.py"

# Add strict allowlist .gcloudignore in the temp context
cat > "$TMP_BUILD_DIR/.gcloudignore" << 'EOF'
**
!.gcloudignore
!cloud-infrastructure/
!cloud-infrastructure/Dockerfile
!cloud-infrastructure/cloud_worker.py
!cloud-infrastructure/**
!core/**
!core/requirements.txt
EOF

# Generate Cloud Build config inside the temp context
cat > "$TMP_BUILD_DIR/cloudbuild-worker.yaml" << EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '${IMAGE_NAME}:${IMAGE_TAG}', '-f', 'cloud-infrastructure/Dockerfile', '.']
images:
  - '${IMAGE_NAME}:${IMAGE_TAG}'
EOF

# Submit the minimal context
IMAGE_NAME="$IMAGE_NAME" IMAGE_TAG="$IMAGE_TAG" gcloud builds submit --project "$PROJECT_ID" --config "$TMP_BUILD_DIR/cloudbuild-worker.yaml" "$TMP_BUILD_DIR"

echo "✅ Docker image available: $IMAGE_NAME:$IMAGE_TAG"

# Create instance template (zonal flag not supported for create-with-container)
echo "🏗️ Creating startup script for GPU worker"
STARTUP_SCRIPT_PATH=$(mktemp -t startup-script-XXXXXXXX.sh)
cat > "$STARTUP_SCRIPT_PATH" << 'SCRIPT_EOF'
#!/bin/bash
set -euxo pipefail

echo "[startup] Begin GPU worker setup"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y curl ca-certificates gnupg lsb-release docker.io

# Install NVIDIA drivers
add-apt-repository -y ppa:graphics-drivers/ppa || true
apt-get update
apt-get install -y nvidia-driver-535 || apt-get install -y nvidia-driver-550 || true

# NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
apt-get update
apt-get install -y nvidia-container-toolkit
systemctl restart docker

# Configure Docker default runtime to nvidia
cat >/etc/docker/daemon.json << DOCKER_EOF
{
  "default-runtime": "nvidia",
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  }
}
DOCKER_EOF
systemctl restart docker

IMAGE="${IMAGE_NAME:-gcr.io/$PROJECT_ID/gpu-video-worker:latest}"
echo "[startup] Pulling image: $IMAGE"
docker pull "$IMAGE" || true

# Create and run the worker container
docker rm -f gpu-worker || true
docker run -d --name gpu-worker \
  --gpus all \
  --restart always \
  -e GCS_BUCKET=${GCS_BUCKET:-trivia-automation} \
  -e ASSETS_BUCKET=${ASSETS_BUCKET:-trivia-automations-2} \
  -e ASSETS_BASE_PATH=${ASSETS_BASE_PATH:-channel-test/video-assets} \
  -p 8080:8080 \
  "$IMAGE"

echo "[startup] GPU worker container started"
SCRIPT_EOF

echo "🏗️ Creating instance template (GPU, Ubuntu, startup-script)"
gcloud compute instance-templates create gpu-video-worker-template \
  --machine-type=$MACHINE_TYPE \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-ssd \
  --maintenance-policy=TERMINATE \
  --restart-on-failure \
  --accelerator=count=1,type=$GPU_TYPE \
  --metadata-from-file=startup-script=$STARTUP_SCRIPT_PATH \
  --metadata=IMAGE_NAME=$IMAGE_NAME,GCS_BUCKET=$BUCKET_NAME,ASSETS_BUCKET=$ASSETS_BUCKET_OVERRIDE,ASSETS_BASE_PATH=$ASSETS_BASE_PATH_OVERRIDE \
  --scopes=cloud-platform \
  ${SERVICE_ACCOUNT_EMAIL:+--service-account=$SERVICE_ACCOUNT_EMAIL} \
  --tags=gpu-worker,http-server

# Create firewall rule for health and status endpoints
echo "🔥 Creating firewall rule for health checks"
gcloud compute firewall-rules create gpu-worker-health-check \
  --allow=tcp:8080 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=gpu-worker \
  --description="Allow health check traffic to GPU workers" || true

# Create health check
echo "🏥 Creating health check"
gcloud compute health-checks create http gpu-worker-health-check \
  --port=8080 \
  --request-path=/healthz \
  --check-interval=30s \
  --timeout=10s \
  --unhealthy-threshold=3 \
  --healthy-threshold=2 || true

# Create managed instance group (zonal)
echo "👥 Creating managed instance group"
gcloud compute instance-groups managed create gpu-video-workers \
  --zone=$ZONE \
  --template=gpu-video-worker-template \
  --size=$MIN_INSTANCES \
  --health-check=gpu-worker-health-check \
  --initial-delay=300

# Set autoscaling policy
echo "📊 Setting autoscaling policy"
gcloud compute instance-groups managed set-autoscaling gpu-video-workers \
  --zone=$ZONE \
  --min-num-replicas=$MIN_INSTANCES \
  --max-num-replicas=$MAX_INSTANCES \
  --target-cpu-utilization=0.7 \
  --cool-down-period=300

# Create job submission script
echo "📝 Creating job submission script"
cat > submit_job.sh << 'EOF'
#!/bin/bash
# Submit a video rendering job to the GPU worker pool

if [ $# -lt 3 ]; then
    echo "Usage: $0 <channel> <job_id> <config_file>"
    echo "Example: $0 channel-test job-001 config.json"
    exit 1
fi

CHANNEL=$1
JOB_ID=$2
CONFIG_FILE=$3
BUCKET_NAME=${BUCKET_NAME:-"trivia-automation"}

# Create job directory structure
JOB_DIR="gs://$BUCKET_NAME/jobs/$CHANNEL/$JOB_ID"

echo "🚀 Submitting job $JOB_ID for channel $CHANNEL"

# Create job directory
gsutil -m mkdir -p $JOB_DIR

# Upload config file
gsutil cp $CONFIG_FILE $JOB_DIR/config.json

# Create initial status
cat > status.json << STATUS_EOF
{
  "status": "pending",
  "channel": "$CHANNEL",
  "job_id": "$JOB_ID",
  "submitted_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "worker_id": null,
  "started_at": null
}
STATUS_EOF

gsutil cp status.json $JOB_DIR/status.json

echo "✅ Job $JOB_ID submitted successfully"
echo "Job directory: $JOB_DIR"
echo "Monitor status: gsutil cat $JOB_DIR/status.json"
EOF

chmod +x submit_job.sh

# Create sample job config
echo "📋 Creating sample job configuration"
cat > sample_job_config.json << 'EOF'
{
  "channel": "channel-test",
  "total_questions": 3,
  "tts_voice": "en-US-Neural2-F",
  "tts_speed": 1.0,
  "questions": [
    {
      "question": "Which sport is known as 'the king of sports'?",
      "answer_a": "Basketball",
      "answer_b": "Baseball",
      "answer_c": "Tennis",
      "answer_d": "Soccer",
      "correct_answer": "Soccer"
    }
  ]
}
EOF

echo ""
echo "🎉 Infrastructure deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Submit a test job: ./submit_job.sh channel-test test-001 sample_job_config.json"
echo "2. Monitor workers: gcloud compute instance-groups managed list-instances gpu-video-workers --zone=$ZONE"
echo "3. Check autoscaling: gcloud compute instance-groups managed describe gpu-video-workers --zone=$ZONE"
echo ""
echo "🔍 Useful commands:"
echo "- View logs: gcloud compute instances tail-serial-port-output <instance-name> --zone=$ZONE"
echo "- SSH to worker: gcloud compute ssh <instance-name> --zone=$ZONE"
echo "- Scale manually: gcloud compute instance-groups managed resize gpu-video-workers --size=5 --zone=$ZONE"
echo ""
echo "📊 Monitoring endpoints:"
echo "- Health check: http://<worker-ip>:8080/healthz"
echo "- Status: http://<worker-ip>:8080/status"
