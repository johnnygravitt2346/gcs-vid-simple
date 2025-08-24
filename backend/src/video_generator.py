#!/usr/bin/env python3
"""
Video Generator for Trivia Factory

Integrates with the existing ffmpeg video creation script to generate
individual clips and final videos using NVENC on preemptible T4 workers.
Now works directly with Gemini-generated questions without CSV conversion.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import csv

logger = logging.getLogger(__name__)

@dataclass
class VideoGenerationRequest:
    questions: List[Dict[str, Any]]
    template_path: str
    output_dir: str
    font_path: str
    resolution: str = "1920x1080"
    fps: int = 30
    quality: str = "medium"

@dataclass
class VideoClip:
    question_id: str
    question_path: str
    answer_path: str
    combined_path: str
    duration: float
    status: str

class VideoGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.temp_dir = tempfile.mkdtemp(prefix="trivia_video_")
        
        # Video generation settings
        self.codec = "h264_nvenc" if self._check_nvenc_available() else "libx264"
        self.quality_presets = {
            "low": {"crf": 28, "preset": "fast"},
            "medium": {"crf": 23, "preset": "medium"},
            "high": {"crf": 18, "preset": "slow"}
        }
    
    def _check_nvenc_available(self) -> bool:
        """Check if NVENC is available on this system."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-encoders"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return "h264_nvenc" in result.stdout
        except Exception:
            return False
    
    async def generate_videos(self, request: VideoGenerationRequest) -> List[VideoClip]:
        """Generate video clips for all questions."""
        logger.info(f"Generating videos for {len(request.questions)} questions")
        
        clips = []
        
        for question in request.questions:
            try:
                clip = await self._generate_single_clip(question, request)
                clips.append(clip)
            except Exception as e:
                logger.error(f"Failed to generate clip for question {question.get('id', 'unknown')}: {e}")
                # Create error clip
                error_clip = VideoClip(
                    question_id=question.get('id', 'error'),
                    question_path="",
                    answer_path="",
                    combined_path="",
                    duration=0.0,
                    status="error"
                )
                clips.append(error_clip)
        
        return clips
    
    async def _generate_single_clip(self, question: Dict[str, Any], request: VideoGenerationRequest) -> VideoClip:
        """Generate a single question-answer clip."""
        question_id = question.get('id', 'unknown')
        logger.info(f"Generating clip for question {question_id}")
        
        # Create temporary CSV for the video generation script
        csv_path = await self._create_question_csv(question, request.output_dir)
        
        # Prepare video generation command
        cmd = [
            "python3", "scripts/trivia_video_generator.py",
            "--csv", csv_path,
            "--templates_dir", request.template_path,
            "--font", request.font_path,
            "--out_dir", os.path.join(request.output_dir, f"clip_{question_id}"),
            "--limit", "1"
        ]
        
        # Execute video generation
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                # Video generated successfully
                output_dir = os.path.join(request.output_dir, f"clip_{question_id}")
                question_path = os.path.join(output_dir, "output", "question_001.mp4")
                answer_path = os.path.join(output_dir, "output", "answer_001.mp4")
                combined_path = os.path.join(output_dir, "output", "individual_clips", "clip_001.mp4")
                
                # Get video duration
                duration = self._get_video_duration(combined_path)
                
                clip = VideoClip(
                    question_id=question_id,
                    question_path=question_path,
                    answer_path=answer_path,
                    combined_path=combined_path,
                    duration=duration,
                    status="completed"
                )
                
                logger.info(f"Successfully generated clip for question {question_id}")
                return clip
                
            else:
                logger.error(f"Video generation failed for question {question_id}: {result.stderr}")
                raise RuntimeError(f"Video generation failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error(f"Video generation timed out for question {question_id}")
            raise RuntimeError("Video generation timed out")
        
        except Exception as e:
            logger.error(f"Unexpected error generating video for question {question_id}: {e}")
            raise
    
    async def _create_question_csv(self, question: Dict[str, Any], output_dir: str) -> str:
        """Create a CSV file for a single question from Gemini-generated data."""
        csv_path = os.path.join(self.temp_dir, f"question_{question.get('id', 'unknown')}.csv")
        
        # Map Gemini question format to CSV format expected by video generator
        csv_data = [
            {
                "Question": question.get('question', ''),
                "A": question.get('option_a', ''),
                "B": question.get('option_b', ''),
                "C": question.get('option_c', ''),
                "D": question.get('option_d', ''),
                "Correct Answer:": question.get('correct_answer', ''),
                "Explanation": question.get('explanation', '')
            }
        ]
        
        # Write CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
        
        return csv_path
    
    def _get_video_duration(self, video_path: str) -> float:
        """Get the duration of a video file using ffprobe."""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                 "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                return 0.0
                
        except Exception:
            return 0.0
    
    async def concatenate_final_video(self, clips: List[VideoClip], output_path: str, 
                                    intro_path: Optional[str] = None, 
                                    outro_path: Optional[str] = None) -> str:
        """Concatenate all clips into a final video."""
        logger.info(f"Concatenating {len(clips)} clips into final video")
        
        # Prepare file list for ffmpeg concat
        file_list_path = os.path.join(self.temp_dir, "concat_list.txt")
        
        with open(file_list_path, 'w') as f:
            # Add intro if provided
            if intro_path and os.path.exists(intro_path):
                f.write(f"file '{intro_path}'\n")
            
            # Add all clips
            for clip in clips:
                if clip.status == "completed" and os.path.exists(clip.combined_path):
                    f.write(f"file '{clip.combined_path}'\n")
            
            # Add outro if provided
            if outro_path and os.path.exists(outro_path):
                f.write(f"file '{outro_path}'\n")
        
        # Execute ffmpeg concat
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", file_list_path,
            "-c", "copy",
            output_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully created final video: {output_path}")
                return output_path
            else:
                logger.error(f"Video concatenation failed: {result.stderr}")
                raise RuntimeError(f"Video concatenation failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("Video concatenation timed out")
            raise RuntimeError("Video concatenation timed out")
        
        except Exception as e:
            logger.error(f"Unexpected error during video concatenation: {e}")
            raise
    
    def cleanup(self):
        """Clean up temporary files."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary files")
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary files: {e}")

# Example usage
async def main():
    config = {
        "video": {
            "quality": "medium",
            "fps": 30,
            "resolution": "1920x1080"
        }
    }
    
    generator = VideoGenerator(config)
    
    # Sample Gemini-generated question
    questions = [{
        "id": "q1",
        "question": "What is the capital of France?",
        "option_a": "London",
        "option_b": "Berlin", 
        "option_c": "Paris",
        "option_d": "Madrid",
        "correct_answer": "C",
        "explanation": "Paris is the capital of France."
    }]
    
    request = VideoGenerationRequest(
        questions=questions,
        template_path="./assets",
        output_dir="./output",
        font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    
    try:
        clips = await generator.generate_videos(request)
        print(f"Generated {len(clips)} video clips")
        
        # Concatenate final video
        final_video = await generator.concatenate_final_video(
            clips, "./output/final_video.mp4"
        )
        print(f"Final video created: {final_video}")
        
    finally:
        generator.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
