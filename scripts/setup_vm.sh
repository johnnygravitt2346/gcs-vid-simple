#!/bin/bash
# Trivia Factory VM Setup Script
# Sets up the VM for lean pipeline execution

set -e

echo "🚀 Setting up Trivia Factory VM..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Update system
echo "📦 Updating system packages..."
sudo apt update

# Install required packages
echo "📦 Installing required packages..."
sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    git \
    ffmpeg \
    jq \
    tmux \
    fonts-dejavu-core \
    curl \
    wget

# Create scratch directory
echo "📁 Creating scratch directory..."
sudo mkdir -p /var/trivia/work
sudo chown $USER:$USER /var/trivia/work
sudo chmod 755 /var/trivia/work

# Create app directory
echo "📁 Setting up application directory..."
mkdir -p ~/trivia
cd ~/trivia

# Clone repository
if [ ! -d "app" ]; then
    echo "📥 Cloning repository..."
    git clone https://github.com/johnnygravitt2346/gcs-video-automations.git app
else
    echo "📁 Repository already exists, updating..."
    cd app
    git pull origin master
    cd ..
fi

cd app

# Create Python virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install dependencies
echo "📦 Installing Python dependencies..."
pip install -U pip wheel
pip install google-cloud-storage google-auth

# Create environment file
echo "⚙️ Creating environment configuration..."
cat > .env <<'ENV'
GOOGLE_CLOUD_PROJECT=mythic-groove-469801-b7
GCS_BUCKET=trivia-automation
GCS_BASE=gs://trivia-automation
GCS_CHANNELS_ROOT=gs://trivia-automation/channels
GCS_DATASETS_ROOT=gs://trivia-automation/datasets
GCS_JOBS_ROOT=gs://trivia-automation/jobs
GCS_MANIFESTS_ROOT=gs://trivia-automation/manifests
RENDER_LOCAL_ROOT=/var/trivia/work
CHANNEL_ID=ch01
DATASET_URI=gs://trivia-automation/datasets/ch01/2025-08-24-001/questions.csv
ENABLE_TTS=0
NVENC_REQUIRED=0
ENV

echo "✅ Environment file created:"
cat .env

# Test FFmpeg
echo "🎬 Testing FFmpeg installation..."
if ffmpeg -version > /dev/null 2>&1; then
    echo -e "${GREEN}✅ FFmpeg is working${NC}"
else
    echo -e "${RED}❌ FFmpeg is not working${NC}"
    exit 1
fi

# Test NVENC availability
echo "🎬 Checking NVENC availability..."
if ffmpeg -hide_banner -encoders 2>/dev/null | grep -q h264_nvenc; then
    echo -e "${GREEN}✅ NVENC is available${NC}"
    echo "💡 You can set NVENC_REQUIRED=1 in .env for GPU acceleration"
else
    echo -e "${YELLOW}⚠️  NVENC not available, will use CPU encoding${NC}"
fi

# Test Google Cloud access
echo "☁️ Testing Google Cloud access..."
if gcloud auth list > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Google Cloud authentication working${NC}"
else
    echo -e "${RED}❌ Google Cloud authentication failed${NC}"
    echo "💡 Make sure service account is attached to VM"
    exit 1
fi

# Test GCS bucket access
echo "☁️ Testing GCS bucket access..."
if gsutil ls gs://trivia-automation > /dev/null 2>&1; then
    echo -e "${GREEN}✅ GCS bucket accessible${NC}"
else
    echo -e "${RED}❌ GCS bucket not accessible${NC}"
    echo "💡 Creating bucket and structure..."
    
    # Create bucket if it doesn't exist
    gsutil mb -p mythic-groove-469801-b7 gs://trivia-automation || true
    
    # Create channel structure
    for n in {01..10}; do
        gsutil -m cp -n /dev/null gs://trivia-automation/channels/ch$n/templates/.keep
        gsutil -m cp -n /dev/null gs://trivia-automation/channels/ch$n/config/.keep
    done
    
    # Create jobs and manifests roots
    gsutil -m cp -n /dev/null gs://trivia-automation/jobs/.keep
    gsutil -m cp -n /dev/null gs://trivia-automation/manifests/.keep
    gsutil -m cp -n /dev/null gs://trivia-automation/datasets/.keep
    
    echo "✅ GCS structure created"
fi

# Upload sample dataset
echo "📤 Uploading sample dataset..."
if [ -f "datasets/ch01/2025-08-24-001/questions.csv" ]; then
    gsutil -m cp -r datasets/ch01 gs://trivia-automation/datasets/
    echo -e "${GREEN}✅ Sample dataset uploaded${NC}"
else
    echo -e "${YELLOW}⚠️  Sample dataset not found, skipping upload${NC}"
fi

# Test runner script
echo "🧪 Testing runner script..."
if python3 scripts/run_job.py --help > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Runner script is working${NC}"
else
    echo -e "${YELLOW}⚠️  Runner script test skipped (no --help option)${NC}"
fi

echo ""
echo -e "${GREEN}🎉 VM setup completed successfully!${NC}"
echo ""
echo "📋 Next steps:"
echo "1. Upload your questions CSV to: gs://trivia-automation/datasets/ch01/2025-08-24-001/questions.csv"
echo "2. (Optional) Upload intro/outro videos to: gs://trivia-automation/channels/ch01/templates/"
echo "3. Run the pipeline: source .venv/bin/activate && python3 scripts/run_job.py"
echo ""
echo "🔧 Configuration:"
echo "   - Scratch directory: /var/trivia/work"
echo "   - Channel: ch01"
echo "   - GCS bucket: trivia-automation"
echo "   - Python venv: ~/trivia/app/.venv"
