# 🧰 Trivia Factory - End-to-End Pipeline

A complete, low-cost pipeline that generates trivia questions using Gemini AI, stores them in Google Cloud Storage, renders video segments using NVENC on preemptible T4 workers, and provides a Pipeline Tester UI to run/inspect jobs and preview outputs.

## 🎯 Goals & Architecture

- **Single Source of Truth**: GCS-only (no Firestore/Pub/Sub for this phase)
- **Cost Target**: $12–25k/mo @ ~80k videos/day using preemptible GPUs, NVENC, and GCS lifecycle cleanup
- **State Management**: All artifacts stored in GCS with materialized JSON indexes refreshed every 1–5 minutes

## 🏗️ System Components

### 1. Core Pipeline (`src/pipeline.py`)
- Orchestrates the complete workflow from question generation to final video
- Manages job lifecycle and status tracking
- Integrates with GCS for persistent storage

### 2. Gemini AI Integration (`src/gemini_generator.py`)
- Generates diverse trivia questions using Google's Gemini 1.5 Flash
- Supports multiple categories and difficulty levels
- Fallback mechanisms for reliability

### 3. Video Generation (`src/video_generator.py`)
- Integrates with your existing ffmpeg video creation script
- Optimized for NVENC on preemptible T4 workers
- Generates individual clips and concatenates final videos

### 4. Web UI (`src/ui.py`)
- FastAPI-based Pipeline Tester interface
- Real-time job monitoring and status updates
- Asset management and job creation

## 🚀 Quick Start

### Prerequisites
- Google Cloud Project with billing enabled
- Service account with necessary permissions
- Gemini API key
- Docker installed

### 1. Clone and Setup
```bash
git clone <repository-url>
cd trivia-factory
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials and settings
```

### 3. Deploy to Google Cloud
```bash
chmod +x deploy.sh
./deploy.sh
```

### 4. Access the UI
The deployment script will output the service URL. Access it in your browser to start creating trivia video jobs.

## 📁 Project Structure

```
trivia-factory/
├── src/                    # Core Python modules
│   ├── pipeline.py        # Main pipeline orchestrator
│   ├── gemini_generator.py # Gemini AI integration
│   ├── video_generator.py # Video generation logic
│   └── ui.py             # FastAPI web interface
├── config/                # Configuration files
│   └── config.yaml       # Main configuration
├── ui/                    # Web UI assets
│   ├── templates/        # HTML templates
│   └── static/           # CSS, JS, images
├── scripts/               # Utility scripts
├── assets/                # Video templates and fonts
├── output/                # Generated videos
├── Dockerfile            # Container configuration
├── deploy.sh             # Deployment script
└── requirements.txt      # Python dependencies
```

## 🔧 Configuration

### Environment Variables
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account JSON
- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
- `GEMINI_API_KEY`: Gemini AI API key
- `GCS_BUCKET_NAME`: Storage bucket for artifacts

### Video Settings
- **Resolution**: 1920x1080 (configurable)
- **Codec**: NVENC (T4) or libx264 fallback
- **Quality**: Low/Medium/High presets
- **FPS**: 30 (configurable)

## 📊 Pipeline Flow

1. **Question Generation**: Gemini AI creates trivia questions
2. **TTS Generation**: Google Cloud TTS for audio narration
3. **Video Rendering**: Individual clips using ffmpeg + NVENC
4. **Concatenation**: Final video assembly
5. **Storage**: All artifacts saved to GCS with lifecycle policies

## 💰 Cost Optimization

- **Preemptible T4 Workers**: 60-80% cost reduction
- **NVENC Hardware Encoding**: Faster than CPU encoding
- **GCS Lifecycle Policies**: Automatic cleanup of temporary files
- **Auto-scaling**: Scale to zero when not in use

## 🔍 Monitoring & Debugging

- **Real-time UI**: Live job status and progress tracking
- **GCS Logs**: All pipeline artifacts stored with metadata
- **Health Checks**: Automated monitoring and alerting
- **Error Handling**: Comprehensive error tracking and fallbacks

## 🚨 Non-Goals (Future Phases)

- YouTube upload automation
- Editorial CMS
- Multi-tenant authentication
- Advanced analytics dashboard

## 🧪 Testing

### First Test Topology
**First test = API + Worker + UI on the same VM; browser connects to VM ports directly.**

- **Operator (your laptop / Cursor):** Open browser to the VM's UI; click buttons, view status
- **Compute (DEV GPU VM – preemptible T4):** Run **FastAPI (backend)**, **worker**, and **Streamlit UI** on the **same VM**. All rendering happens here. All artifacts go to **GCS**

### Local Development
```bash
# Start the UI locally
python src/ui.py

# Test video generation
python src/video_generator.py

# Run pipeline tests
python -m pytest tests/
```

### Cloud Testing
1. Deploy using `deploy.sh`
2. Create a test job through the UI
3. Monitor progress and check outputs
4. Verify GCS storage and cleanup

## 🔒 Security

- Service account-based authentication
- No hardcoded credentials
- GCS bucket policies for access control
- Secure asset uploads

## 📈 Scaling

- **Horizontal**: Auto-scaling worker pools
- **Vertical**: Configurable instance sizes
- **Storage**: GCS with lifecycle policies
- **CDN**: Cloud CDN for video delivery

## 🆘 Troubleshooting

### Common Issues
1. **NVENC not available**: Falls back to CPU encoding
2. **GCS permissions**: Check service account roles
3. **Gemini API limits**: Implement rate limiting
4. **Video generation failures**: Check ffmpeg installation

### Debug Commands
```bash
# Check GPU availability
nvidia-smi

# Verify ffmpeg
ffmpeg -version

# Test GCS access
gsutil ls gs://your-bucket

# Check service logs
gcloud logging read "resource.type=cloud_run_revision"
```

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review GCS logs and pipeline status
3. Verify configuration and permissions
4. Check GPU availability and ffmpeg installation

## 🔄 Updates

- **Pipeline**: `git pull && ./deploy.sh`
- **Assets**: Upload new templates via UI
- **Configuration**: Update `config/config.yaml`
- **Dependencies**: Update `requirements.txt`

---

**Built for Google Cloud with ❤️ and NVENC acceleration**
