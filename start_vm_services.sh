#!/bin/bash
# Trivia Factory VM Services Startup Script
# First Test Topology: API + Worker + UI on the same VM

set -e

echo "🎬 Starting Trivia Factory Services on VM..."
echo "Topology: API + Worker + UI on same VM"
echo ""

# Check if .env file exists
if [ ! -f "backend/.env" ]; then
    echo "❌ Error: backend/.env file not found!"
    echo "Please copy backend/env.example to backend/.env and configure it."
    exit 1
fi

# Load environment variables
source backend/.env

# Run cloud-only guard script
echo "🔒 Running cloud-only validation..."
if ! backend/bin/guard_cloud_only.sh; then
    echo "❌ Cloud-only validation failed!"
    echo "Please fix the issues before starting services."
    exit 1
fi
echo "✅ Cloud-only validation passed!"

echo "📋 Configuration:"
echo "  Project: ${GOOGLE_CLOUD_PROJECT}"
echo "  Bucket: ${GCS_BUCKET}"
echo "  API URL: ${API_BASE_URL}"
echo "  Channel: ${CHANNEL_ID}"
echo ""

# Check if Python dependencies are installed
echo "🔍 Checking dependencies..."
cd backend
if ! python3 -c "import streamlit, fastapi, uvicorn" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    pip3 install -r requirements.txt
fi
cd ..

# Function to start service in background
start_service() {
    local name=$1
    local cmd=$2
    local log_file=$3
    
    echo "🚀 Starting $name..."
    echo "  Command: $cmd"
    echo "  Log file: $log_file"
    
    # Create logs directory
    mkdir -p logs
    
    # Start service in background
    nohup bash -c "$cmd" > "$log_file" 2>&1 &
    local pid=$!
    
    # Store PID
    echo $pid > "logs/${name}.pid"
    echo "  ✅ $name started with PID: $pid"
    echo ""
}

# Stop any existing services
echo "🛑 Stopping any existing services..."
for service in api worker ui; do
    if [ -f "logs/${service}.pid" ]; then
        pid=$(cat "logs/${service}.pid")
        if kill -0 $pid 2>/dev/null; then
            echo "  Stopping $service (PID: $pid)..."
            kill $pid
        fi
        rm -f "logs/${service}.pid"
    fi
done
echo ""

# Start API service
start_service "API" \
    "cd backend && python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000" \
    "logs/api.log"

# Wait a moment for API to start
sleep 3

# Start Worker service
start_service "Worker" \
    "cd backend && python3 worker.py" \
    "logs/worker.log"

# Start Streamlit UI service
start_service "Streamlit UI" \
    "cd backend && streamlit run pipeline_tester_ui.py --server.port 8501 --server.address 0.0.0.0" \
    "logs/ui.log"

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 5

# Check service status
echo "📊 Service Status:"
echo ""

# Check API
if curl -s "http://localhost:8000/test/health" > /dev/null; then
    echo "  ✅ API: http://localhost:8000 (healthy)"
else
    echo "  ❌ API: http://localhost:8000 (unhealthy)"
fi

# Check Streamlit UI
if curl -s "http://localhost:8501" > /dev/null; then
    echo "  ✅ Streamlit UI: http://localhost:8501"
else
    echo "  ❌ Streamlit UI: http://localhost:8501"
fi

echo ""
echo "🎯 Access URLs (replace localhost with your VM's external IP):"
echo "  📱 Streamlit UI: http://localhost:8501"
echo "  🔌 API Docs: http://localhost:8000/docs"
echo "  🏥 Health Check: http://localhost:8000/test/health"
echo ""
echo "📝 Logs available in logs/ directory:"
echo "  API: logs/api.log"
echo "  Worker: logs/worker.log"
echo "  UI: logs/ui.log"
echo ""
echo "🛑 To stop all services: ./stop_vm_services.sh"
echo ""
echo "✅ Trivia Factory services started successfully!"
