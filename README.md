# 🎬 GCS Video Automations

A production-ready, cloud-native system for generating trivia videos from Gemini AI with scalable GPU rendering.

## 🚀 Quick Start

The complete production pipeline is located in the `production-pipeline/` directory.

```bash
# Navigate to the production pipeline
cd production-pipeline

# For local testing and development
cd core
pip install -r requirements.txt

# For cloud deployment
cd ../cloud-infrastructure
chmod +x deploy_infrastructure.sh
./deploy_infrastructure.sh
```

## 📁 Repository Structure

```
gcs-video-automations/
├── production-pipeline/          # 🎯 Main production system
│   ├── core/                    # Video generation engine
│   ├── cloud-infrastructure/    # Production deployment
│   ├── documentation/           # System documentation
│   └── examples/                # Usage examples
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

## 🔧 What This System Does

1. **🧠 Gemini AI Integration**: Automatically generates trivia questions
2. **☁️ Cloud-Native**: All assets and processing in Google Cloud
3. **🎬 Video Generation**: Creates professional MP4 videos with:
   - Animated backgrounds
   - Text-to-speech audio
   - Timer animations
   - Sound effects
4. **🚀 Scalable**: Handles 80,000+ videos per day with auto-scaling
5. **🛡️ Production Ready**: Fault tolerance, monitoring, and health checks

## 📚 Documentation

- **Main Guide**: [production-pipeline/README.md](production-pipeline/README.md)
- **Core Components**: [production-pipeline/core/](production-pipeline/core/)
- **Cloud Deployment**: [production-pipeline/cloud-infrastructure/](production-pipeline/cloud-infrastructure/)
- **Examples**: [production-pipeline/examples/](production-pipeline/examples/)

## 🎯 Use Cases

- **Content Creation**: Automated trivia video generation
- **Education**: Educational content at scale
- **Entertainment**: Social media content production
- **Marketing**: Branded trivia campaigns

## 🚨 Requirements

- Google Cloud Project with billing enabled
- Gemini API key
- Service account credentials for GCS access
- NVIDIA GPU instances for production rendering

## 🔮 Future Features

- Multi-GPU support
- Advanced scheduling
- Real-time monitoring dashboard
- Cost optimization
- Custom video formats

---

**Built for production-scale video automation** 🎬✨

For detailed information, see the [production pipeline documentation](production-pipeline/README.md).
