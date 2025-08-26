# 🧪 Testing Framework for GCS Video Automations

This directory contains a comprehensive testing framework that allows you to test each component of the trivia video generation pipeline independently, or run full system tests.

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Set required environment variables
export GEMINI_API_KEY="your-gemini-api-key"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/credentials.json"

# Check environment
python run_all_tests.py --env-check
```

### 2. Run All Tests
```bash
# Test all components
python run_all_tests.py --all

# Test specific component
python run_all_tests.py --component gemini
python run_all_tests.py --component tts
python run_all_tests.py --component video
python run_all_tests.py --component pipeline
```

## 📋 Available Test Components

### 🧠 Gemini Feeder Tests (`test_gemini_feeder.py`)
**Purpose**: Test AI question generation with retry logic

**What it tests**:
- Question generation with different target counts (3, 5, 7, 10)
- Retry logic when Gemini doesn't generate enough questions
- Question quality and format validation
- CSV dataset structure verification

**Usage**:
```bash
python test_gemini_feeder.py
```

**Key Features**:
- ✅ **Retry Logic**: Automatically retries until target question count is met
- ✅ **Quality Validation**: Checks question structure and content
- ✅ **Count Verification**: Downloads and counts actual questions generated
- ✅ **Multiple Test Cases**: Tests various question counts

### 🔊 TTS Tests (`test_tts.py`)
**Purpose**: Test Text-to-Speech functionality

**What it tests**:
- Different TTS voices (en-US-Neural2-F, en-US-Neural2-M, etc.)
- Text length handling (short, medium, long, very long)
- Speaking rate variations (0.5x to 2.0x)
- Audio file generation and quality

**Usage**:
```bash
python test_tts.py
```

**Key Features**:
- ✅ **Voice Testing**: Tests all available neural voices
- ✅ **Length Testing**: Tests various text lengths
- ✅ **Rate Testing**: Tests different speaking speeds
- ✅ **Quality Validation**: Checks file sizes and generation success

### 🎬 Video Generation Tests (`test_video_generation.py`)
**Purpose**: Test video generation with different question counts

**What it tests**:
- Video generation with 3, 5, 7, and 10 questions
- PNG text rendering and overlay
- Video concatenation and final assembly
- GCS upload and file verification

**Usage**:
```bash
python test_video_generation.py
```

**Key Features**:
- ✅ **Sample Data**: Creates test CSV files with sample questions
- ✅ **Multiple Counts**: Tests various question counts
- ✅ **Output Verification**: Checks generated video files
- ✅ **GCS Integration**: Tests cloud storage functionality

### 🚀 Full Pipeline Tests (`trivia_generator_cli.py`)
**Purpose**: Test the complete pipeline from Gemini to final video

**What it tests**:
- End-to-end workflow
- Interactive user input
- Progress tracking
- Final video generation and upload

**Usage**:
```bash
python trivia_generator_cli.py
```

**Key Features**:
- ✅ **Interactive Interface**: Fun terminal UI with emojis
- ✅ **Progress Tracking**: Shows step-by-step progress
- ✅ **User Input**: Asks for number of questions
- ✅ **Complete Workflow**: Tests entire pipeline

## 🎯 Master Test Runner (`run_all_tests.py`)

The master test runner provides a unified interface for running all tests:

```bash
# Check environment only
python run_all_tests.py --env-check

# Test specific component
python run_all_tests.py --component gemini
python run_all_tests.py --component tts
python run_all_tests.py --component video
python run_all_tests.py --component pipeline

# Test all components
python run_all_tests.py --all

# Test pipeline with custom question count
python run_all_tests.py --component pipeline --questions 7
```

## 🔧 Testing Workflow

### 1. **Component Testing** (Recommended for Development)
Test individual components to isolate issues:
```bash
# Test just the AI question generation
python run_all_tests.py --component gemini

# Test just the TTS system
python run_all_tests.py --component tts

# Test just the video generation
python run_all_tests.py --component video
```

### 2. **Integration Testing** (Recommended for Validation)
Test the complete pipeline:
```bash
# Test full pipeline with 5 questions
python run_all_tests.py --component pipeline --questions 5

# Or use the interactive interface
python trivia_generator_cli.py
```

### 3. **Full System Testing** (Recommended for Deployment)
Test all components together:
```bash
python run_all_tests.py --all
```

## 📊 Test Results Interpretation

### ✅ PASS
- Component is working correctly
- All test cases succeeded
- Ready for production use

### ⚠️ PARTIAL
- Component partially working
- Some test cases succeeded
- May need investigation

### ❌ FAIL
- Component has issues
- Test cases failed
- Needs debugging and fixes

## 🐛 Debugging Failed Tests

### 1. **Check Environment Variables**
```bash
python run_all_tests.py --env-check
```

### 2. **Check Individual Components**
```bash
# Test just the failing component
python run_all_tests.py --component [component_name]
```

### 3. **Check Logs**
- Look for error messages in test output
- Check GCS bucket permissions
- Verify API keys and credentials

### 4. **Common Issues**
- **Missing API Keys**: Set `GEMINI_API_KEY` and `GOOGLE_APPLICATION_CREDENTIALS`
- **GCS Permissions**: Ensure service account has read/write access
- **Network Issues**: Check internet connectivity for API calls
- **Font Issues**: Cloud environment may need font packages

## 🚀 Production Deployment

### 1. **Test in Development**
```bash
# Run all tests locally
python run_all_tests.py --all
```

### 2. **Test in Staging**
```bash
# Test with production-like data
python run_all_tests.py --component pipeline --questions 10
```

### 3. **Deploy to Production**
- All tests pass locally and in staging
- Video generation produces expected output
- GCS integration works correctly
- Error handling is robust

## 📁 File Structure

```
production-pipeline/
├── run_all_tests.py           # Master test runner
├── test_gemini_feeder.py      # Gemini AI tests
├── test_tts.py               # TTS functionality tests
├── test_video_generation.py  # Video generation tests
├── trivia_generator_cli.py   # Full pipeline tests
├── TESTING_README.md         # This file
└── core/                     # Core modules being tested
    ├── gemini_feeder.py
    ├── cloud_video_generator_fixed.py
    └── ...
```

## 🎯 Best Practices

### 1. **Test Before Deploying**
Always run tests before pushing to production:
```bash
python run_all_tests.py --all
```

### 2. **Test Individual Components**
When debugging, test components individually:
```bash
python run_all_tests.py --component [component_name]
```

### 3. **Monitor Test Results**
- Check all test results
- Investigate any failures
- Verify output quality

### 4. **Update Tests**
- Add new test cases for new features
- Update tests when APIs change
- Maintain test coverage

## 🔗 Related Documentation

- **Core Pipeline**: See `README.md` for main pipeline documentation
- **Cloud Infrastructure**: See `cloud-infrastructure/` for deployment details
- **Examples**: See `examples/` for usage examples

---

**🎉 Happy Testing!** This framework ensures your trivia video generation pipeline is robust, reliable, and ready for production use.
