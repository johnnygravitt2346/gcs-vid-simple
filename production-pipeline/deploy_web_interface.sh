#!/bin/bash

# 🚀 Deploy Web Interface for GCS Video Automations
# This script sets up and runs the web interface

echo "🚀 Deploying GCS Video Automation Web Interface..."

# Check if we're in the right directory
if [ ! -f "web_interface.py" ]; then
    echo "❌ Error: Please run this script from the production-pipeline directory"
    exit 1
fi

# Check environment variables
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  Warning: GEMINI_API_KEY is not set. Gemini mode will be disabled until you set it."
fi

if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "❌ Error: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set"
    echo "Set it with: export GOOGLE_APPLICATION_CREDENTIALS='path/to/credentials.json'"
    exit 1
fi

echo "✅ Environment variables configured"

# Create virtual environment if it doesn't exist
if [ ! -d "venv_web" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv_web
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv_web/bin/activate

# Install requirements
echo "📥 Installing requirements..."
pip install -r requirements_web.txt

# Create templates directory if it doesn't exist
if [ ! -d "templates" ]; then
    echo "📁 Creating templates directory..."
    mkdir -p templates
fi

# Check if template exists
if [ ! -f "templates/index.html" ]; then
    echo "❌ Error: templates/index.html not found"
    echo "Please ensure the HTML template is in place"
    exit 1
fi

echo "✅ All dependencies installed and configured"

# Get local IP address for network access
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)

if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="localhost"
fi

echo ""
echo "🌐 Web Interface Ready!"
echo "========================"
echo "Local access: http://localhost:5000"
echo "Network access: http://$LOCAL_IP:5000"
echo ""
echo "📱 You can now access this from any computer on your network!"
echo "🌍 To make it accessible from the internet, you'll need to:"
echo "   1. Configure your router's port forwarding (port 5000)"
echo "   2. Use a service like ngrok: ngrok http 5000"
echo "   3. Deploy to Google Cloud Run or similar service"
echo ""
echo "🚀 Starting web interface..."
echo "Press Ctrl+C to stop"

# Start the web interface
python web_interface.py
