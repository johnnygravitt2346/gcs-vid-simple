# 🚀 Trivia Factory - Complete Setup Guide

## 📋 Prerequisites

- Python 3.9+
- Node.js 16+ (for frontend)
- Git
- FFmpeg
- Google Cloud account with billing enabled

## 🏗️ Project Structure

```
trivia-factory/
├── backend/                 # Python FastAPI backend
│   ├── src/                # Core modules
│   ├── config/             # Configuration files
│   ├── scripts/            # Utility scripts
│   └── requirements.txt    # Python dependencies
├── frontend/                # React dashboard
│   ├── src/                # React components
│   ├── public/             # Static assets
│   └── package.json        # Node dependencies
├── assets/                  # Video templates, fonts, etc.
├── docs/                    # Documentation
├── tests/                   # Test suite
└── docker/                  # Docker configurations
```

## 🚀 Quick Start (5 minutes)

### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/trivia-factory.git
cd trivia-factory
```

### 2. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
```

### 4. Environment Configuration
```bash
cd ../backend
cp .env.example .env
# Edit .env with your API keys and settings
```

### 5. Start Services
```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm start
```

### 6. Access Dashboard
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🔧 Detailed Setup

### Backend Dependencies
```bash
# Core
pip install fastapi uvicorn google-cloud-storage google-cloud-aiplatform

# Video processing
pip install opencv-python Pillow numpy

# Utilities
pip install pydantic python-dotenv requests aiofiles

# Development
pip install pytest black flake8
```

### Frontend Dependencies
```bash
npm install react react-dom react-router-dom
npm install @mui/material @emotion/react @emotion/styled
npm install axios recharts
npm install --save-dev @types/react @types/node
```

### Environment Variables
```bash
# Backend (.env)
GOOGLE_APPLICATION_CREDENTIALS=./gcp_service_account.json
GOOGLE_CLOUD_PROJECT=your-project-id
GEMINI_API_KEY=your_gemini_api_key
GCS_BUCKET_NAME=trivia-factory-prod

# Frontend (.env.local)
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=development
```

## 🧪 Testing Your Setup

### 1. Backend Health Check
```bash
curl http://localhost:8000/api/health
# Expected: {"status": "healthy", "timestamp": "..."}
```

### 2. Frontend Build Test
```bash
cd frontend
npm run build
# Should complete without errors
```

### 3. Integration Test
```bash
cd backend
pytest tests/ -v
# Should run all tests successfully
```

### 4. End-to-End Test
1. Open http://localhost:3000
2. Create a test trivia job
3. Monitor progress in real-time
4. Verify outputs are generated

## 🐳 Docker Development

### Backend Container
```bash
cd backend
docker build -t trivia-backend .
docker run -p 8000:8000 trivia-backend
```

### Frontend Container
```bash
cd frontend
docker build -t trivia-frontend .
docker run -p 3000:3000 trivia-frontend
```

### Full Stack with Docker Compose
```bash
docker-compose up --build
```

## 🔍 Troubleshooting

### Common Issues

#### Backend Won't Start
```bash
# Check Python version
python3 --version  # Should be 3.9+

# Check virtual environment
which python  # Should point to venv/bin/python

# Check dependencies
pip list | grep fastapi
```

#### Frontend Build Fails
```bash
# Clear node modules
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 16+
```

#### API Connection Issues
```bash
# Check CORS settings in backend
# Verify API URL in frontend
# Check network tab in browser dev tools
```

#### Video Generation Fails
```bash
# Check FFmpeg installation
ffmpeg -version

# Verify asset paths
ls -la assets/

# Check permissions
chmod +x scripts/*.py
```

### Debug Mode
```bash
# Backend debug
export DEBUG=1
uvicorn src.main:app --reload --log-level debug

# Frontend debug
export REACT_APP_DEBUG=true
npm start
```

## 📚 Development Workflow

### 1. Feature Development
```bash
git checkout -b feature/new-feature
# Make changes
npm run test  # Frontend tests
pytest        # Backend tests
git commit -m "Add new feature"
git push origin feature/new-feature
```

### 2. Testing
```bash
# Run all tests
npm run test:all  # Frontend
pytest            # Backend

# Run specific tests
pytest tests/test_pipeline.py -v
npm run test -- --testNamePattern="job creation"
```

### 3. Code Quality
```bash
# Format code
black src/
npm run format

# Lint code
flake8 src/
npm run lint
```

## 🚀 Production Deployment

### Google Cloud Run
```bash
# Deploy backend
gcloud run deploy trivia-backend --source backend/

# Deploy frontend
gcloud run deploy trivia-frontend --source frontend/
```

### Docker Registry
```bash
# Build and push images
docker build -t gcr.io/PROJECT_ID/trivia-backend backend/
docker push gcr.io/PROJECT_ID/trivia-backend
```

## 📖 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://reactjs.org/docs/)
- [Google Cloud Documentation](https://cloud.google.com/docs)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)

## 🆘 Getting Help

1. Check the troubleshooting section above
2. Review logs in browser dev tools and terminal
3. Check GitHub Issues for known problems
4. Create a new issue with detailed error information

---

**Happy coding! 🎉**
