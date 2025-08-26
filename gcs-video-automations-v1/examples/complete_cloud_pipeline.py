#!/usr/bin/env python3
"""
Complete Cloud Pipeline: Gemini → GCS → Cloud Video Generation
This script orchestrates the entire pipeline from start to finish.
"""

import asyncio
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
import json

# Add core modules to path
sys.path.append(str(Path(__file__).parent.parent / "core"))

from gemini_feeder import GeminiFeeder, FeederRequest
from cloud_video_generator_fixed import JobInfo, process_job
from google.cloud import storage

# Configuration
GCS_ASSETS_BUCKET = "trivia-automations-2"
GCS_ASSET_BASE_PATH = "channel-test/video-assets"
GCS_JOBS_BUCKET = "trivia-automation"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def setup_gcs_bucket_structure():
    """Ensure the GCS bucket structure exists for jobs"""
    client = storage.Client()
    
    # Create jobs bucket if it doesn't exist
    try:
        bucket = client.bucket(GCS_JOBS_BUCKET)
        bucket.reload()
    except Exception:
        print(f"Creating bucket: {GCS_JOBS_BUCKET}")
        bucket = client.create_bucket(GCS_JOBS_BUCKET, location="us-central1")
    
    # Create job structure
    job_base_path = f"jobs/channel-test/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    return job_base_path

async def generate_trivia_with_gemini():
    """Generate trivia questions using Gemini AI"""
    print("🧠 Generating trivia questions with Gemini AI...")
    
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    # Initialize Gemini Feeder
    feeder = GeminiFeeder(api_key=GEMINI_API_KEY)
    
    # Create feeder request
    feeder_request = FeederRequest(
        channel_id="channel-test",
        prompt_preset="sports",
        quantity=3,
        difficulty="medium",
        language_filter="en"
    )
    
    # Generate trivia dataset
    print("📝 Generating trivia dataset...")
    dataset_uri = await feeder.generate_dataset(feeder_request)
    
    print(f"✅ Generated dataset: {dataset_uri}")
    return dataset_uri

def save_trivia_to_gcs(dataset_uri: str, job_path: str):
    """Save trivia data to GCS"""
    print(f"☁️ Processing dataset from: {dataset_uri}")
    
    # Parse the dataset URI to get the bucket and path
    if dataset_uri.startswith("gs://"):
        parts = dataset_uri.split("/")
        source_bucket = parts[2]
        source_path = "/".join(parts[3:])
    else:
        raise ValueError(f"Invalid dataset URI: {dataset_uri}")
    
    # The CSV file is at {dataset_uri}/questions.csv
    csv_source_path = f"{source_path}/questions.csv"
    
    # Download the CSV from the source location
    client = storage.Client()
    source_bucket_obj = client.bucket(source_bucket)
    source_blob = source_bucket_obj.blob(csv_source_path)
    
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        # Download and write CSV content
        csv_content = source_blob.download_as_text()
        f.write(csv_content)
        temp_csv_path = f.name
    
    # Upload to our job location
    target_bucket = client.bucket(GCS_JOBS_BUCKET)
    csv_blob_path = f"{job_path}/questions.csv"
    target_blob = target_bucket.blob(csv_blob_path)
    target_blob.upload_from_filename(temp_csv_path)
    
    # Cleanup temp file
    os.unlink(temp_csv_path)
    
    print(f"✅ Trivia data saved to: gs://{GCS_JOBS_BUCKET}/{csv_blob_path}")
    return f"gs://{GCS_JOBS_BUCKET}/{csv_blob_path}"

def create_job_manifest(job_path: str, csv_path: str, dataset_type: str):
    """Create job manifest file"""
    print("📋 Creating job manifest...")
    
    manifest = {
        "job_id": job_path.split("/")[-1],
        "channel": "channel-test",
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "dataset_type": dataset_type,
        "gcs_csv_path": csv_path,
        "output_bucket": GCS_JOBS_BUCKET,
        "output_path": f"final_videos/channel-test/{job_path.split('/')[-1]}/final_video.mp4"
    }
    
    # Save manifest to GCS
    client = storage.Client()
    bucket = client.bucket(GCS_JOBS_BUCKET)
    
    manifest_blob = bucket.blob(f"{job_path}/_MANIFEST.json")
    manifest_blob.upload_from_string(
        json.dumps(manifest, indent=2),
        content_type="application/json"
    )
    
    print(f"✅ Job manifest created: gs://{GCS_JOBS_BUCKET}/{job_path}/_MANIFEST.json")
    return manifest

def process_video_job(manifest):
    """Process the video generation job"""
    print("🎬 Starting video generation job...")
    
    # Create JobInfo object
    job_info = JobInfo(
        job_id=manifest["job_id"],
        channel=manifest["channel"],
        gcs_csv_path=manifest["gcs_csv_path"],
        output_bucket=manifest["output_bucket"],
        output_path=manifest["output_path"]
    )
    
    # Process the job
    output_path = process_job(job_info)
    
    # Update manifest with completion status
    manifest["status"] = "completed"
    manifest["completed_at"] = datetime.now().isoformat()
    manifest["final_video_path"] = output_path
    
    # Save updated manifest
    client = storage.Client()
    bucket = client.bucket(GCS_JOBS_BUCKET)
    
    manifest_blob = bucket.blob(f"jobs/channel-test/{manifest['job_id']}/_MANIFEST.json")
    manifest_blob.upload_from_string(
        json.dumps(manifest, indent=2),
        content_type="application/json"
    )
    
    print(f"✅ Video generation completed: {output_path}")
    return output_path

async def main():
    """Main pipeline execution"""
    print("🚀 Starting Complete Cloud Pipeline")
    print("=" * 50)
    
    try:
        # Step 1: Setup GCS bucket structure
        print("\n📁 Step 1: Setting up GCS bucket structure...")
        job_path = setup_gcs_bucket_structure()
        print(f"✅ Job path: {job_path}")
        
        # Step 2: Generate trivia with Gemini
        print("\n🧠 Step 2: Generating trivia with Gemini AI...")
        dataset_uri = await generate_trivia_with_gemini()
        print(f"✅ Generated dataset: {dataset_uri}")
        
        # Step 3: Save trivia to GCS
        print("\n☁️ Step 3: Saving trivia data to GCS...")
        csv_path = save_trivia_to_gcs(dataset_uri, job_path)
        print(f"✅ CSV saved to: {csv_path}")
        
        # Step 4: Create job manifest
        print("\n📋 Step 4: Creating job manifest...")
        manifest = create_job_manifest(job_path, csv_path, "dataset")
        print(f"✅ Manifest created for job: {manifest['job_id']}")
        
        # Step 5: Process video generation
        print("\n🎬 Step 5: Processing video generation...")
        final_video_path = process_video_job(manifest)
        print(f"✅ Final video: {final_video_path}")
        
        print("\n🎉 Pipeline completed successfully!")
        print("=" * 50)
        print(f"📊 Job ID: {manifest['job_id']}")
        print(f"📝 Dataset Type: {manifest['dataset_type']}")
        print(f"🎬 Final Video: {final_video_path}")
        print(f"📁 GCS Job Path: gs://{GCS_JOBS_BUCKET}/jobs/channel-test/{manifest['job_id']}")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check environment
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY environment variable is required")
        print("Set it with: export GEMINI_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Run the pipeline
    asyncio.run(main())
