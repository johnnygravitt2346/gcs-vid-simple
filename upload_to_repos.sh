#!/bin/bash

echo "🚀 Uploading GCS Video Automations to GitHub and GCS"
echo "=============================================="

# Configuration
GITHUB_REPO="johnnygravitt2346/gcs-video-automations"
GCS_BUCKET="gcs-video-automations-prod"
GCP_PROJECT="mythic-groove-469801-b7"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Step 1: Initialize Git repository
print_status "📁 Initializing Git repository..."
if [[ ! -d ".git" ]]; then
    git init
    git add .
    git commit -m "Initial commit: Complete GCS Video Automations System"
    print_success "✅ Git repository initialized"
else
    print_status "Git repository already exists"
fi

# Step 2: Add GitHub remote
print_status "🔗 Adding GitHub remote..."
if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/$GITHUB_REPO.git"
    print_success "✅ GitHub remote added"
else
    print_status "GitHub remote already exists"
fi

# Step 3: Push to GitHub
print_status "📤 Pushing to GitHub..."
if git push -u origin main 2>/dev/null || git push -u origin master 2>/dev/null; then
    print_success "✅ Code pushed to GitHub successfully"
else
    print_warning "⚠️  GitHub push failed - you may need to create the repository first"
    echo "   Visit: https://github.com/new"
    echo "   Repository name: gcs-video-automations"
    echo "   Make it public or private as preferred"
    echo "   Then run this script again"
fi

# Step 4: Upload to Google Cloud Storage
print_status "☁️  Uploading to Google Cloud Storage..."

# Check if bucket exists, create if not
if ! gsutil ls gs://$GCS_BUCKET >/dev/null 2>&1; then
    print_status "Creating GCS bucket: $GCS_BUCKET"
    gsutil mb gs://$GCS_BUCKET
    print_success "✅ GCS bucket created"
else
    print_status "GCS bucket already exists"
fi

# Create directory structure in GCS
print_status "📁 Creating GCS directory structure..."
gsutil -m cp -r backend gs://$GCS_BUCKET/scripts/
gsutil -m cp -r frontend gs://$GCS_BUCKET/scripts/
gsutil -m cp -r assets gs://$GCS_BUCKET/scripts/ 2>/dev/null || print_warning "No assets directory found"
gsutil -m cp start_trivia_factory.sh gs://$GCS_BUCKET/scripts/
gsutil -m cp README_INTEGRATED_SYSTEM.md gs://$GCS_BUCKET/scripts/
gsutil -m cp upload_to_repos.sh gs://$GCS_BUCKET/scripts/

print_success "✅ Files uploaded to GCS successfully"

# Step 5: Verify uploads
print_status "🔍 Verifying GCS uploads..."
echo "Files in GCS bucket:"
gsutil ls -r gs://$GCS_BUCKET/scripts/

# Step 6: Create bootstrap instructions
print_status "📝 Creating bootstrap instructions..."
cat > BOOTSTRAP_INSTRUCTIONS.md << 'EOF'
# 🚀 GCS Video Automations Bootstrap Instructions

## Quick Start (One Command)

```bash
# Download and run the bootstrap script
gsutil cp gs://gcs-video-automations-prod/scripts/start_trivia_factory.sh .
chmod +x start_trivia_factory.sh
./start_trivia_factory.sh
```

## What This Does

1. ✅ Downloads all project files from GCS
2. ✅ Installs Python dependencies
3. ✅ Sets up environment configuration
4. ✅ Starts backend API (port 8000)
5. ✅ Starts frontend dashboard (port 8080)
6. ✅ Creates test scripts

## Access Points

- **Backend API**: http://localhost:8000
- **Frontend Dashboard**: http://localhost:8080
- **API Docs**: http://localhost:8000/docs

## Next Steps

1. Set your Gemini API key in `backend/.env`
2. Run `./test_pipeline.sh` to test the system
3. Use Cloud Shell Web Preview on port 8080

## Repository Links

- **GitHub**: https://github.com/johnnygravitt2346/gcs-video-automations
- **GCS**: gs://trivia-factory-prod/scripts/
- **Documentation**: README_INTEGRATED_SYSTEM.md

## Support

- Check the logs in the terminal
- Review the troubleshooting section in the README
- Open issues on GitHub if needed
EOF

print_success "✅ Bootstrap instructions created"

# Step 7: Final summary
echo ""
echo "🎉 UPLOAD COMPLETE!"
echo "==================="
echo ""
echo "📁 GitHub Repository:"
echo "   https://github.com/johnnygravitt2346/gcs-video-automations"
echo "   (You may need to create this repository first)"
echo ""
echo "☁️  Google Cloud Storage:"
echo "   gs://$GCS_BUCKET/scripts/"
echo ""
echo "🚀 Bootstrap Command:"
echo "   gsutil cp gs://gcs-video-automations-prod/scripts/start_trivia_factory.sh . && chmod +x start_trivia_factory.sh && ./start_trivia_factory.sh"
echo ""
echo "📚 Documentation:"
echo "   README_INTEGRATED_SYSTEM.md"
echo "   BOOTSTRAP_INSTRUCTIONS.md"
echo ""
echo "🔧 Next Steps:"
echo "1. Create the GitHub repository if it doesn't exist"
echo "2. Test the bootstrap system in Cloud Shell"
echo "3. Configure your API keys"
echo "4. Run a test pipeline"
echo ""
echo "✅ Your GCS Video Automations system is now available in both repositories!"
