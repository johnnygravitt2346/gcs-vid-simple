#!/usr/bin/env python3
"""
Integration script showing how Gemini Feeder works with the video pipeline.

This script demonstrates the complete flow:
1. Generate trivia dataset using Gemini Feeder
2. Use the generated dataset with the video pipeline
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gemini_feeder import GeminiFeeder, FeederRequest

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

async def generate_and_process_dataset():
    """Generate a dataset and show how it integrates with the pipeline."""
    print("=" * 80)
    print("GEMINI FEEDER + VIDEO PIPELINE INTEGRATION")
    print("=" * 80)
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ No GEMINI_API_KEY environment variable set")
        print("Please set it with: export GEMINI_API_KEY='your_key_here'")
        return
    
    try:
        # Step 1: Initialize Gemini Feeder
        print("\n1️⃣ Initializing Gemini Feeder...")
        feeder = GeminiFeeder(api_key=api_key)
        print("✅ Gemini Feeder initialized")
        
        # Step 2: Generate dataset
        print("\n2️⃣ Generating trivia dataset...")
        request = FeederRequest(
            channel_id="ch01",
            prompt_preset="science_tech",
            quantity=5,  # Small dataset for demo
            difficulty="medium",
            style="engaging",
            tags=["demo", "integration"],
            max_question_length=150,
            max_option_length=80
        )
        
        print(f"   Channel: {request.channel_id}")
        print(f"   Preset: {request.prompt_preset}")
        print(f"   Quantity: {request.quantity}")
        print(f"   Difficulty: {request.difficulty}")
        
        dataset_uri = await feeder.generate_dataset(request)
        print(f"✅ Dataset generated: {dataset_uri}")
        
        # Step 3: Show pipeline integration
        print("\n3️⃣ Pipeline Integration Points")
        print("   The generated dataset can now be used with:")
        print("   - Video generation pipeline")
        print("   - Individual clip creation")
        print("   - Final video concatenation")
        
        # Step 4: Show the files created
        print("\n4️⃣ Generated Files")
        csv_uri = f"{dataset_uri}/questions.csv"
        manifest_uri = f"{dataset_uri}/_DATASET.json"
        
        print(f"   📊 Questions CSV: {csv_uri}")
        print(f"   📋 Dataset Manifest: {manifest_uri}")
        
        # Step 5: Show how to use with video pipeline
        print("\n5️⃣ Video Pipeline Usage")
        print("   The video pipeline can now:")
        print("   - Download questions.csv from GCS")
        print("   - Process each question/answer pair")
        print("   - Generate individual video clips")
        print("   - Concatenate into final video")
        
        # Step 6: Example pipeline command
        print("\n6️⃣ Example Pipeline Command")
        print("   Once you have the dataset, you can run:")
        print(f"   python scripts/run_trivia_pipeline.py --csv {csv_uri}")
        print("   or")
        print(f"   python scripts/trivia_video_generator.py --csv {csv_uri}")
        
        print("\n" + "=" * 80)
        print("🎉 INTEGRATION COMPLETE!")
        print("=" * 80)
        print(f"\nYour dataset is ready at: {dataset_uri}")
        print("\nNext steps:")
        print("1. Verify the dataset files in GCS")
        print("2. Run the video pipeline with the generated CSV")
        print("3. Check the final video output")
        
    except Exception as e:
        print(f"❌ Error during integration: {e}")
        logging.error(f"Integration failed: {e}")
        raise

async def main():
    """Main function."""
    setup_logging()
    await generate_and_process_dataset()

if __name__ == "__main__":
    asyncio.run(main())
