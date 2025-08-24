#!/bin/bash

# Initialize Git repository for Trivia Factory
# This script sets up the Git repository with proper structure

echo "🚀 Initializing Trivia Factory Git Repository"
echo "============================================="

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "❌ Git not found. Please install Git first."
    echo "   Ubuntu/Debian: sudo apt-get install git"
    echo "   macOS: brew install git"
    exit 1
fi

# Initialize Git repository
if [ ! -d ".git" ]; then
    echo "📁 Initializing Git repository..."
    git init
    echo "✅ Git repository initialized"
else
    echo "ℹ️  Git repository already exists"
fi

# Add all files
echo "📝 Adding files to Git..."
git add .

# Create initial commit
echo "💾 Creating initial commit..."
git commit -m "🎉 Initial commit: Complete Trivia Factory pipeline

- Backend: FastAPI pipeline with Gemini AI integration
- Frontend: React dashboard with Material-UI
- Video processing: NVENC-optimized pipeline
- Infrastructure: GCS + preemptible T4 workers
- Documentation: Complete setup and deployment guides"

echo ""
echo "�� Repository setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Add remote origin: git remote add origin <your-repo-url>"
echo "2. Push to remote: git push -u origin main"
echo "3. Set up development environment: ./dev.sh setup"
echo "4. Start development servers: ./dev.sh start"
echo ""
echo "📚 Available commands:"
echo "  ./dev.sh setup     - Setup development environment"
echo "  ./dev.sh start     - Start development servers"
echo "  ./dev.sh stop      - Stop development servers"
echo "  ./dev.sh restart   - Restart development servers"
echo ""
echo "🌐 Access points:"
echo "  Frontend: http://localhost:3000"
echo "  Backend API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
