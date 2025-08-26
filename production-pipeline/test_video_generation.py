#!/usr/bin/env python3
"""
🎬 Test Suite for Video Generation
Test video generation with different question counts and configurations
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Add core modules to path
sys.path.append(str(Path(__file__).parent / "core"))

from cloud_video_generator_fixed import JobInfo, process_job
from google.cloud import storage

# Configuration
GCS_JOBS_BUCKET = "trivia-automation"

def create_test_csv(questions: int, output_path: str):
    """Create a test CSV with the specified number of questions"""
    print(f"📝 Creating test CSV with {questions} questions...")
    
    import csv
    
    # Sample question data
    sample_questions = [
        {
            "question": "What is the largest mammal on Earth?",
            "option_a": "African Elephant",
            "option_b": "Blue Whale",
            "option_c": "Giraffe",
            "option_d": "Hippopotamus",
            "correct_answer": "Blue Whale",
            "category": "Animals",
            "difficulty": "Easy"
        },
        {
            "question": "Which planet is known as the Red Planet?",
            "option_a": "Venus",
            "option_b": "Mars",
            "option_c": "Jupiter",
            "option_d": "Saturn",
            "correct_answer": "Mars",
            "category": "Space",
            "difficulty": "Easy"
        },
        {
            "question": "What year did World War II end?",
            "option_a": "1943",
            "option_b": "1944",
            "option_c": "1945",
            "option_d": "1946",
            "correct_answer": "1945",
            "category": "History",
            "difficulty": "Medium"
        },
        {
            "question": "Which country is home to the Taj Mahal?",
            "option_a": "China",
            "option_b": "India",
            "option_c": "Pakistan",
            "option_d": "Bangladesh",
            "correct_answer": "India",
            "category": "Geography",
            "difficulty": "Medium"
        },
        {
            "question": "What is the largest ocean on Earth?",
            "option_a": "Atlantic Ocean",
            "option_b": "Indian Ocean",
            "option_c": "Pacific Ocean",
            "option_d": "Arctic Ocean",
            "correct_answer": "Pacific Ocean",
            "category": "Geography",
            "difficulty": "Easy"
        },
        {
            "question": "Who painted the Mona Lisa?",
            "option_a": "Vincent van Gogh",
            "option_b": "Pablo Picasso",
            "option_c": "Leonardo da Vinci",
            "option_d": "Michelangelo",
            "correct_answer": "Leonardo da Vinci",
            "category": "Art",
            "difficulty": "Medium"
        },
        {
            "question": "What is the chemical symbol for gold?",
            "option_a": "Ag",
            "option_b": "Au",
            "option_c": "Fe",
            "option_d": "Cu",
            "correct_answer": "Au",
            "category": "Science",
            "difficulty": "Easy"
        },
        {
            "question": "Which sport is known as 'The Beautiful Game'?",
            "option_a": "Basketball",
            "option_b": "Tennis",
            "option_c": "Soccer",
            "option_d": "Baseball",
            "correct_answer": "Soccer",
            "category": "Sports",
            "difficulty": "Easy"
        },
        {
            "question": "What is the capital of Australia?",
            "option_a": "Sydney",
            "option_b": "Melbourne",
            "option_c": "Canberra",
            "option_d": "Brisbane",
            "correct_answer": "Canberra",
            "category": "Geography",
            "difficulty": "Medium"
        },
        {
            "question": "How many sides does a hexagon have?",
            "option_a": "5",
            "option_b": "6",
            "option_c": "7",
            "option_d": "8",
            "correct_answer": "6",
            "category": "Mathematics",
            "difficulty": "Easy"
        }
    ]
    
    # Use only the requested number of questions
    selected_questions = sample_questions[:questions]
    
    # Write to CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        if selected_questions:
            fieldnames = selected_questions[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(selected_questions)
    
    print(f"✅ Created test CSV with {len(selected_questions)} questions")
    return len(selected_questions)

def upload_test_csv_to_gcs(csv_path: str, job_id: str) -> str:
    """Upload test CSV to GCS and return the GCS path"""
    print(f"☁️ Uploading test CSV to GCS...")
    
    client = storage.Client()
    
    # Create jobs bucket if it doesn't exist
    try:
        bucket = client.bucket(GCS_JOBS_BUCKET)
        bucket.reload()
    except Exception:
        print(f"📦 Creating bucket: {GCS_JOBS_BUCKET}")
        bucket = client.create_bucket(GCS_JOBS_BUCKET, location="us-central1")
    
    # Upload CSV
    gcs_csv_path = f"jobs/channel-test/{job_id}/questions.csv"
    blob = bucket.blob(gcs_csv_path)
    blob.upload_from_filename(csv_path)
    
    gcs_full_path = f"gs://{GCS_JOBS_BUCKET}/{gcs_csv_path}"
    print(f"✅ CSV uploaded to: {gcs_full_path}")
    return gcs_full_path

def test_video_generation(question_count: int):
    """Test video generation with a specific number of questions"""
    print(f"\n🎬 Testing Video Generation - {question_count} Questions")
    print("=" * 60)
    
    # Create unique job ID
    from datetime import datetime
    job_id = f"test-{question_count}q-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    try:
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_csv_path = f.name
        
        create_test_csv(question_count, temp_csv_path)
        
        # Upload to GCS
        gcs_csv_path = upload_test_csv_to_gcs(temp_csv_path, job_id)
        
        # Clean up temp CSV
        os.unlink(temp_csv_path)
        
        # Create JobInfo
        job_info = JobInfo(
            job_id=job_id,
            channel="channel-test",
            gcs_csv_path=gcs_csv_path,
            output_bucket=GCS_JOBS_BUCKET,
            output_path=f"test_videos/channel-test/{job_id}/final_video.mp4"
        )
        
        print(f"🚀 Starting video generation for {question_count} questions...")
        print(f"📁 Output will be: {job_info.output_path}")
        
        # Process the job
        output_path = process_job(job_info)
        
        print(f"✅ Video generation completed: {output_path}")
        
        # Verify the output
        verify_video_output(output_path, question_count)
        
        return output_path
        
    except Exception as e:
        print(f"❌ Video generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def verify_video_output(output_path: str, expected_questions: int):
    """Verify the generated video output"""
    print(f"\n🔍 Verifying Video Output")
    print("=" * 60)
    
    try:
        client = storage.Client()
        
        if output_path.startswith("gs://"):
            parts = output_path.split("/")
            bucket_name = parts[2]
            file_path = "/".join(parts[3:])
            
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(file_path)
            
            # Check if file exists and get metadata
            if blob.exists():
                blob.reload()
                size_mb = blob.size / (1024 * 1024)
                print(f"✅ Video file exists: {output_path}")
                print(f"📊 File size: {size_mb:.2f} MB")
                print(f"🕒 Created: {blob.time_created}")
                
                # Check if it's a reasonable size (should be > 1MB for any video)
                if size_mb > 1:
                    print(f"✅ File size looks reasonable for {expected_questions} questions")
                else:
                    print(f"⚠️  File size seems small for {expected_questions} questions")
                    
            else:
                print(f"❌ Video file not found: {output_path}")
                
        else:
            print(f"⚠️  Invalid output path format: {output_path}")
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")

def main():
    """Main test runner"""
    print("🎬 Video Generation Test Suite")
    print("=" * 60)
    
    # Test different question counts
    test_cases = [3, 5, 7, 10]
    
    results = {}
    
    for question_count in test_cases:
        print(f"\n{'='*20} Testing {question_count} Questions {'='*20}")
        
        # Test video generation
        output_path = test_video_generation(question_count)
        
        if output_path:
            results[question_count] = "✅ PASS"
            print(f"\n📊 Test Result: ✅ PASS")
        else:
            results[question_count] = "❌ FAIL"
            print(f"\n📊 Test Result: ❌ FAIL")
        
        print("\n" + "-"*60)
    
    # Summary
    print(f"\n🎯 Test Summary")
    print("=" * 60)
    for question_count, result in results.items():
        print(f"   {question_count} Questions: {result}")

if __name__ == "__main__":
    main()
