# NVIDIA CUDA base image for GPU acceleration
FROM nvidia/cuda:11.8-devel-ubuntu20.04

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

# Install FFmpeg with NVIDIA hardware acceleration
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavcodec-extra \
    && rm -rf /var/lib/apt/lists/*

# Verify FFmpeg has NVENC support
RUN ffmpeg -hide_banner -encoders | grep -i nvenc || (echo "NVENC not available" && exit 1)

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the worker script
COPY cloud_worker.py /app/worker.py

# Create necessary directories
RUN mkdir -p /app/tmp /app/output /app/assets

# Expose health check port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Start the worker
CMD ["python3", "worker.py"]
