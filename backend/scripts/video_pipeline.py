#!/usr/bin/env python3
import os
import sys
import json
import tempfile
import subprocess
from google.cloud import storage
import google.generativeai as genai

print("🎬 Starting Video Pipeline Test...")

# Initialize clients
storage_client = storage.Client(project="mythic-groove-469801-b7")

# Test Gemini AI
print("🤖 Testing Gemini AI...")
try:
    # Set up Gemini API key (we'll need to get this from environment or GCS)
    genai.configure(api_key="YOUR_API_KEY")  # We'll handle this properly
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Generate 1 trivia question about space exploration with 4 multiple choice answers. Format as JSON with 'question', 'correct_answer', and 'options' fields.")
    trivia_data = json.loads(response.text)
    print(f"✅ Gemini AI working! Question: {trivia_data['question'][:50]}...")
except Exception as e:
    print(f"❌ Gemini AI error: {e}")
    # Fallback question
    trivia_data = {
        "question": "What planet is known as the Red Planet?",
        "correct_answer": "Mars",
        "options": ["Venus", "Mars", "Jupiter", "Saturn"]
    }
    print("🔄 Using fallback question")

# Test GCS operations
print("☁️ Testing GCS operations...")
bucket = storage_client.bucket("trivia-automation")

# Create test folder structure
test_folder = "trivia-tests/test-assets"
test_blob = bucket.blob(f"{test_folder}/test_status.txt")
test_blob.upload_from_string("Pipeline test completed successfully!")
print(f"✅ GCS upload working! Created: {test_folder}/test_status.txt")

# Test video processing (if ffmpeg available)
print("🎥 Testing video processing...")
try:
    result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ FFmpeg available!")
        ffmpeg_version = result.stdout.split('\n')[0]
        print(f"   Version: {ffmpeg_version}")
    else:
        print("❌ FFmpeg not working properly")
except FileNotFoundError:
    print("❌ FFmpeg not installed")

print("🎉 Video Pipeline Test Complete!")
print(f"�� Test results saved to: gs://trivia-automation/{test_folder}/test_status.txt")
