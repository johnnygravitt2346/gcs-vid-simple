# 🔧 Technical Pipeline Specification: GCS Video Automation V2.0

## 📋 Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Pipeline Flow & Data Movement](#pipeline-flow--data-movement)
3. [Component Breakdown](#component-breakdown)
4. [Data Structures & APIs](#data-structures--apis)
5. [Infrastructure & Deployment](#infrastructure--deployment)
6. [Error Handling & Monitoring](#error-handling--monitoring)
7. [Performance Characteristics](#performance-characteristics)
8. [Next Steps & Recommendations](#next-steps--recommendations)

---

## 🏗️ System Architecture Overview

### High-Level Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Interface │    │  Gemini AI API   │    │  GCS Storage    │
│   (Flask/HTML)  │◄──►│   (Question Gen) │◄──►│  (Asset Mgmt)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Video Pipeline │    │   TTS Service    │    │  Output Videos  │
│  (FFmpeg/Cloud) │◄──►│  (Google Cloud)  │◄──►│  (GCS Buckets)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Technology Stack
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla + Socket.IO)
- **Backend**: Python 3.8+, Flask, Flask-SocketIO
- **AI/ML**: Google Gemini AI API (gemini-1.5-flash)
- **Cloud**: Google Cloud Platform (GCS, TTS, Compute)
- **Video Processing**: FFmpeg (libx264, aac codecs)
- **Infrastructure**: Docker, Cloud Build, Auto-scaling

---

## 🔄 Pipeline Flow & Data Movement

### 1. User Request Phase
```
User Input → Web Form → Flask Route → Job Creation → Background Thread
```

**Detailed Flow:**
1. User selects category, number of questions, channel
2. Frontend sends POST to `/generate` endpoint
3. Flask creates unique job ID and stores in `active_jobs` dict
4. Spawns background thread for `run_generation_pipeline()`
5. Returns job ID to frontend for progress tracking

**Key Data:**
- `job_id`: `web-{YYYYMMDD-HHMMSS}` format
- `category`: User-selected trivia type (sports, science, etc.)
- `num_questions`: Integer 1-10
- `channel_id`: GCS bucket organization identifier

### 2. Question Generation Phase
```
Gemini API → Prompt Engineering → Response Parsing → Validation → CSV Storage
```

**Detailed Flow:**
1. **Prompt Construction**: Category-specific prompts from `prompt_presets`
2. **Gemini Call**: Async API call with structured prompt
3. **Response Parsing**: JSON extraction and question object creation
4. **Validation**: Content length, format, answer distribution checks
5. **Deduplication**: Hash-based duplicate removal
6. **CSV Storage**: Questions saved to GCS under `{channel_id}/feeds/`

**Example Prompt for Sports:**
```python
"Generate {count} engaging sports trivia questions. Focus on popular sports like football, basketball, baseball, soccer, tennis, and Olympic sports. Include questions about famous athletes, historical events, rules, and records."
```

### 3. Video Generation Phase
```
Template Selection → TTS Generation → Video Composition → Concatenation → Upload
```

**Detailed Flow:**
1. **Asset Resolution**: Download/cache video templates from GCS
2. **TTS Generation**: Google Cloud TTS for each question/answer
3. **Video Composition**: FFmpeg overlays with text, timers, effects
4. **Individual Clips**: Question + Answer pairs as separate videos
5. **Final Assembly**: Concatenate intro + clips + outro
6. **Upload**: Final video to GCS `final_videos/{channel_id}/{job_id}/`

**Video Processing Pipeline:**
```
Template Video → Text Overlay → Timer Animation → Audio Mix → Export
     ↓              ↓            ↓            ↓         ↓
  1.mp4/3.mp4   drawtext    overlay     amix    H.264/AAC
```

### 4. Web Interface Updates
```
Progress Events → Socket.IO → Real-time Updates → Video Display
```

**Detailed Flow:**
1. **Progress Tracking**: 10% → 100% with detailed step descriptions
2. **Socket Events**: `job_update` events for real-time communication
3. **Frontend Updates**: Progress bars, status text, video players
4. **Completion**: Final video URL generation and display

---

## 🧩 Component Breakdown

### Core Modules

#### 1. `web_interface.py` - Main Server
**Purpose**: Flask application with Socket.IO for real-time communication
**Key Functions:**
- `start_generation()`: Entry point for video generation requests
- `run_generation_pipeline()`: Background processing orchestration
- `continue_video_generation()`: Video pipeline execution
- Socket event handlers for progress updates

**Dependencies:**
```python
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from core.gemini_feeder_fixed import GeminiFeederFixed, FeederRequest
from core.cloud_video_generator_fixed import JobInfo, process_job
```

#### 2. `gemini_feeder_fixed.py` - AI Question Generator
**Purpose**: Generates trivia questions using Gemini AI with category-specific prompts
**Key Functions:**
- `generate_dataset()`: Main generation with retry logic
- `_generate_questions()`: Gemini API calls
- `_build_enhanced_gemini_prompt()`: Category-specific prompt construction
- `_validate_questions()`: Content validation and filtering

**Prompt Presets Structure:**
```python
self.prompt_presets = {
    "sports": {"prompt": "Generate {count} engaging sports trivia questions..."},
    "science": {"prompt": "Generate {count} engaging science trivia questions..."},
    # ... 16 total categories
}
```

#### 3. `cloud_video_generator_fixed.py` - Video Processing Engine
**Purpose**: Handles all video generation, composition, and encoding
**Key Functions:**
- `build_question_clip()`: Creates question videos with text overlays
- `build_answer_clip()`: Creates answer videos with correct answer display
- `concat_many_ordered()`: Assembles final video from components
- `make_intro_outro()`: Generates intro/outro sequences

**Video Specifications:**
- **Resolution**: 1920x1080 (16:9 aspect ratio)
- **Frame Rate**: 30 fps
- **Codec**: H.264 (libx264) with AAC audio
- **Quality**: CRF 23, 3Mbps target, 5Mbps max

#### 4. `asset_resolver.py` - Asset Management
**Purpose**: Manages GCS asset downloads, caching, and path resolution
**Key Functions:**
- `get_asset_path()`: Resolves asset paths with local caching
- `download_gcs_asset()`: Downloads large assets to local cache
- `preflight_validate()`: Checks asset availability before processing

#### 5. `path_resolver.py` - GCS Path Management
**Purpose**: Provides consistent GCS path structures across the system
**Key Functions:**
- `assets_root_uri()`: Base path for video templates and assets
- `feeds_csv_input_uri()`: Path for input CSV files
- `outputs_final_uri()`: Path for final video outputs

### Frontend Components

#### 1. `templates/index.html` - User Interface
**Purpose**: Main web interface for video generation
**Key Features:**
- Category selection dropdown (16 options)
- Question quantity selection (1-10)
- Real-time progress updates
- Video player for final output
- Socket.IO integration for live updates

**JavaScript Functions:**
- `startGeneration()`: Initiates video generation
- `showVideoOutputs()`: Displays completed videos
- Socket event handlers for progress tracking

#### 2. Socket.IO Integration
**Purpose**: Real-time communication between backend and frontend
**Event Flow:**
```
Backend → Frontend: job_update (progress, status, current_step)
Frontend → Backend: approve_questions, regenerate_questions
```

---

## 📊 Data Structures & APIs

### Core Data Models

#### 1. `FeederRequest` Dataclass
```python
@dataclass
class FeederRequest:
    channel_id: str                    # GCS channel identifier
    prompt_preset: str                 # Category (sports, science, etc.)
    quantity: int                      # Number of questions (1-10)
    tags: Optional[List[str]]          # Optional topic tags
    banned_topics: Optional[List[str]] # Content restrictions
    banned_terms: Optional[List[str]]  # Term restrictions
    max_question_length: int           # Character limit (default: 200)
    max_option_length: int             # Option limit (default: 100)
    answer_distribution_tolerance: int # Answer balance tolerance
    language_filter: str               # Language code (default: "en")
    difficulty: str                    # Difficulty level (default: "medium")
    style: str                         # Question style (default: "engaging")
```

#### 2. `TriviaQuestion` Dataclass
```python
@dataclass
class TriviaQuestion:
    qid: str                           # Unique question identifier
    question: str                      # Question text
    option_a: str                      # Option A text
    option_b: str                      # Option B text
    option_c: str                      # Option C text
    option_d: str                      # Option D text
    answer_key: str                    # Correct answer (A, B, C, or D)
    topic: Optional[str]               # Topic classification
    tags: Optional[List[str]]          # Content tags
    difficulty: Optional[str]          # Difficulty level
    language: str                      # Language code
```

#### 3. `JobInfo` Dataclass
```python
@dataclass
class JobInfo:
    job_id: str                        # Unique job identifier
    channel: str                       # GCS channel
    gcs_csv_path: str                  # Input CSV location
    output_bucket: str                 # Output bucket name
    output_path: str                   # Final video path
```

### API Endpoints

#### 1. `/generate` (POST)
**Purpose**: Start video generation process
**Request Body:**
```json
{
    "num_questions": 5,
    "category": "sports",
    "channel_id": "channel-test",
    "input_mode": "gemini",
    "gemini_api_key": "your-api-key"
}
```

**Response:**
```json
{
    "job_id": "web-20250826-141630",
    "message": "Generation started",
    "status": "starting"
}
```

#### 2. `/channels` (GET)
**Purpose**: List available GCS channels
**Response:**
```json
{
    "channels": ["channel-test", "sports-channel", "science-channel"]
}
```

#### 3. `/channels/<channel_id>/preflight` (GET)
**Purpose**: Validate channel configuration and assets
**Response:**
```json
{
    "ok": true,
    "errors": {}
}
```

### Socket.IO Events

#### 1. `job_update` (Backend → Frontend)
**Purpose**: Real-time progress updates
**Data Structure:**
```json
{
    "job_id": "web-20250826-141630",
    "status": "running",
    "progress": 45,
    "current_step": "Generating video clips...",
    "output_path": "final_videos/channel-test/web-20250826-141630/final_video.mp4"
}
```

#### 2. `approve_questions` (Frontend → Backend)
**Purpose**: User approval of generated questions
**Data Structure:**
```json
{
    "job_id": "web-20250826-141630"
}
```

---

## ☁️ Infrastructure & Deployment

### GCS Bucket Structure
```
trivia-automations-2/
├── channel-test/
│   ├── video-assets/           # Video templates, fonts, audio
│   │   ├── 1.mp4              # Question template
│   │   ├── 2.mp4              # Bridge template
│   │   ├── 3.mp4              # Answer template
│   │   ├── fonts/             # Font files
│   │   └── audio/             # Sound effects
│   ├── feeds/
│   │   ├── csv_input/         # User CSV uploads
│   │   └── gemini_input/      # AI-generated questions
│   └── final_videos/          # Completed video outputs
│       └── web-{job_id}/
│           └── final_video.mp4
```

### Cloud Infrastructure Components

#### 1. Auto-scaling Worker Fleet
**Purpose**: Handle video generation workloads
**Configuration:**
- **Instance Type**: GPU-enabled (n1-standard-4 with T4 GPU)
- **Scaling**: 0-10 instances based on queue depth
- **Health Checks**: HTTP endpoint monitoring
- **Startup Script**: `startup-script.sh` for environment setup

#### 2. Cloud Build Pipeline
**Purpose**: Automated container builds and deployments
**File**: `cloudbuild-worker.yaml`
**Process:**
1. Build Docker image from `Dockerfile`
2. Push to Container Registry
3. Deploy to Cloud Run or Compute Engine

#### 3. Docker Configuration
**Purpose**: Containerized video processing environment
**Key Features:**
- FFmpeg installation and configuration
- Python dependencies from `requirements.txt`
- Font installation for text rendering
- GCS authentication setup

### Deployment Scripts

#### 1. `deploy_web_interface.sh`
**Purpose**: Deploy web interface to Cloud Run
**Process:**
1. Build container image
2. Deploy to Cloud Run
3. Configure environment variables
4. Set up custom domain (optional)

#### 2. `deploy_infrastructure.sh`
**Purpose**: Deploy cloud infrastructure
**Process:**
1. Create GCS buckets with proper IAM
2. Deploy Cloud Functions for job processing
3. Set up Cloud Scheduler for maintenance
4. Configure monitoring and alerting

---

## 🚨 Error Handling & Monitoring

### Error Categories

#### 1. **API Errors**
- **Gemini API Failures**: Retry logic with exponential backoff
- **GCS Permission Errors**: Fallback to signed URLs
- **TTS Service Errors**: Fallback to text-only videos

#### 2. **Processing Errors**
- **Video Generation Failures**: FFmpeg error handling
- **Asset Download Errors**: Fallback to cached assets
- **Memory/Storage Issues**: Resource monitoring and cleanup

#### 3. **User Input Errors**
- **Invalid Categories**: Fallback to general_knowledge
- **Missing API Keys**: Clear error messages
- **File Upload Issues**: Validation and user feedback

### Monitoring & Logging

#### 1. **Progress Tracking**
```python
# Real-time progress updates
socketio.emit('job_update', {
    'job_id': job_id,
    'progress': current_progress,
    'current_step': detailed_description
})
```

#### 2. **Error Logging**
```python
# Comprehensive error logging
logger.error(f"Video generation failed: {e}")
import traceback
traceback.print_exc()
```

#### 3. **Performance Metrics**
- **Generation Time**: Per-question and total pipeline timing
- **Success Rate**: Percentage of successful generations
- **Resource Usage**: CPU, memory, and storage utilization

---

## ⚡ Performance Characteristics

### Timing Benchmarks
```
Question Generation (Gemini):     ~30 seconds for 5 questions
TTS Generation (Google Cloud):   ~10 seconds per question
Video Processing (FFmpeg):       ~2-5 minutes total
Total Pipeline Time:             ~3-6 minutes for 5 questions
```

### Resource Requirements
- **CPU**: 4+ cores for video processing
- **Memory**: 8GB+ RAM for large video files
- **Storage**: 10GB+ temporary storage per job
- **Network**: High bandwidth for GCS operations

### Scalability Considerations
- **Concurrent Jobs**: 5-10 simultaneous generations
- **Queue Management**: Redis-based job queuing
- **Auto-scaling**: 0-10 worker instances
- **CDN Integration**: Cloud CDN for video delivery

---

## 🎯 Next Steps & Recommendations

### Immediate Improvements (Week 1-2)

#### 1. **Enhanced Error Handling**
```python
# Implement circuit breaker pattern
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
```

#### 2. **Better Monitoring**
- Implement Prometheus metrics
- Add Cloud Logging integration
- Create custom dashboards

#### 3. **Performance Optimization**
- Implement video caching
- Add CDN integration
- Optimize FFmpeg parameters

### Medium-term Enhancements (Month 1-2)

#### 1. **Advanced Video Features**
- Multiple video templates
- Custom branding overlays
- Advanced transitions and effects

#### 2. **Analytics Dashboard**
- Generation statistics
- User behavior tracking
- Performance metrics

#### 3. **Multi-language Support**
- Internationalization (i18n)
- Language-specific TTS voices
- Cultural content adaptation

### Long-term Roadmap (Month 3-6)

#### 1. **AI Enhancement**
- Custom model training
- Content personalization
- Advanced question generation

#### 2. **Enterprise Features**
- Multi-tenant architecture
- Advanced user management
- Compliance and security features

#### 3. **Mobile Applications**
- iOS/Android apps
- Offline processing
- Mobile-optimized UI

### Technical Debt & Refactoring

#### 1. **Code Organization**
- Implement proper dependency injection
- Add comprehensive unit tests
- Create API documentation

#### 2. **Infrastructure**
- Implement Infrastructure as Code (Terraform)
- Add automated testing pipeline
- Implement blue-green deployments

#### 3. **Security**
- Implement proper authentication
- Add API rate limiting
- Implement audit logging

---

## 📚 Development Guidelines

### Code Standards
- **Python**: PEP 8 compliance, type hints
- **JavaScript**: ES6+, consistent formatting
- **Documentation**: Docstrings for all functions
- **Testing**: 80%+ code coverage target

### Git Workflow
- **Branch Strategy**: Feature branches → develop → main
- **Commit Messages**: Conventional commits format
- **Code Review**: Required for all PRs
- **Release Tags**: Semantic versioning (v2.0.0)

### Deployment Process
1. **Development**: Local testing with mock services
2. **Staging**: Cloud environment with test data
3. **Production**: Blue-green deployment with rollback capability

---

## 🔍 Troubleshooting Guide

### Common Issues

#### 1. **Videos Not Displaying**
- Check GCS bucket permissions
- Verify signed URL generation
- Check browser console for errors

#### 2. **Category Selection Not Working**
- Verify category parameter passing
- Check Gemini API key validity
- Review prompt preset configuration

#### 3. **Video Generation Failures**
- Check FFmpeg installation
- Verify asset availability
- Review resource constraints

### Debug Commands
```bash
# Check video generation
ffprobe -v error -show_entries stream=width,height -of csv=p=0 video.mp4

# Test GCS access
gsutil ls gs://trivia-automations-2/channel-test/video-assets/

# Monitor system resources
htop
df -h
free -h
```

---

## 📞 Support & Resources

### Documentation
- **API Reference**: OpenAPI/Swagger specs
- **User Guide**: Step-by-step tutorials
- **Developer Guide**: Architecture and contribution guidelines

### Testing
- **Unit Tests**: pytest framework
- **Integration Tests**: End-to-end pipeline testing
- **Performance Tests**: Load testing and benchmarking

### Monitoring
- **Health Checks**: Automated system monitoring
- **Alerting**: Slack/email notifications
- **Metrics**: Custom dashboards and reports

---

**🎯 This specification provides a complete technical understanding of the V2.0 pipeline. Use this as the foundation for all future development and enhancement work.**
