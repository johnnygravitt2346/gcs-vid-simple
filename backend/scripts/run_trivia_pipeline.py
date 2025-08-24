#!/usr/bin/env python3
"""
Trivia Factory Integrated Pipeline Runner

This script runs the complete pipeline:
1. Generate questions using Gemini AI
2. Create video clips for each question
3. Concatenate into final video
4. Upload results to GCS

Usage:
    python3 run_trivia_pipeline.py --topic "Space Exploration" --difficulty "Medium" --count 5
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.gemini_generator import GeminiQuestionGenerator, QuestionGenerationRequest
from src.video_generator import VideoGenerator

class TriviaPipelineRunner:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_dir = config.get('output_dir', './output')
        self.assets_dir = config.get('assets_dir', './assets')
        
        # Ensure output directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'questions'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'videos'), exist_ok=True)
        
        # Initialize components
        self.gemini_generator = GeminiQuestionGenerator(
            api_key=config['gemini_api_key'],
            project_id=config['gcp_project_id']
        )
        
        self.video_generator = VideoGenerator(config)
    
    async def run_pipeline(self, topic: str, difficulty: str, count: int, category: str = "General") -> Dict[str, Any]:
        """Run the complete trivia pipeline."""
        start_time = time.time()
        pipeline_id = f"pipeline_{int(start_time)}"
        
        logger.info(f"Starting pipeline {pipeline_id} for topic: {topic}")
        
        try:
            # Step 1: Generate questions with Gemini
            logger.info("Step 1: Generating questions with Gemini AI...")
            questions = await self._generate_questions(topic, difficulty, count, category)
            
            if not questions:
                raise RuntimeError("No questions were generated")
            
            logger.info(f"Generated {len(questions)} questions successfully")
            
            # Step 2: Save questions to JSON
            questions_file = await self._save_questions(questions, pipeline_id)
            logger.info(f"Questions saved to: {questions_file}")
            
            # Step 3: Generate video clips
            logger.info("Step 2: Generating video clips...")
            clips = await self._generate_videos(questions, pipeline_id)
            
            logger.info(f"Generated {len(clips)} video clips")
            
            # Step 4: Concatenate final video
            logger.info("Step 3: Creating final video...")
            final_video = await self._create_final_video(clips, pipeline_id)
            
            # Step 5: Upload to GCS if configured
            if self.config.get('upload_to_gcs', False):
                logger.info("Step 4: Uploading to Google Cloud Storage...")
                await self._upload_to_gcs(pipeline_id, questions_file, final_video)
            
            # Calculate timing
            duration = time.time() - start_time
            
            # Prepare results
            results = {
                'pipeline_id': pipeline_id,
                'topic': topic,
                'difficulty': difficulty,
                'question_count': count,
                'category': category,
                'questions_generated': len(questions),
                'videos_created': len(clips),
                'final_video': final_video,
                'questions_file': questions_file,
                'duration_seconds': duration,
                'status': 'completed',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Save results summary
            results_file = os.path.join(self.output_dir, f'{pipeline_id}_results.json')
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Pipeline {pipeline_id} completed successfully in {duration:.1f} seconds")
            return results
            
        except Exception as e:
            duration = time.time() - start_time
            error_results = {
                'pipeline_id': pipeline_id,
                'topic': topic,
                'difficulty': difficulty,
                'question_count': count,
                'category': category,
                'status': 'failed',
                'error': str(e),
                'duration_seconds': duration,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.error(f"Pipeline {pipeline_id} failed: {e}")
            return error_results
    
    async def _generate_questions(self, topic: str, difficulty: str, count: int, category: str) -> List[Dict[str, Any]]:
        """Generate questions using Gemini AI."""
        request = QuestionGenerationRequest(
            topic=topic,
            difficulty=difficulty,
            question_count=count,
            category=category
        )
        
        questions = await self.gemini_generator.generate_questions(request)
        
        # Convert to dictionary format for video generation
        questions_dict = []
        for i, q in enumerate(questions):
            question_dict = {
                'id': f'q_{i+1:03d}',
                'question': q.question,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'correct_answer': q.correct_answer,
                'explanation': q.explanation,
                'category': q.category,
                'difficulty': q.difficulty
            }
            questions_dict.append(question_dict)
        
        return questions_dict
    
    async def _save_questions(self, questions: List[Dict[str, Any]], pipeline_id: str) -> str:
        """Save generated questions to JSON file."""
        questions_file = os.path.join(self.output_dir, 'questions', f'{pipeline_id}_questions.json')
        
        with open(questions_file, 'w', encoding='utf-8') as f:
            json.dump({
                'pipeline_id': pipeline_id,
                'generated_at': datetime.utcnow().isoformat(),
                'questions': questions
            }, f, indent=2, ensure_ascii=False)
        
        return questions_file
    
    async def _generate_videos(self, questions: List[Dict[str, Any]], pipeline_id: str) -> List[Any]:
        """Generate video clips for all questions."""
        video_output_dir = os.path.join(self.output_dir, 'videos', pipeline_id)
        
        request = VideoGenerator.VideoGenerationRequest(
            questions=questions,
            template_path=self.assets_dir,
            output_dir=video_output_dir,
            font_path=self.config.get('font_path', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
            quality=self.config.get('video_quality', 'medium'),
            fps=self.config.get('video_fps', 30)
        )
        
        clips = await self.video_generator.generate_videos(request)
        return clips
    
    async def _create_final_video(self, clips: List[Any], pipeline_id: str) -> str:
        """Concatenate all clips into final video."""
        video_output_dir = os.path.join(self.output_dir, 'videos', pipeline_id)
        final_video = os.path.join(video_output_dir, 'final_video.mp4')
        
        # Filter completed clips
        completed_clips = [clip for clip in clips if clip.status == 'completed']
        
        if not completed_clips:
            raise RuntimeError("No completed video clips to concatenate")
        
        final_video_path = await self.video_generator.concatenate_final_video(
            completed_clips, final_video
        )
        
        return final_video_path
    
    async def _upload_to_gcs(self, pipeline_id: str, questions_file: str, final_video: str):
        """Upload results to Google Cloud Storage."""
        try:
            from google.cloud import storage
            
            client = storage.Client()
            bucket_name = self.config.get('gcs_bucket')
            if not bucket_name:
                logger.warning("GCS bucket not configured, skipping upload")
                return
            
            bucket = client.bucket(bucket_name)
            
            # Upload questions
            questions_blob = bucket.blob(f'pipelines/{pipeline_id}/questions.json')
            questions_blob.upload_from_filename(questions_file)
            logger.info(f"Uploaded questions to GCS: gs://{bucket_name}/pipelines/{pipeline_id}/questions.json")
            
            # Upload final video
            video_blob = bucket.blob(f'pipelines/{pipeline_id}/final_video.mp4')
            video_blob.upload_from_filename(final_video)
            logger.info(f"Uploaded video to GCS: gs://{bucket_name}/pipelines/{pipeline_id}/final_video.mp4")
            
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {e}")
            raise

async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Trivia Factory Pipeline")
    parser.add_argument("--topic", required=True, help="Topic for trivia questions")
    parser.add_argument("--difficulty", default="Medium", choices=["Easy", "Medium", "Hard"], help="Question difficulty")
    parser.add_argument("--count", type=int, default=5, help="Number of questions to generate")
    parser.add_argument("--category", default="General", help="Question category")
    parser.add_argument("--config", default="config/pipeline_config.json", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Load configuration
    config_path = args.config
    if not os.path.exists(config_path):
        print(f"Configuration file not found: {config_path}")
        print("Please create a configuration file or use environment variables")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Create and run pipeline
    runner = TriviaPipelineRunner(config)
    results = await runner.run_pipeline(
        topic=args.topic,
        difficulty=args.difficulty,
        count=args.count,
        category=args.category
    )
    
    # Print results
    if results['status'] == 'completed':
        print("\n" + "="*60)
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Pipeline ID: {results['pipeline_id']}")
        print(f"Topic: {results['topic']}")
        print(f"Questions: {results['questions_generated']}")
        print(f"Videos: {results['videos_created']}")
        print(f"Duration: {results['duration_seconds']:.1f} seconds")
        print(f"Final Video: {results['final_video']}")
        print(f"Questions File: {results['questions_file']}")
        print("="*60)
    else:
        print(f"\n❌ Pipeline failed: {results.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
