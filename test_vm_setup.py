#!/usr/bin/env python3
"""
Test VM Setup Script

Quick verification that the VM environment is properly configured
before starting the full Trivia Factory services.
"""

import os
import sys
import requests
import subprocess
from pathlib import Path

def test_python_dependencies():
    """Test if required Python packages are available"""
    print("🔍 Testing Python dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn", 
        "streamlit",
        "google.cloud.storage",
        "google.cloud.aiplatform",
        "google.cloud.texttospeech"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {missing_packages}")
        print("Run: pip3 install -r backend/requirements.txt")
        return False
    
    print("✅ All Python dependencies available")
    return True

def test_environment_variables():
    """Test if required environment variables are set"""
    print("\n🔍 Testing environment variables...")
    
    required_vars = [
        "GOOGLE_CLOUD_PROJECT",
        "GCS_BUCKET",
        "API_BASE_URL",
        "CHANNEL_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {missing_vars}")
        print("Please set these in your .env file")
        return False
    
    print("✅ All required environment variables set")
    return True

def test_gcs_access():
    """Test if GCS bucket is accessible"""
    print("\n🔍 Testing GCS access...")
    
    try:
        from google.cloud import storage
        
        bucket_name = os.getenv("GCS_BUCKET")
        if not bucket_name:
            print("  ❌ GCS_BUCKET not set")
            return False
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # Try to list objects (this will fail if no access)
        blobs = list(bucket.list_blobs(max_results=1))
        print(f"  ✅ GCS bucket '{bucket_name}' accessible")
        print(f"  📊 Bucket contains {len(blobs)}+ objects")
        return True
        
    except Exception as e:
        print(f"  ❌ GCS access failed: {e}")
        print("  💡 Make sure service account is attached to VM")
        return False

def test_ports_available():
    """Test if required ports are available"""
    print("\n🔍 Testing port availability...")
    
    ports_to_test = [8000, 8501]
    
    for port in ports_to_test:
        try:
            # Try to bind to the port
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', port))
            sock.close()
            print(f"  ✅ Port {port} available")
        except OSError:
            print(f"  ❌ Port {port} already in use")
            return False
    
    print("✅ All required ports available")
    return True

def test_gpu_availability():
    """Test if GPU is available"""
    print("\n🔍 Testing GPU availability...")
    
    try:
        result = subprocess.run(['nvidia-smi'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        
        if result.returncode == 0:
            print("  ✅ NVIDIA GPU available")
            print("  📊 GPU Info:")
            for line in result.stdout.split('\n')[:5]:
                if line.strip():
                    print(f"    {line}")
            return True
        else:
            print("  ❌ NVIDIA GPU not available")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("  ❌ nvidia-smi not available")
        return False

def test_ffmpeg():
    """Test if ffmpeg is available"""
    print("\n🔍 Testing ffmpeg...")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        
        if result.returncode == 0:
            print("  ✅ ffmpeg available")
            # Extract version info
            version_line = result.stdout.split('\n')[0]
            print(f"  📊 {version_line}")
            return True
        else:
            print("  ❌ ffmpeg not working")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("  ❌ ffmpeg not installed")
        print("  💡 Install with: sudo apt-get install ffmpeg")
        return False

def main():
    """Run all tests"""
    print("🎬 Trivia Factory VM Setup Test")
    print("=" * 50)
    
    tests = [
        ("Python Dependencies", test_python_dependencies),
        ("Environment Variables", test_environment_variables),
        ("GCS Access", test_gcs_access),
        ("Port Availability", test_ports_available),
        ("GPU Availability", test_gpu_availability),
        ("FFmpeg", test_ffmpeg)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} test failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Ready to start services.")
        print("Run: ./start_vm_services.sh")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix issues before starting services.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
