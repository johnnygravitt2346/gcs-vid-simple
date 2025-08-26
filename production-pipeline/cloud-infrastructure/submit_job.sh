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
