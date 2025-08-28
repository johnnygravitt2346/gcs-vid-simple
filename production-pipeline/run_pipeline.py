#!/usr/bin/env python3
"""
Interactive Sports Trivia Pipeline Runner
A user-friendly interface to run the complete pipeline from start to finish.
"""

import asyncio
import os
import sys
import logging
from google.cloud import storage
from src.core.official_video_generator import EfficientPipelineSimple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import configuration
try:
    from config import GEMINI_API_KEY, GCS_BUCKET_NAME, GCS_PROJECT_ID
except ImportError:
    print("❌ config.py not found! Please create it with your API key.")
    print("   See config.py.example for reference.")
    sys.exit(1)

class InteractivePipeline:
    def __init__(self):
        self.storage_client = None
        self.pipeline = None
        self.generated_videos = []
        
    def print_welcome(self):
        """Display welcome message and pipeline information."""
        print("=" * 80)
        print("🎯 WELCOME TO THE SPORTS TRIVIA VIDEO PIPELINE! 🎯")
        print("=" * 80)
        print()
        print("This pipeline will:")
        print("  🎬 Generate unique sports trivia questions")
        print("  🎥 Create professional video content")
        print("  ☁️  Upload everything to Google Cloud Storage")
        print("  🔗 Provide you with direct video links")
        print()
        print("Supported Sports: Basketball, Football, Baseball, Soccer, Hockey")
        print("Supported Difficulties: Easy (1), Medium (2), Hard (3)")
        print("🎬 Video Count: Unlimited (with confirmation for large batches)")
        print()
        print(f"🔑 API Key: {'✅ Configured' if GEMINI_API_KEY != 'AIzaSyBQJQJQJQJQJQJQJQJQJQJQJQJQJQJQJQ' else '❌ NOT SET - Please update the script'}")
        print(f"☁️  GCS Bucket: {GCS_BUCKET_NAME}")
        print()
        
    def get_user_input(self):
        """Get user preferences for the pipeline."""
        print("📋 PIPELINE CONFIGURATION")
        print("-" * 40)
        
        # Get number of quiz videos
        while True:
            try:
                quiz_count = input("How many quiz videos would you like to create? (1-100): ").strip()
                quiz_count = int(quiz_count)
                if 1 <= quiz_count <= 100:
                    break
                elif quiz_count > 100:
                    print("⚠️  That's a lot of videos! Are you sure? Type 'yes' to confirm:")
                    confirm = input().strip().lower()
                    if confirm == 'yes':
                        break
                    else:
                        print("Please enter a smaller number.")
                else:
                    print("❌ Please enter a number greater than 0.")
            except ValueError:
                print("❌ Please enter a valid number.")
        
        # Get questions per video
        while True:
            try:
                questions_per_quiz = input("How many questions in each video? (10-50): ").strip()
                questions_per_quiz = int(questions_per_quiz)
                if 10 <= questions_per_quiz <= 50:
                    break
                else:
                    print("❌ Please enter a number between 10 and 50.")
            except ValueError:
                print("❌ Please enter a valid number.")
        
        # Get difficulty level
        while True:
            difficulty_input = input("What level of difficulty? (Easy/Medium/Hard or 1/2/3): ").strip().lower()
            if difficulty_input in ['easy', '1']:
                difficulty = 1
                difficulty_name = "Easy"
                break
            elif difficulty_input in ['medium', '2']:
                difficulty = 2
                difficulty_name = "Medium"
                break
            elif difficulty_input in ['hard', '3']:
                difficulty = 3
                difficulty_name = "Hard"
                break
            else:
                print("❌ Please enter Easy/Medium/Hard or 1/2/3.")
        
        # Display summary
        print()
        print("📊 PIPELINE SUMMARY:")
        print(f"  🎬 Quiz Videos: {quiz_count}")
        print(f"  📝 Questions per Video: {questions_per_quiz}")
        print(f"  🎯 Difficulty: {difficulty_name} (Level {difficulty})")
        print(f"  🏆 Total Questions: {quiz_count * questions_per_quiz}")
        print()
        
        # Confirm execution
        while True:
            run_choice = input("Run pipeline? (y/n): ").strip().lower()
            if run_choice in ['y', 'yes']:
                return quiz_count, questions_per_quiz, difficulty, difficulty_name
            elif run_choice in ['n', 'no']:
                print("❌ Pipeline cancelled. Goodbye!")
                sys.exit(0)
            else:
                print("❌ Please enter y or n.")
    
    def check_environment(self):
        """Check if all required environment variables are set."""
        print("🔍 Checking environment...")
        
        # Check if API key is properly configured
        if GEMINI_API_KEY == "AIzaSyBQJQJQJQJQJQJQJQJQJQJQJQJQJQJQJQ":
            print("❌ GEMINI_API_KEY is not configured!")
            print("   Please update the GEMINI_API_KEY variable at the top of this script")
            print("   with your actual Gemini API key.")
            return False
        
        try:
            self.storage_client = storage.Client()
            print("✅ Google Cloud Storage client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Google Cloud Storage: {e}")
            return False
        
        try:
            self.pipeline = EfficientPipelineSimple(self.storage_client, GEMINI_API_KEY)
            print("✅ Pipeline initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize pipeline: {e}")
            return False
        
        print("✅ Environment check passed!")
        return True
    
    async def run_pipeline(self, quiz_count, questions_per_quiz, difficulty, difficulty_name):
        """Run the complete pipeline."""
        print()
        print("🚀 STARTING PIPELINE EXECUTION")
        print("=" * 50)
        
        # Sports to cycle through for variety
        sports = ['basketball', 'football', 'baseball', 'soccer', 'hockey']
        
        for quiz_num in range(quiz_count):
            print(f"\n🎯 GENERATING QUIZ {quiz_num + 1}/{quiz_count}")
            print("-" * 40)
            
            sport = sports[quiz_num % len(sports)]
            print(f"🏆 Sport: {sport.title()}")
            print(f"🎯 Difficulty: {difficulty_name}")
            print(f"📝 Target Questions: {questions_per_quiz}")
            
            # Clear any existing data for this quiz
            self.pipeline.spec_registry.clear()
            self.pipeline.coverage_counters.clear()
            self.pipeline.banlist.clear()
            
            # Generate specs
            print("📋 Generating question specifications...")
            specs = await self.pipeline._generate_spec_batch_simple(sport, difficulty, questions_per_quiz)
            
            if not specs:
                print(f"❌ Failed to generate specs for quiz {quiz_num + 1}")
                continue
            
            print(f"✅ Generated {len(specs)} specs")
            
            # Generate questions with retry logic
            print("📝 Generating questions with retry logic...")
            questions = await self.pipeline._generate_questions_with_retry(specs, questions_per_quiz)
            
            if len(questions) < questions_per_quiz:
                print(f"🔄 Need {questions_per_quiz - len(questions)} more questions. Generating additional specs...")
                additional_specs = await self.pipeline._generate_spec_batch_simple(sport, difficulty, questions_per_quiz - len(questions))
                additional_questions = await self.pipeline._generate_questions_with_retry(additional_specs, questions_per_quiz - len(questions))
                questions.extend(additional_questions)
                print(f"✅ Added {len(additional_questions)} more questions")
            
            print(f"✅ Generated {len(questions)}/{questions_per_quiz} questions")
            
            # Create CSV
            csv_filename = f"quiz_{quiz_num + 1}_{sport}_{difficulty_name.lower()}.csv"
            csv_path = await self.pipeline._create_csv_from_questions(questions, csv_filename)
            
            if not csv_path:
                print(f"❌ Failed to create CSV for quiz {quiz_num + 1}")
                continue
            
            print(f"📄 CSV created: {csv_filename}")
            
            # Upload to GCS
            gcs_path = f"episodes/quiz_{quiz_num + 1}_{sport}_{difficulty_name.lower()}/{csv_filename}"
            bucket = self.storage_client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(csv_path)
            print(f"☁️  Uploaded to GCS: {gcs_path}")
            
            # Generate video
            print("🎥 Generating video...")
            video_path = await self.pipeline._generate_video_from_csv(csv_path, f"quiz_{quiz_num + 1}_{sport}_{difficulty_name.lower()}")
            
            if video_path:
                video_gcs_path = f"episodes/quiz_{quiz_num + 1}_{sport}_{difficulty_name.lower()}/video.mp4"
                video_url = f"https://console.cloud.google.com/storage/browser/{GCS_BUCKET_NAME}?prefix={video_gcs_path}"
                
                self.generated_videos.append({
                    'quiz_num': quiz_num + 1,
                    'sport': sport,
                    'difficulty': difficulty_name,
                    'questions': len(questions),
                    'video_url': video_url,
                    'gcs_path': video_gcs_path
                })
                
                print(f"✅ Video generated and uploaded!")
                print(f"🔗 View: {video_url}")
            else:
                print(f"❌ Video generation failed for quiz {quiz_num + 1}")
            
            print(f"🎉 Quiz {quiz_num + 1} completed!")
        
        print("\n🎊 PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 50)
    
    def display_results(self):
        """Display final results and video links."""
        if not self.generated_videos:
            print("❌ No videos were generated successfully.")
            return
        
        print(f"\n📊 PIPELINE RESULTS")
        print(f"✅ Successfully generated {len(self.generated_videos)} quiz videos!")
        print()
        
        print("🎬 GENERATED VIDEOS:")
        print("-" * 80)
        
        for video in self.generated_videos:
            print(f"🎯 Quiz {video['quiz_num']}: {video['sport'].title()} - {video['difficulty']}")
            print(f"   📝 Questions: {video['questions']}")
            print(f"   🔗 Video Link: {video['video_url']}")
            print(f"   📁 GCS Path: gs://{GCS_BUCKET_NAME}/{video['gcs_path']}")
            print()
        
        print("🎉 All videos are now available in your Google Cloud Storage bucket!")
        print("📱 You can view them directly in the GCS Console or download them for local use.")
        print()
        print(f"🔗 Main GCS Console: https://console.cloud.google.com/storage/browser/{GCS_BUCKET_NAME}")

async def main():
    """Main function to run the interactive pipeline."""
    pipeline = InteractivePipeline()
    
    try:
        # Welcome and configuration
        pipeline.print_welcome()
        
        # Check environment
        if not pipeline.check_environment():
            print("❌ Environment check failed. Please fix the issues above and try again.")
            return
        
        # Get user input
        quiz_count, questions_per_quiz, difficulty, difficulty_name = pipeline.get_user_input()
        
        # Run the pipeline
        await pipeline.run_pipeline(quiz_count, questions_per_quiz, difficulty, difficulty_name)
        
        # Display results
        pipeline.display_results()
        
    except KeyboardInterrupt:
        print("\n\n❌ Pipeline interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
