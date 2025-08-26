#!/usr/bin/env python3
"""
🧠 Test Suite for Gemini Feeder
Test question generation with retry logic and validation
"""

import asyncio
import os
import sys
import json
import tempfile
from pathlib import Path

# Add core modules to path
sys.path.append(str(Path(__file__).parent / "core"))

from gemini_feeder_fixed import GeminiFeederFixed, FeederRequest
from google.cloud import storage

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def test_gemini_generation(target_questions: int, max_retries: int = 5):
    """Test Gemini question generation with retry logic"""
    
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY environment variable is required")
        print("Set it with: export GEMINI_API_KEY='your-api-key'")
        return None
    
    print(f"🧠 Testing Gemini Feeder - Target: {target_questions} questions")
    print("=" * 60)
    
    async def generate_with_retry():
        feeder = GeminiFeederFixed(api_key=GEMINI_API_KEY)
        
        for attempt in range(1, max_retries + 1):
            print(f"\n📝 Attempt {attempt}/{max_retries}")
            print(f"🎯 Requesting {target_questions} sports trivia questions...")
            
            # Create feeder request
            feeder_request = FeederRequest(
                channel_id="channel-test",
                prompt_preset="sports",
                quantity=target_questions,
                difficulty="medium",
                language_filter="en"
            )
            
            try:
                # Generate trivia dataset
                dataset_uri = await feeder.generate_dataset(feeder_request)
                print(f"✅ Generated dataset: {dataset_uri}")
                
                # Verify question count
                actual_count = verify_question_count(dataset_uri)
                
                if actual_count >= target_questions:
                    print(f"🎉 SUCCESS! Generated {actual_count} questions (≥ {target_questions} requested)")
                    return dataset_uri, actual_count
                else:
                    print(f"❌ Only got {actual_count} questions, need {target_questions}")
                    if attempt < max_retries:
                        print(f"🔄 Retrying... (attempt {attempt + 1}/{max_retries})")
                        continue
                    else:
                        print(f"⚠️  Maximum retries reached. Best result: {actual_count} questions")
                        return dataset_uri, actual_count
                        
            except Exception as e:
                print(f"❌ Generation failed: {e}")
                if attempt < max_retries:
                    print(f"🔄 Retrying... (attempt {attempt + 1}/{max_retries})")
                    continue
                else:
                    print(f"💥 All attempts failed")
                    return None, 0
    
    return asyncio.run(generate_with_retry())

def verify_question_count(dataset_uri: str) -> int:
    """Verify the actual number of questions generated"""
    print(f"🔍 Verifying question count from: {dataset_uri}")
    
    try:
        client = storage.Client()
        
        if dataset_uri.startswith("gs://"):
            parts = dataset_uri.split("/")
            source_bucket = parts[2]
            source_path = "/".join(parts[3:])
            csv_source_path = f"{source_path}/questions.csv"
            
            source_bucket_obj = client.bucket(source_bucket)
            source_blob = source_bucket_obj.blob(csv_source_path)
            
            # Download and count questions
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                csv_content = source_blob.download_as_text()
                f.write(csv_content)
                temp_csv_path = f.name
            
            # Count questions
            import csv
            with open(temp_csv_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                actual_count = len(rows)
            
            # Clean up temp file
            os.unlink(temp_csv_path)
            
            print(f"📊 Found {actual_count} questions in dataset")
            return actual_count
            
        else:
            print(f"⚠️  Invalid dataset URI format: {dataset_uri}")
            return 0
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return 0

def test_question_quality(dataset_uri: str):
    """Test the quality of generated questions"""
    print(f"\n🔍 Testing Question Quality")
    print("=" * 60)
    
    try:
        client = storage.Client()
        
        if dataset_uri.startswith("gs://"):
            parts = dataset_uri.split("/")
            source_bucket = parts[2]
            source_path = "/".join(parts[3:])
            csv_source_path = f"{source_path}/questions.csv"
            
            source_bucket_obj = client.bucket(source_bucket)
            source_blob = source_bucket_obj.blob(csv_source_path)
            
            # Download and analyze questions
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                csv_content = source_blob.download_as_text()
                f.write(csv_content)
                temp_csv_path = f.name
            
            # Analyze questions
            import csv
            with open(temp_csv_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                print(f"📊 Total Questions: {len(rows)}")
                
                for i, row in enumerate(rows, 1):
                    print(f"\n🎯 Question {i}:")
                    print(f"   📝 Question: {row.get('question', 'N/A')[:100]}...")
                    print(f"   ✅ Answer: {row.get('correct_answer', 'N/A')}")
                    print(f"   🎲 Options: A) {row.get('option_a', 'N/A')} | B) {row.get('option_b', 'N/A')} | C) {row.get('option_c', 'N/A')} | D) {row.get('option_d', 'N/A')}")
                    print(f"   🏷️  Category: {row.get('category', 'N/A')}")
                    print(f"   ⭐ Difficulty: {row.get('difficulty', 'N/A')}")
            
            # Clean up temp file
            os.unlink(temp_csv_path)
            
        else:
            print(f"⚠️  Invalid dataset URI format: {dataset_uri}")
            
    except Exception as e:
        print(f"❌ Quality test failed: {e}")

def main():
    """Main test runner"""
    print("🧠 Gemini Feeder Test Suite")
    print("=" * 60)
    
    # Test different question counts
    test_cases = [3, 5, 7, 10]
    
    for target in test_cases:
        print(f"\n{'='*20} Testing {target} Questions {'='*20}")
        
        # Test generation
        dataset_uri, actual_count = test_gemini_generation(target, max_retries=3)
        
        if dataset_uri:
            # Test quality
            test_question_quality(dataset_uri)
            
            # Summary
            success_rate = "✅ PASS" if actual_count >= target else "⚠️  PARTIAL"
            print(f"\n📊 Test Result: {success_rate}")
            print(f"   Requested: {target} | Generated: {actual_count}")
        else:
            print(f"\n❌ Test Failed: Could not generate questions")
        
        print("\n" + "-"*60)

if __name__ == "__main__":
    main()
