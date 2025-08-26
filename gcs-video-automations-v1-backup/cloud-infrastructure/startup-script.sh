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
  IMAGE_PLACEHOLDER
