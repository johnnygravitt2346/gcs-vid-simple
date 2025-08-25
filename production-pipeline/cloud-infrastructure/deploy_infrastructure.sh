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

# Create GCS bucket if it doesn't exist
echo "🪣 Creating GCS bucket $BUCKET_NAME"
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME || echo "Bucket already exists"

# Create bucket structure
echo "📁 Creating bucket structure"
gsutil -m cp -r gs://trivia-automations-2/channel-test/video-assets gs://$BUCKET_NAME/ || echo "Assets already exist"

# Build and push Docker image
echo "🐳 Building and pushing Docker image"
IMAGE_NAME="gcr.io/$PROJECT_ID/gpu-video-worker"
IMAGE_TAG="latest"

# Build the image
docker build -t $IMAGE_NAME:$IMAGE_TAG .

# Configure Docker for GCR
gcloud auth configure-docker

# Push the image
docker push $IMAGE_NAME:$IMAGE_TAG

echo "✅ Docker image pushed: $IMAGE_NAME:$IMAGE_TAG"

# Create startup script
echo "📝 Creating startup script"
cat > startup-script.sh << 'EOF'
#!/bin/bash
# Startup script for GPU video rendering worker

# Install Docker
apt-get update
apt-get install -y docker.io

# Start Docker service
systemctl start docker
systemctl enable docker

# Pull the worker image
docker pull IMAGE_PLACEHOLDER

# Run the worker container with GPU access
docker run --rm \
  --gpus all \
  --name gpu-video-worker \
  -p 8080:8080 \
  -e GCS_BUCKET=BUCKET_PLACEHOLDER \
  -e WORKER_ID=worker-$(hostname) \
  -v /var/run/docker.sock:/var/run/docker.sock \
  IMAGE_PLACEHOLDER
EOF

# Replace placeholders in startup script
sed -i "s|IMAGE_PLACEHOLDER|$IMAGE_NAME:$IMAGE_TAG|g" startup-script.sh
sed -i "s|BUCKET_PLACEHOLDER|$BUCKET_NAME|g" startup-script.sh

# Create instance template
echo "🏗️ Creating instance template"
gcloud compute instance-templates create gpu-video-worker-template \
  --machine-type=$MACHINE_TYPE \
  --zone=$ZONE \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-ssd \
  --accelerator="type=$GPU_TYPE,count=1" \
  --maintenance-policy=TERMINATE \
  --restart-on-failure \
  --metadata-from-file=startup-script=startup-script.sh \
  --tags=gpu-worker,http-server \
  --network-interface=network-tier=PREMIUM,subnet=default

# Create firewall rule for health checks
echo "🔥 Creating firewall rule for health checks"
gcloud compute firewall-rules create gpu-worker-health-check \
  --allow=tcp:8080 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=gpu-worker \
  --description="Allow health check traffic to GPU workers"

# Create health check
echo "🏥 Creating health check"
gcloud compute health-checks create http gpu-worker-health-check \
  --port=8080 \
  --request-path=/healthz \
  --check-interval=30s \
  --timeout=10s \
  --unhealthy-threshold=3 \
  --healthy-threshold=2

# Create managed instance group
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

# Create autoscaler
echo "⚖️ Creating autoscaler"
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
  "total_questions": 10,
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
