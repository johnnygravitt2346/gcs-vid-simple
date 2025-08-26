# Base image
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,video

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    wget \
    git \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Install FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavcodec-extra \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy core requirements and install Python dependencies (paths relative to build context root)
COPY core/requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir -r ./requirements.txt

# Copy core and worker code
COPY core /app/core
COPY cloud-infrastructure/cloud_worker.py /app/worker.py

# Create necessary directories
RUN mkdir -p /app/tmp /app/output /app/assets

# Install common fonts for drawtext
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Expose health check port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Start the worker
CMD ["python3", "worker.py"]
