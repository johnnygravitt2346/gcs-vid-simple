# 🚀 Complete Cloud Pipeline: Gemini → Video Generation

A production-ready, cloud-native pipeline that generates trivia videos from Gemini AI with scalable GPU rendering. **Everything streams from GCS - no local dependencies!**

## 🏗️ Architecture Overview

```
Gemini AI → GCS Storage → Cloud GPU Workers → Final Video
    ↓           ↓            ↓              ↓
Trivia Gen   CSV Files   Stream Assets   MP4 Output
```

## 🔑 Key Features

✅ **100% Cloud-Native**: All assets stream from GCS, no local file dependencies  
✅ **Gemini AI Integration**: Automated trivia generation with GCS persistence  
✅ **GPU Acceleration**: NVIDIA T4 with NVENC encoding for fast rendering  
✅ **GCS Streaming**: Assets processed directly from cloud storage  
✅ **Scalable**: Designed for 80,000+ videos per day  
✅ **Production Ready**: Job management, checkpoints, and monitoring  

## 📁 Pipeline Components

### 1. **Gemini Feeder** (`core/gemini_feeder.py`)
- Generates trivia questions using Gemini AI
- Saves output to GCS for persistence
- Configurable topics, difficulty, and question count

### 2. **Cloud Video Generator** (`core/cloud_video_generator.py`)
- **Uses exact same logic** as your working local version
- Streams all assets from GCS (no downloads)
- Optimized for cloud GPU workers
- NVIDIA GPU acceleration with NVENC

### 3. **Complete Pipeline** (`examples/complete_cloud_pipeline.py`)
- Orchestrates entire flow from start to finish
- Creates job manifests and tracks progress
- Handles GCS bucket management

## 🚀 Quick Start

### Prerequisites

1. **Google Cloud Project** with billing enabled
2. **Gemini API Key** for trivia generation
3. **Service Account** with GCS permissions
4. **FFmpeg** with NVIDIA GPU support

### Environment Setup

```bash
# Set your credentials
export GEMINI_API_KEY="your-gemini-api-key"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"

# Install dependencies
cd production-pipeline/core
pip install -r requirements.txt
```

### Test Components

```bash
# Test all pipeline components
cd production-pipeline/examples
python3 test_cloud_pipeline.py
```

### Run Complete Pipeline

```bash
# Run the full pipeline
cd production-pipeline/examples
python3 complete_cloud_pipeline.py
```

## 🔧 How It Works

### Step 1: Gemini Generates Trivia
```python
feeder = GeminiFeeder(api_key=GEMINI_API_KEY)
trivia_data = await feeder.generate_dataset(request)
```

### Step 2: Save to GCS
```python
# CSV saved to: gs://trivia-automation/jobs/channel-test/job-001/questions.csv
csv_path = save_trivia_to_gcs(trivia_data, job_path)
```

### Step 3: Cloud Video Generation
```python
# All assets stream from GCS - no downloads!
job_info = JobInfo(
    gcs_csv_path="gs://bucket/path/questions.csv",
    output_path="gs://bucket/final_videos/job-001.mp4"
)
output_path = process_job(job_info)
```

## 🎬 GCS Streaming Assets

The video generator streams these assets directly from GCS:

- **Video Templates**: `gs://trivia-automations-2/channel-test/video-assets/1.mp4`
- **Timer Assets**: `gs://trivia-automations-2/channel-test/video-assets/slide_timer_bar_5s.mp4`
- **Audio Effects**: `gs://trivia-automations-2/channel-test/video-assets/ding_correct_answer_long.wav`
- **Trivia Data**: `gs://trivia-automation/jobs/channel-test/job-001/questions.csv`

## 🖥️ GPU Worker Deployment

### Local Testing
```bash
# Test on your local machine (if you have NVIDIA GPU)
python3 complete_cloud_pipeline.py
```

### Cloud Deployment
```bash
# Deploy to Google Cloud GPU workers
cd production-pipeline/cloud-infrastructure
./deploy_infrastructure.sh
```

## 📊 Job Structure

Each job creates this GCS structure:
```
gs://trivia-automation/
├── jobs/
│   └── channel-test/
│       └── 20250825-143022/          # Job ID (timestamp)
│           ├── questions.csv          # Gemini-generated trivia
│           └── _MANIFEST.json        # Job metadata
└── final_videos/
    └── channel-test/
        └── 20250825-143022/
            └── final_video.mp4       # Generated video
```

## 🔍 Monitoring & Debugging

### Check Job Status
```bash
# View job manifest
gsutil cat gs://trivia-automation/jobs/channel-test/job-001/_MANIFEST.json
```

### View Generated Video
```bash
# Download final video
gsutil cp gs://trivia-automation/final_videos/channel-test/job-001/final_video.mp4 ./
```

### Check GCS Assets
```bash
# List available video assets
gsutil ls gs://trivia-automations-2/channel-test/video-assets/
```

## 🚨 Important Notes

### GCS Streaming vs Downloading
- **Assets stream directly** from GCS during processing
- **No local storage** required for video templates
- **CSV data read** directly from GCS bucket
- **Temporary files** only for TTS audio (small, cleaned up)

### Performance Considerations
- **Network latency** affects streaming performance
- **Large video files** (1.mp4, 2.mp4, 3.mp4) stream during processing
- **Audio files** are small and stream quickly
- **GPU acceleration** minimizes processing time

### Error Handling
- **GCS connection failures** are handled gracefully
- **Asset streaming errors** trigger retry logic
- **Job manifests** track progress and failures
- **Cleanup** removes temporary files on completion

## 🧪 Testing

### Component Tests
```bash
# Test individual components
python3 test_cloud_pipeline.py
```

### Integration Tests
```bash
# Test complete pipeline
python3 complete_cloud_pipeline.py
```

### Production Tests
```bash
# Test on cloud GPU workers
# (Deploy infrastructure first)
```

## 🔮 Future Enhancements

- **Multi-GPU support** per worker instance
- **Advanced job scheduling** with priority queues
- **Real-time monitoring** dashboard
- **Cost optimization** with spot instances
- **Custom video formats** and resolutions

## 📚 Related Documentation

- **Core Components**: See `core/` directory
- **Cloud Infrastructure**: See `cloud-infrastructure/` directory
- **Examples**: See `examples/` directory
- **Main Pipeline**: See `README.md`

---

**Ready for production-scale trivia video generation!** 🎬✨

The pipeline maintains the exact same video generation logic as your working local version while making it completely cloud-native with GCS streaming.
