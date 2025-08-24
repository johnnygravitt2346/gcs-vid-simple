# Trivia Factory Pipeline - Google Cloud Environment
FROM nvidia/cuda:11.8-devel-ubuntu20.04

# Environment variables at the top for easy discovery
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV ASSETS_DIR=/app/assets
ENV GOOGLE_CLOUD_PROJECT=mythic-groove-469801-b7
ENV GOOGLE_CLOUD_REGION=us-central1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.9 \
    python3.9-dev \
    python3.9-distutils \
    python3-pip \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    libgl1-mesa-glx \
    fonts-dejavu \
    fonts-liberation \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python3
RUN ln -s /usr/bin/python3.9 /usr/bin/python3

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Set up working directory
WORKDIR /app

# Copy application code
COPY src/ /app/src/
COPY config/ /app/config/
COPY ui/ /app/ui/
COPY scripts/ /app/scripts/

# Copy the video generation script
COPY trivia_video_generator.py /app/scripts/

# Create necessary directories
RUN mkdir -p /app/assets /app/output /app/temp

# Set permissions
RUN chmod +x /app/scripts/*.py

# Expose port for UI
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Default command
CMD ["python3", "src/ui.py"]
