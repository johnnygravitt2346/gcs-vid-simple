# 🚀 Quick Start - Baseline Pipeline

## ⚡ Get Running in 5 Minutes

### 1. **Environment Setup**
```bash
# Activate virtual environment
source venv_web/bin/activate

# Set your Gemini API key
export GEMINI_API_KEY="your_api_key_here"
```

### 2. **Test the Pipeline**
```bash
# Basic test (2 quizzes, 5 questions each)
python3 test_complete_trivia_flow.py

# Full production test (5 quizzes, 20 questions each)
python3 test_5_full_quizzes.py
```

### 3. **View Results**
- **Local**: Check `output/` directory
- **GCS**: Visit console links in output
- **Videos**: `gs://trivia-automations-2/episodes/`

## 🎯 What You'll Get

### **Output Videos**
- **Resolution**: 1920x1080 (Full HD)
- **Quality**: Professional-grade MP4
- **Content**: Factually accurate sports trivia
- **Design**: Modern typography with beautiful shadows

### **Pipeline Features**
- ✅ **Gemini Integration**: AI-powered question generation
- ✅ **Modern Typography**: Helvetica-based design system
- ✅ **Font Optimization**: Dynamic sizing based on content
- ✅ **Professional Audio**: Google TTS + stereo balance
- ✅ **GCS Upload**: Automatic cloud storage

## 🔧 Troubleshooting

### **Common Issues**
1. **Font Not Found**: Check `fonts/` directory exists
2. **FFmpeg Error**: Ensure FFmpeg is installed
3. **GCS Permission**: Verify service account access
4. **Memory Issues**: Check available RAM

### **Quick Fixes**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check FFmpeg
ffmpeg -version

# Verify fonts
ls -la fonts/
```

## 📚 Full Documentation
- **Technical Details**: `README_VIDEO_CREATION.md`
- **Complete Process**: `BASELINE_PIPELINE_README.md`
- **Code**: `src/core/official_video_generator.py`

---

**🎉 Your baseline pipeline is ready to generate professional sports trivia videos!**
