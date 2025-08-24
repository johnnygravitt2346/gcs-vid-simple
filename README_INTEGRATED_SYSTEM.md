# 🧰 GCS Video Automations - Complete Integrated System

A fully integrated AI-powered trivia video generation system that combines Gemini AI question generation with automated video creation, all running in Google Cloud environments.

## 🚀 Features

- **🤖 Gemini AI Integration**: Automatically generates engaging trivia questions
- **🎥 Automated Video Creation**: Creates professional video clips from questions
- **☁️ Google Cloud Native**: Built for Cloud Shell, Cloud Run, and GCS
- **🔧 One-Command Bootstrap**: Complete system setup with a single script
- **📊 Real-time Dashboard**: Web interface for monitoring and control
- **🔄 Complete Pipeline**: From question generation to final video output

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API    │    │   Video Gen     │
│   Dashboard     │◄──►│   FastAPI        │◄──►│   FFmpeg        │
│   (Port 8080)   │    │   (Port 8000)    │    │   Pipeline      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Gemini AI      │
                       │   Question Gen   │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Google Cloud   │
                       │   Storage (GCS)  │
                       └──────────────────┘
```

## 📁 Project Structure

```
trivia-factory/
├── backend/
│   ├── src/
│   │   ├── main.py                 # FastAPI backend server
│   │   ├── gemini_generator.py     # Gemini AI integration
│   │   ├── pipeline.py             # Pipeline orchestration
│   │   └── video_generator.py      # Video generation logic
│   ├── scripts/
│   │   ├── run_trivia_pipeline.py  # Main pipeline runner
│   │   └── trivia_video_generator.py # Video creation script
│   ├── config/
│   │   └── pipeline_config.json    # Configuration file
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── index.html                  # Dashboard interface
│   └── package.json                # Frontend configuration
├── assets/                         # Video templates and assets
├── start_trivia_factory.sh         # One-command bootstrap
└── test_pipeline.sh                # Pipeline testing script
```

## 🚀 Quick Start

### 1. Bootstrap the Complete System

```bash
# Download and run the bootstrap script
gsutil cp gs://trivia-factory-prod/scripts/start_trivia_factory.sh .
chmod +x start_trivia_factory.sh
./start_trivia_factory.sh
```

### 2. Configure API Keys

Edit `backend/.env`:
```bash
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 3. Test the Pipeline

```bash
./test_pipeline.sh
```

### 4. Access the Dashboard

- **Backend API**: http://localhost:8000
- **Frontend Dashboard**: http://localhost:8080
- **API Documentation**: http://localhost:8000/docs

## 🔧 Manual Setup (Alternative)

### Prerequisites

- Python 3.8+
- FFmpeg and FFprobe
- Google Cloud SDK
- Gemini AI API key

### Installation

```bash
# Clone the repository
git clone https://github.com/johnnygravitt2346/gcs-video-automations.git
cd gcs-video-automations

# Install Python dependencies
pip install -r backend/requirements.txt

# Set up environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys
```

## 📖 Usage

### Running the Complete Pipeline

```bash
cd backend
python3 scripts/run_trivia_pipeline.py \
  --topic "Space Exploration" \
  --difficulty "Medium" \
  --count 5 \
  --category "Science"
```

### API Endpoints

- `GET /api/health` - Health check
- `GET /api/jobs` - List all jobs
- `POST /api/jobs` - Create new job
- `GET /api/jobs/{job_id}` - Get job status
- `GET /api/stats` - System statistics

### Configuration Options

Edit `backend/config/pipeline_config.json`:

```json
{
  "gemini_api_key": "your_key_here",
  "gcp_project_id": "your-project-id",
  "gcs_bucket": "your-bucket-name",
  "video_quality": "medium",
  "video_fps": 30,
  "tts": {
    "voice": "en-US-Neural2-F",
    "speed": 1.0
  }
}
```

## 🎥 Video Generation

The system automatically:

1. **Generates Questions**: Uses Gemini AI to create engaging trivia
2. **Creates Video Clips**: Generates individual question/answer clips
3. **Adds TTS Audio**: Text-to-speech for questions and answers
4. **Applies Templates**: Uses video templates for consistent styling
5. **Concatenates**: Combines all clips into final video
6. **Uploads to GCS**: Stores results in Google Cloud Storage

### Video Templates Required

- `1.mp4` - Entrance slide
- `2.mp4` - Bridge/question slide  
- `3.mp4` - Answer slide

### Output Structure

```
output/
├── questions/
│   └── pipeline_1234567890_questions.json
├── videos/
│   └── pipeline_1234567890/
│       ├── clip_001/
│       ├── clip_002/
│       └── final_video.mp4
└── pipeline_1234567890_results.json
```

## 🔒 Security & Configuration

### Environment Variables

- `GEMINI_API_KEY` - Your Gemini AI API key
- `GOOGLE_APPLICATION_CREDENTIALS` - GCP service account JSON
- `GCP_PROJECT_ID` - Google Cloud project ID
- `GCS_BUCKET` - Google Cloud Storage bucket name

### Service Account Permissions

Your GCP service account needs:
- Cloud Storage Admin
- AI Platform Developer
- Text-to-Speech Admin

## 🧪 Testing

### Test the Complete Pipeline

```bash
# Run the test script
./test_pipeline.sh

# Or test manually
cd backend
python3 scripts/run_trivia_pipeline.py \
  --topic "Test Topic" \
  --difficulty "Easy" \
  --count 2
```

### Expected Output

```
🧪 Testing Trivia Factory Pipeline...
=====================================
✅ All required files found
🚀 Testing pipeline with 'Space Exploration' topic...
🧪 Test completed!
```

## 🚀 Deployment

### Cloud Shell (Development)

```bash
./start_trivia_factory.sh
```

### Cloud Run (Production)

```bash
# Build and deploy
gcloud run deploy trivia-factory \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Docker

```bash
# Build image
docker build -t trivia-factory .

# Run container
docker run -p 8000:8000 trivia-factory
```

## 🔍 Troubleshooting

### Common Issues

1. **Gemini API Key Missing**
   ```bash
   # Set in backend/.env
   GEMINI_API_KEY=your_key_here
   ```

2. **FFmpeg Not Found**
   ```bash
   # Install FFmpeg
   sudo apt-get update && sudo apt-get install ffmpeg
   ```

3. **Port Already in Use**
   ```bash
   # Check what's using the port
   netstat -tlnp | grep :8000
   
   # Kill the process
   kill -9 <PID>
   ```

4. **GCS Upload Failed**
   ```bash
   # Check credentials
   gcloud auth application-default login
   
   # Verify bucket exists
   gsutil ls gs://your-bucket-name
   ```

### Logs

- **Backend**: Check terminal output for FastAPI logs
- **Frontend**: Check browser console for JavaScript errors
- **Pipeline**: Check `output/` directory for result files

## 📚 API Reference

### Question Generation

```python
from src.gemini_generator import GeminiQuestionGenerator

generator = GeminiQuestionGenerator(api_key, project_id)
questions = await generator.generate_questions(request)
```

### Video Generation

```python
from src.video_generator import VideoGenerator

generator = VideoGenerator(config)
clips = await generator.generate_videos(request)
```

### Pipeline Runner

```python
from scripts.run_trivia_pipeline import TriviaPipelineRunner

runner = TriviaPipelineRunner(config)
results = await runner.run_pipeline(topic, difficulty, count, category)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: This README
- **Examples**: Check the `examples/` directory

## 🎯 Roadmap

- [ ] Multi-language support
- [ ] Advanced video effects
- [ ] Real-time collaboration
- [ ] Mobile app
- [ ] Analytics dashboard
- [ ] A/B testing for questions

---

**Built with ❤️ for the Google Cloud community**
