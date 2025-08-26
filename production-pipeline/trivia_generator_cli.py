#!/usr/bin/env python3
"""
🎬 Fun Terminal Trivia Video Generator
Interactive CLI with progress bars and fun prompts!
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add core modules to path
sys.path.append(str(Path(__file__).parent / "core"))

from gemini_feeder import GeminiFeeder, FeederRequest
from cloud_video_generator_fixed import JobInfo, process_job
from google.cloud import storage

# Configuration
GCS_ASSETS_BUCKET = "trivia-automations-2"
GCS_ASSET_BASE_PATH = "channel-test/video-assets"
GCS_JOBS_BUCKET = "trivia-automation"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def print_banner():
    """Print a fun banner for the trivia generator"""
    print("🎬" + "="*60 + "🎬")
    print("🚀  WELCOME TO THE TRIVIA VIDEO GENERATOR! 🚀")
    print("🎯  Generate professional trivia videos with AI! 🎯")
    print("🎬" + "="*60 + "🎬")
    print()

def get_user_input():
    """Get user input for trivia generation"""
    print("🎲  Let's create some awesome trivia videos!")
    print()
    
    while True:
        try:
            num_questions = input("📝 How many general sports trivia questions? (1-10): ").strip()
            num_questions = int(num_questions)
            
            if 1 <= num_questions <= 10:
                return num_questions
            else:
                print("❌ Please enter a number between 1 and 10!")
        except ValueError:
            print("❌ Please enter a valid number!")
    
    return 3  # Default fallback

def print_progress_bar(current, total, prefix="Progress", suffix="Complete", length=50):
    """Print a beautiful progress bar"""
    filled = int(length * current // total)
    bar = "█" * filled + "░" * (length - filled)
    percent = current / total * 100
    
    print(f"\r{prefix}: |{bar}| {percent:0.1f}% {suffix}", end="", flush=True)
    
    if current == total:
        print()  # New line when complete

def print_step_header(step_num, total_steps, title):
    """Print a step header with progress"""
    print(f"\n🎯 Step {step_num}/{total_steps}: {title}")
    print("─" * 60)

async def generate_trivia_with_progress(num_questions):
    """Generate trivia with progress indication"""
    print_step_header(1, 4, "Generating Trivia Questions with Gemini AI")
    
    if not GEMINI_API_KEY:
        raise ValueError("❌ GEMINI_API_KEY environment variable is required")
    
    print("🧠 Connecting to Gemini AI...")
    feeder = GeminiFeeder(api_key=GEMINI_API_KEY)
    
    max_retries = 5
    attempt = 1
    
    while attempt <= max_retries:
        print(f"📝 Attempt {attempt}/{max_retries}: Generating {num_questions} sports trivia questions...")
        print("⏳ This may take a moment...")
        
        # Create feeder request
        feeder_request = FeederRequest(
            channel_id="channel-test",
            prompt_preset="sports",
            quantity=num_questions,
            difficulty="medium",
            language_filter="en"
        )
        
        # Generate trivia dataset
        dataset_uri = await feeder.generate_dataset(feeder_request)
        
        # Verify we got the right number of questions
        print(f"🔍 Verifying question count from: {dataset_uri}")
        
        # Download and count the questions
        import tempfile
        client = storage.Client()
        
        if dataset_uri.startswith("gs://"):
            parts = dataset_uri.split("/")
            source_bucket = parts[2]
            source_path = "/".join(parts[3:])
            csv_source_path = f"{source_path}/questions.csv"
            
            source_bucket_obj = client.bucket(source_bucket)
            source_blob = source_bucket_obj.blob(csv_source_path)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                csv_content = source_blob.download_as_text()
                f.write(csv_content)
                temp_csv_path = f.name
            
            # Count the questions
            import csv
            with open(temp_csv_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                actual_count = len(rows)
            
            # Clean up temp file
            os.unlink(temp_csv_path)
            
            print(f"📊 Generated {actual_count} questions, requested {num_questions}")
            
            if actual_count >= num_questions:
                print(f"✅ Successfully generated {actual_count} questions (≥ {num_questions} requested)")
                return dataset_uri
            else:
                print(f"❌ Only got {actual_count} questions, need {num_questions}")
                if attempt < max_retries:
                    print(f"🔄 Retrying... (attempt {attempt + 1}/{max_retries})")
                    attempt += 1
                    continue
                else:
                    print(f"⚠️  Maximum retries reached. Proceeding with {actual_count} questions.")
                    return dataset_uri
        else:
            print(f"⚠️  Invalid dataset URI format: {dataset_uri}")
            return dataset_uri
    
    # Should never reach here, but just in case
    return dataset_uri

def setup_job_structure():
    """Setup GCS job structure"""
    print_step_header(2, 4, "Setting up Cloud Storage")
    
    client = storage.Client()
    
    # Create jobs bucket if it doesn't exist
    try:
        bucket = client.bucket(GCS_JOBS_BUCKET)
        bucket.reload()
    except Exception:
        print(f"📦 Creating bucket: {GCS_JOBS_BUCKET}")
        bucket = client.create_bucket(GCS_JOBS_BUCKET, location="us-central1")
    
    # Create job structure
    job_base_path = f"jobs/channel-test/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    print(f"📁 Job path: {job_base_path}")
    return job_base_path

def save_trivia_to_gcs(dataset_uri: str, job_path: str):
    """Save trivia data to GCS with progress"""
    print_step_header(3, 4, "Processing Trivia Data")
    
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
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        # Download and write CSV content
        csv_content = source_blob.download_as_text()
        f.write(csv_content)
        temp_csv_path = f.name
    
    # Upload to our job location
    target_bucket = client.bucket(GCS_JOBS_BUCKET)
    csv_blob_path = f"{job_path}/questions.csv"
    
    csv_blob = target_bucket.blob(csv_blob_path)
    csv_blob.upload_from_filename(temp_csv_path)
    
    # Clean up temp file
    os.unlink(temp_csv_path)
    
    csv_gcs_path = f"gs://{GCS_JOBS_BUCKET}/{csv_blob_path}"
    print(f"✅ Trivia data saved to: {csv_gcs_path}")
    return csv_gcs_path

def create_job_manifest(job_path: str, csv_path: str, dataset_type: str):
    """Create job manifest"""
    print("📋 Creating job manifest...")
    
    job_id = job_path.split("/")[-1]
    
    manifest = {
        "job_id": job_id,
        "channel": "channel-test",
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "dataset_type": dataset_type,
        "gcs_csv_path": csv_path,
        "output_bucket": GCS_JOBS_BUCKET,
        "output_path": f"final_videos/channel-test/{job_id}/final_video.mp4"
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

def process_video_job_with_progress(manifest, num_questions):
    """Process video generation with detailed progress"""
    print_step_header(4, 4, "Generating Professional Video")
    
    print("🎬 Starting video generation job...")
    
    # Create JobInfo object
    job_info = JobInfo(
        job_id=manifest["job_id"],
        channel=manifest["channel"],
        gcs_csv_path=manifest["gcs_csv_path"],
        output_bucket=manifest["output_bucket"],
        output_path=manifest["output_path"]
    )
    
    print(f"📊 Processing {num_questions} trivia questions...")
    print("🎨 Applying perfect text rendering and professional styling...")
    print("⏱️  This will process ALL questions for a complete video...")
    
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

def print_success_summary(manifest, final_video_path, num_questions):
    """Print a beautiful success summary with clickable link"""
    print("\n" + "🎉" + "="*60 + "🎉")
    print("🚀  TRIVIA VIDEO GENERATION COMPLETED SUCCESSFULLY! 🚀")
    print("🎬" + "="*60 + "🎬")
    
    print(f"\n📊 Job Summary:")
    print(f"   🆔 Job ID: {manifest['job_id']}")
    print(f"   📝 Questions Generated: {num_questions}")
    print(f"   🎯 Category: Sports Trivia")
    print(f"   🕒 Created: {manifest['created_at']}")
    
    print(f"\n🎬 Final Video:")
    print(f"   📁 GCS Path: {final_video_path}")
    
    # Create clickable link for local development
    if "gs://" in final_video_path:
        gcs_parts = final_video_path.replace("gs://", "").split("/")
        bucket_name = gcs_parts[0]
        file_path = "/".join(gcs_parts[1:])
        
        # Create a clickable link (works in most modern terminals)
        clickable_link = f"https://console.cloud.google.com/storage/browser/{bucket_name}?prefix={file_path}"
        
        print(f"\n🔗 Clickable Links:")
        print(f"   🌐 Google Cloud Console: {clickable_link}")
        print(f"   📱 Direct GCS: {final_video_path}")
        
        print(f"\n💡 To download the video:")
        print(f"   gsutil cp '{final_video_path}' ./")
    
    print(f"\n🎯 GCS Job Path: gs://{GCS_JOBS_BUCKET}/jobs/channel-test/{manifest['job_id']}")
    print("🎉" + "="*60 + "🎉")

async def main():
    """Main interactive trivia generation flow"""
    print_banner()
    
    try:
        # Get user input
        num_questions = get_user_input()
        
        print(f"\n🚀 Starting generation of {num_questions} trivia questions...")
        print("⏱️  Estimated time: 2-5 minutes depending on complexity")
        print()
        
        # Step 1: Generate trivia with Gemini
        dataset_uri = await generate_trivia_with_progress(num_questions)
        
        # Step 2: Setup GCS structure
        job_path = setup_job_structure()
        
        # Step 3: Save trivia to GCS
        csv_path = save_trivia_to_gcs(dataset_uri, job_path)
        
        # Step 4: Create job manifest
        manifest = create_job_manifest(job_path, csv_path, "dataset")
        
        # Step 5: Process video generation
        final_video_path = process_video_job_with_progress(manifest, num_questions)
        
        # Success summary
        print_success_summary(manifest, final_video_path, num_questions)
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Check environment
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY environment variable is required")
        print("Set it with: export GEMINI_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Run the interactive pipeline
    asyncio.run(main())
