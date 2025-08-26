#!/usr/bin/env python3
"""
Test Cloud Pipeline Components
This script tests individual components of the cloud pipeline.
"""

import os
import sys
from pathlib import Path

# Add core modules to path
sys.path.append(str(Path(__file__).parent.parent / "core"))

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing module imports...")
    
    try:
        from gemini_feeder import GeminiFeeder, FeederRequest
        print("✅ Gemini Feeder imported successfully")
    except ImportError as e:
        print(f"❌ Gemini Feeder import failed: {e}")
        return False
    
    try:
        from cloud_video_generator_fixed import JobInfo, process_job
        print("✅ Cloud Video Generator imported successfully")
    except ImportError as e:
        print(f"❌ Cloud Video Generator import failed: {e}")
        return False
    
    try:
        from google.cloud import storage
        print("✅ Google Cloud Storage imported successfully")
    except ImportError as e:
        print(f"❌ Google Cloud Storage import failed: {e}")
        return False
    
    try:
        from google.cloud import texttospeech
        print("✅ Google Cloud TTS imported successfully")
    except ImportError as e:
        print(f"❌ Google Cloud TTS import failed: {e}")
        return False
    
    return True

def test_gcs_connection():
    """Test GCS connection"""
    print("\n☁️ Testing GCS connection...")
    
    try:
        from google.cloud import storage
        client = storage.Client()
        
        # Try to list buckets
        buckets = list(client.list_buckets(max_results=5))
        print(f"✅ GCS connection successful, found {len(buckets)} buckets")
        return True
        
    except Exception as e:
        print(f"❌ GCS connection failed: {e}")
        print("💡 Make sure you have GOOGLE_APPLICATION_CREDENTIALS set")
        return False

def test_gemini_api():
    """Test Gemini API key"""
    print("\n🧠 Testing Gemini API...")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not set")
        print("💡 Set it with: export GEMINI_API_KEY='your-api-key'")
        return False
    
    if len(api_key) < 10:
        print("❌ GEMINI_API_KEY appears to be invalid (too short)")
        return False
    
    print(f"✅ Gemini API key found: {api_key[:10]}...")
    return True

def test_ffmpeg():
    """Test FFmpeg availability"""
    print("\n🎬 Testing FFmpeg...")
    
    try:
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg available: {version_line}")
            return True
        else:
            print("❌ FFmpeg command failed")
            return False
            
    except FileNotFoundError:
        print("❌ FFmpeg not found in PATH")
        print("💡 Install FFmpeg: https://ffmpeg.org/download.html")
        return False
    except Exception as e:
        print(f"❌ FFmpeg test failed: {e}")
        return False

def test_nvidia_gpu():
    """Test NVIDIA GPU availability"""
    print("\n🖥️ Testing NVIDIA GPU...")
    
    try:
        import subprocess
        result = subprocess.run(["nvidia-smi"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            # Extract GPU info
            lines = result.stdout.split('\n')
            for line in lines:
                if 'NVIDIA' in line and 'GPU' in line:
                    print(f"✅ NVIDIA GPU found: {line.strip()}")
                    return True
            
            print("✅ nvidia-smi working (GPU info available)")
            return True
        else:
            print("❌ nvidia-smi command failed")
            return False
            
    except FileNotFoundError:
        print("❌ nvidia-smi not found (NVIDIA drivers not installed)")
        print("💡 Install NVIDIA drivers: https://www.nvidia.com/drivers/")
        return False
    except Exception as e:
        print(f"❌ NVIDIA GPU test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Cloud Pipeline Component Tests")
    print("=" * 40)
    
    tests = [
        ("Module Imports", test_imports),
        ("GCS Connection", test_gcs_connection),
        ("Gemini API", test_gemini_api),
        ("FFmpeg", test_ffmpeg),
        ("NVIDIA GPU", test_nvidia_gpu),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Pipeline is ready to run.")
        return True
    else:
        print("⚠️ Some tests failed. Please fix the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
