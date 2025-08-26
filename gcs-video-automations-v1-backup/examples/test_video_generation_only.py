#!/usr/bin/env python3
"""
Test Cloud Video Generation Only
This script tests the video generation part without Gemini to verify GCS streaming works.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add core modules to path
sys.path.append(str(Path(__file__).parent.parent / "core"))

from cloud_video_generator_fixed import JobInfo, process_job
from google.cloud import storage

# Configuration
GCS_ASSETS_BUCKET = "trivia-automations-2"
GCS_ASSET_BASE_PATH = "channel-test/video-assets"
GCS_JOBS_BUCKET = "trivia-automation"

def create_sample_csv():
    """Create a sample CSV with test trivia questions"""
    csv_content = """Question,OptionA,OptionB,OptionC,OptionD,Correct Answer
What is the capital of France?,Paris,London,Berlin,Madrid,A
Which planet is closest to the Sun?,Mercury,Venus,Earth,Mars,A
What is 2 + 2?,3,4,5,6,B"""
    
    return csv_content

def upload_sample_csv():
    """Upload sample CSV to GCS for testing"""
    print("📝 Creating sample CSV for testing...")
    
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(create_sample_csv())
        temp_csv_path = f.name
    
    # Upload to GCS
    client = storage.Client()
    bucket = client.bucket(GCS_JOBS_BUCKET)
    
    csv_blob_path = "test-jobs/sample-questions.csv"
    blob = bucket.blob(csv_blob_path)
    blob.upload_from_filename(temp_csv_path)
    
    # Cleanup temp file
    os.unlink(temp_csv_path)
    
    csv_uri = f"gs://{GCS_JOBS_BUCKET}/{csv_blob_path}"
    print(f"✅ Sample CSV uploaded to: {csv_uri}")
    return csv_uri

def test_cloud_video_generation():
    """Test the cloud video generation with sample data"""
    print("🎬 Testing Cloud Video Generation...")
    
    # Create job info
    job_info = JobInfo(
        job_id="test-video-001",
        channel="channel-test",
        gcs_csv_path="gs://trivia-automation/test-jobs/sample-questions.csv",
        output_bucket="trivia-automation",
        output_path="test-videos/sample-video.mp4"
    )
    
    try:
        # Process the job
        output_path = process_job(job_info)
        print(f"✅ Video generation completed: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Video generation failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing Cloud Video Generation (No Gemini)")
    print("=" * 50)
    
    try:
        # Step 1: Upload sample CSV
        print("\n📝 Step 1: Uploading sample CSV...")
        csv_uri = upload_sample_csv()
        
        # Step 2: Test video generation
        print("\n🎬 Step 2: Testing video generation...")
        success = test_cloud_video_generation()
        
        if success:
            print("\n🎉 Test completed successfully!")
            print("✅ GCS streaming is working")
            print("✅ Video generation is working")
            print("✅ No local processing required")
        else:
            print("\n❌ Test failed")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Check environment
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        print("❌ Error: GOOGLE_CLOUD_PROJECT environment variable is required")
        print("Set it with: export GOOGLE_CLOUD_PROJECT='your-project-id'")
        sys.exit(1)
    
    # Run the test
    success = main()
    sys.exit(0 if success else 1)

