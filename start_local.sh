#!/bin/bash

# Trivia Factory Local Development Startup Script

echo "🚀 Starting Trivia Factory locally..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if assets directory has required files
if [ ! -f "assets/1.mp4" ] || [ ! -f "assets/2.mp4" ] || [ ! -f "assets/3.mp4" ]; then
    echo "⚠️  Warning: Missing video template files in assets/ directory"
    echo "   Expected: 1.mp4, 2.mp4, 3.mp4"
    echo "   Please add your video templates to continue"
fi

# Check if font files exist
if [ ! -f "assets/font.ttf" ]; then
    echo "⚠️  Warning: No font file found in assets/ directory"
    echo "   Please add a .ttf font file for text rendering"
fi

# Set environment variables for local development
export GOOGLE_CLOUD_PROJECT="mythic-groove-469801-b7"
export ASSETS_DIR="./assets"
export TESTING_MODE="1"  # Use silent audio for local testing

echo "🌐 Starting FastAPI server..."
echo "   UI will be available at: http://localhost:8080"
echo "   API docs at: http://localhost:8080/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the FastAPI server
python src/ui.py
