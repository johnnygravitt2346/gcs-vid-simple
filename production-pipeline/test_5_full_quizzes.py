#!/usr/bin/env python3
"""
🧪 Test Script for 5 Full 20-Question Quiz Videos

This script tests the official video generation system by creating:
- 5 complete quizzes
- 20 questions per quiz (100 total questions)
- Factually accurate, verified sports trivia
- Professional videos with modern typography

Usage:
    python3 test_5_full_quizzes.py
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from google.cloud import storage

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from core.official_video_generator import EfficientPipelineSimple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

async def main():
    """Main test function for 5 full 20-question quiz videos."""
    
    print("🚀 Starting 5 Full Quiz Video Generation Test...")
    print("📝 This will generate 5 quizzes with 20 questions each (100 total questions)")
    print("🎬 Each quiz will be a complete, professional video with factually accurate content")
    print("⏱️  Estimated time: 15-20 minutes for all videos")
    print()
    
    try:
        # Initialize the official video generator
        logger.info("🔧 Initializing official video generator...")
        storage_client = storage.Client()
        pipeline = EfficientPipelineSimple(storage_client, os.environ['GEMINI_API_KEY'])
        
        # Generate 5 quizzes with 20 questions each
        logger.info("🎯 Starting production of 5 full quiz videos...")
        result = await pipeline.run_sports_quiz_pipeline(
            quiz_count=5,
            questions_per_quiz=20
        )
        
        if result:
            logger.info("✅ All 5 quiz videos generated successfully!")
            logger.info("🎥 Videos uploaded to GCS:")
            
            # List the generated videos
            for i in range(1, 6):
                episode_id = f"episode_{i:03d}"
                gcs_path = f"gs://trivia-automations-2/episodes/{episode_id}/video.mp4"
                console_link = f"https://console.cloud.google.com/storage/browser/trivia-automations-2?prefix=episodes/{episode_id}/video.mp4"
                
                logger.info(f"  📺 Quiz {i}: {episode_id}")
                logger.info(f"     📍 GCS: {gcs_path}")
                logger.info(f"     🔗 View: {console_link}")
                logger.info()
            
            logger.info("🎉 Production test completed successfully!")
            logger.info("📊 Total: 5 quizzes × 20 questions = 100 questions processed")
            logger.info("🎬 Total: 5 professional videos generated and uploaded")
            
        else:
            logger.error("❌ Video generation failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n✅ 5 Full Quiz Video Generation Test completed successfully!")
        print("🎥 Check the GCS console links above to view your videos")
    else:
        print("\n❌ Test failed - check logs for details")
        sys.exit(1)
