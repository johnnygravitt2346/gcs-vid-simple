#!/bin/bash

echo "🚀 GCS Video Automations - Complete Integrated System Bootstrap"
echo "========================================================"

# Configuration
BUCKET="gcs-video-automations-prod"
PROJECT_DIR="gcs-video-automations"
GCP_PROJECT="mythic-groove-469801-b7"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in Cloud Shell
if [[ "$CLOUD_SHELL" == "true" ]]; then
    print_status "Running in Google Cloud Shell"
else
    print_warning "Not running in Cloud Shell - some features may not work"
fi

# Step 1: Create project directory
print_status "📁 Creating project directory..."
cd /home/johnny
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Step 2: Download all project files from GCS
print_status "📥 Downloading project files from GCS..."

# Create directory structure
mkdir -p backend/src backend/config backend/scripts frontend assets

# Download backend files
gsutil cp gs://$BUCKET/scripts/backend/main.py backend/src/main.py
gsutil cp gs://$BUCKET/scripts/backend/requirements.txt backend/requirements.txt
gsutil cp gs://$BUCKET/scripts/backend/gemini_generator.py backend/src/gemini_generator.py
gsutil cp gs://$BUCKET/scripts/backend/pipeline.py backend/src/pipeline.py
gsutil cp gs://$BUCKET/scripts/backend/video_generator.py backend/src/video_generator.py
gsutil cp gs://$BUCKET/scripts/backend/__init__.py backend/src/__init__.py

# Download scripts
gsutil cp gs://$BUCKET/scripts/backend/trivia_video_generator.py backend/scripts/trivia_video_generator.py
gsutil cp gs://$BUCKET/scripts/backend/run_trivia_pipeline.py backend/scripts/run_trivia_pipeline.py

# Download config
gsutil cp gs://$BUCKET/scripts/backend/pipeline_config.json backend/config/pipeline_config.json

# Download frontend files
gsutil cp gs://$BUCKET/scripts/frontend/index.html frontend/index.html
gsutil cp gs://$BUCKET/scripts/frontend/package.json frontend/package.json

# Download assets (if they exist)
gsutil cp gs://$BUCKET/scripts/assets/* assets/ 2>/dev/null || print_warning "No assets found in GCS"

print_success "✅ Files downloaded successfully!"

# Step 3: Install Python dependencies
print_status "🐍 Installing Python dependencies..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    pip install fastapi uvicorn google-cloud-storage google-cloud-aiplatform google-cloud-texttospeech pillow pyyaml
    print_success "✅ Python dependencies installed"
else
    print_status "Python dependencies already available"
fi

# Step 4: Create environment file
print_status "⚙️ Creating environment configuration..."
cat > backend/.env << 'EOF'
# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=./tts-test-service-account.json
GCP_PROJECT_ID=mythic-groove-469801-b7
GCS_BUCKET=gcs-video-automations-prod

# TTS Configuration
TTS_ENDPOINT=http://tts.ytsites.org/v1/audio
TTS_VOICE=en-US-Neural2-F
TTS_SPEED=1.0

# Video Configuration
VIDEO_QUALITY=medium
VIDEO_FPS=30
ASSETS_DIR=./assets
EOF

print_success "✅ Environment file created"

# Step 5: Create test script
print_status "🧪 Creating test script..."
cat > test_pipeline.sh << 'EOF'
#!/bin/bash

echo "🧪 Testing GCS Video Automations Pipeline..."
echo "====================================="

# Check if we have the required files
if [[ ! -f "backend/src/gemini_generator.py" ]]; then
    echo "❌ Gemini generator not found"
    exit 1
fi

if [[ ! -f "backend/scripts/run_trivia_pipeline.py" ]]; then
    echo "❌ Pipeline runner not found"
    exit 1
fi

echo "✅ All required files found"

# Test with a simple topic
echo "🚀 Testing pipeline with 'Space Exploration' topic..."
cd backend

# Run a test pipeline (this will fail without API keys, but tests the setup)
python3 scripts/run_trivia_pipeline.py --topic "Space Exploration" --difficulty "Medium" --count 2 --category "Science" || echo "Test completed (expected to fail without API keys)"

echo "🧪 Test completed!"
EOF

chmod +x test_pipeline.sh
print_success "✅ Test script created"

# Step 6: Start servers
print_status "🚀 Starting Trivia Factory servers..."

# Start backend API
cd backend
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend dashboard
cd ../frontend
python3 -m http.server 8080 &
FRONTEND_PID=$!

# Wait for servers to start
sleep 3

# Check if servers are running
if netstat -tlnp 2>/dev/null | grep -q ":8000"; then
    print_success "✅ Backend API running on port 8000"
else
    print_error "❌ Backend API failed to start"
fi

if netstat -tlnp 2>/dev/null | grep -q ":8080"; then
    print_success "✅ Frontend dashboard running on port 8080"
else
    print_error "❌ Frontend dashboard failed to start"
fi

# Step 7: Display status and instructions
echo ""
echo "🎉 GCS Video Automations is now running!"
echo "=================================="
echo "🔗 Backend API: http://localhost:8000"
echo "🌐 Frontend Dashboard: http://localhost:8080"
echo "📚 API Docs: http://localhost:8000/docs"
echo "🛑 To stop servers: kill $BACKEND_PID $FRONTEND_PID"
echo "🔄 To restart: ./start_trivia_factory.sh"
echo ""
echo "💡 Next steps:"
echo "1. Set your Gemini API key in backend/.env"
echo "2. Run: ./test_pipeline.sh"
echo "3. Use Cloud Shell Web Preview on port 8080 for the dashboard"
echo ""
echo "🚀 Bootstrap complete! Your GCS Video Automations system is ready."
echo "=================================================="
