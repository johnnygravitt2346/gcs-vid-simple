#!/bin/bash

# 🚀 Quick Start Web Interface
# Simple script to start the web interface

echo "🌐 Starting GCS Video Automation Web Interface..."

# Check if virtual environment exists
if [ ! -d "venv_web" ]; then
    echo "📦 Virtual environment not found. Running full deployment..."
    ./deploy_web_interface.sh
else
    echo "🔧 Activating existing virtual environment..."
    source venv_web/bin/activate
    
    echo "🚀 Starting web interface..."
    echo "🌐 Access at: http://localhost:5000"
    echo "📱 Network access: http://$(ifconfig | grep 'inet ' | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1):5000"
    echo ""
    echo "Press Ctrl+C to stop"
    
    python web_interface.py
fi
