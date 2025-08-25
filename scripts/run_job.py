#!/usr/bin/env python3
"""
Trivia Factory Lean Runner

Single VM, single runner that processes datasets and produces videos.
No API, no UI - just pure video generation pipeline.
"""

import os
import sys
import csv
import json
import hashlib
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LeanRunner:
    """Lean video generation runner for single VM deployment."""
    
    def __init__(self):
        """Initialize the runner with environment configuration."""
        self._load_environment()
        self._validate_environment()
        self._setup_directories()
    
    def _load_environment(self):
        """Load configuration from environment variables."""
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        self.bucket = os.getenv('GCS_BUCKET')
        self.gcs_base = os.getenv('GCS_BASE')
        self.channels_root = os.getenv('GCS_CHANNELS_ROOT')
        self.datasets_root = os.getenv('GCS_DATASETS_ROOT')
        self.jobs_root = os.getenv('GCS_JOBS_ROOT')
        self.manifests_root = os.getenv('GCS_MANIFESTS_ROOT')
        self.render_root = os.getenv('RENDER_LOCAL_ROOT')
        self.channel_id = os.getenv('CHANNEL_ID')
        self.dataset_uri = os.getenv('DATASET_URI')
        self.enable_tts = os.getenv('ENABLE_TTS', '0') == '1'
        self.nvenc_required = os.getenv('NVENC_REQUIRED', '0') == '1'
        
        # Generate job ID
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        self.job_id = f"{self.channel_id}-{timestamp}"
        
        logger.info(f"Initialized runner for job: {self.job_id}")
        logger.info(f"Channel: {self.channel_id}")
        logger.info(f"Dataset: {self.dataset_uri}")
    
    def _validate_environment(self):
        """Validate required environment variables."""
        required_vars = [
            'GOOGLE_CLOUD_PROJECT', 'GCS_BUCKET', 'GCS_BASE',
            'CHANNEL_ID', 'DATASET_URI', 'RENDER_LOCAL_ROOT'
        ]
        
        missing = [var for var in required_vars if not getattr(self, var.lower().replace('gcs_', ''))]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
    
    def _setup_directories(self):
        """Setup local scratch directories."""
        self.job_scratch = Path(self.render_root) / self.job_id
        self.job_scratch.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.job_scratch / 'clips').mkdir(exist_ok=True)
        (self.job_scratch / 'final').mkdir(exist_ok=True)
        (self.job_scratch / 'temp').mkdir(exist_ok=True)
        
        logger.info(f"Scratch directory: {self.job_scratch}")
    
    def _get_ffmpeg_command(self, input_file: str, output_file: str, text: str, duration: int = 10) -> List[str]:
        """Generate FFmpeg command with consistent encoding profile."""
        
        # Base encoding profile (CPU fallback)
        base_profile = [
            'ffmpeg', '-y',  # Overwrite output
            '-f', 'lavfi',   # Input format
            '-i', f'color=black:size=1280x720:duration={duration}',  # Black background
            '-vf', f"drawtext=text='{text}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            '-c:v', 'h264',
            '-preset', 'veryfast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-r', '24',
            '-s', '1280x720',
            output_file
        ]
        
        # Use NVENC if available and required
        if self.nvenc_required and self._check_nvenc():
            base_profile[8:12] = ['h264_nvenc', '-preset', 'p4', '-rc', 'vbr_hq', '-cq', '28']
            base_profile.extend(['-b:v', '2500k', '-maxrate', '4000k', '-bufsize', '8000k', '-g', '48', '-bf', '2'])
        
        return base_profile
    
    def _check_nvenc(self) -> bool:
        """Check if NVENC is available."""
        try:
            result = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], 
                                  capture_output=True, text=True, timeout=10)
            return 'h264_nvenc' in result.stdout
        except:
            return False
    
    def _run_ffmpeg(self, cmd: List[str]) -> bool:
        """Run FFmpeg command and return success status."""
        try:
            logger.info(f"Running FFmpeg: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("FFmpeg completed successfully")
                return True
            else:
                logger.error(f"FFmpeg failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timed out")
            return False
        except Exception as e:
            logger.error(f"FFmpeg error: {e}")
            return False
    
    def _download_dataset(self) -> List[Dict[str, str]]:
        """Download and parse the dataset from GCS."""
        logger.info(f"Downloading dataset: {self.dataset_uri}")
        
        # Extract dataset path from GCS URI
        dataset_path = self.dataset_uri.replace(f"gs://{self.bucket}/", "")
        local_path = self.job_scratch / 'temp' / 'questions.csv'
        
        # Download using gsutil
        cmd = ['gsutil', 'cp', self.dataset_uri, str(local_path)]
        if subprocess.run(cmd).returncode != 0:
            raise RuntimeError(f"Failed to download dataset: {self.dataset_uri}")
        
        # Parse CSV
        questions = []
        with open(local_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                questions.append(row)
        
        logger.info(f"Loaded {len(questions)} questions from dataset")
        return questions
    
    def _render_question_clip(self, question: Dict[str, str], question_num: int) -> str:
        """Render a single question as a video clip."""
        logger.info(f"Rendering question {question_num}: {question.get('question', 'Unknown')[:50]}...")
        
        # Prepare question text
        question_text = question.get('question', 'Question')
        options = [
            f"A: {question.get('option_a', 'Option A')}",
            f"B: {question.get('option_b', 'Option B')}",
            f"C: {question.get('option_c', 'Option C')}",
            f"D: {question.get('option_d', 'Option D')}"
        ]
        
        # Combine text for display
        display_text = f"{question_text}\n\n" + "\n".join(options)
        
        # Generate output filename
        output_file = self.job_scratch / 'clips' / f'q{question_num:03d}.mp4'
        
        # Get FFmpeg command
        duration = int(question.get('duration_sec', 15))
        cmd = self._get_ffmpeg_command('', str(output_file), display_text, duration)
        
        # Run FFmpeg
        if self._run_ffmpeg(cmd):
            logger.info(f"Question {question_num} rendered successfully")
            return str(output_file)
        else:
            raise RuntimeError(f"Failed to render question {question_num}")
    
    def _upload_clip(self, local_path: str, question_num: int) -> str:
        """Upload a clip to GCS and return the URI."""
        gcs_uri = f"{self.jobs_root}/{self.job_id}/clips/q{question_num:03d}.mp4"
        
        logger.info(f"Uploading clip {question_num} to GCS")
        cmd = ['gsutil', 'cp', local_path, gcs_uri]
        
        if subprocess.run(cmd).returncode == 0:
            logger.info(f"Clip {question_num} uploaded successfully")
            return gcs_uri
        else:
            raise RuntimeError(f"Failed to upload clip {question_num}")
    
    def _create_final_video(self, questions: List[Dict[str, str]]) -> str:
        """Create final concatenated video with intro/outro."""
        logger.info("Creating final concatenated video")
        
        # Create concat file
        concat_file = self.job_scratch / 'temp' / 'concat.txt'
        
        with open(concat_file, 'w') as f:
            # Add intro if available
            intro_path = f"{self.channels_root}/{self.channel_id}/templates/intro.mp4"
            if self._check_gcs_file(intro_path):
                f.write(f"file '{intro_path}'\n")
                logger.info("Added intro to concat")
            
            # Add question clips
            for i in range(len(questions)):
                clip_path = f"{self.jobs_root}/{self.job_id}/clips/q{i+1:03d}.mp4"
                f.write(f"file '{clip_path}'\n")
            
            # Add outro if available
            outro_path = f"{self.channels_root}/{self.channel_id}/templates/outro.mp4"
            if self._check_gcs_file(outro_path):
                f.write(f"file '{outro_path}'\n")
                logger.info("Added outro to concat")
        
        # Download all files to scratch for concatenation
        self._download_files_for_concat(concat_file)
        
        # Create final video
        final_path = self.job_scratch / 'final' / 'final_video.mp4'
        
        # Use FFmpeg concat demuxer
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c', 'copy',  # Copy streams without re-encoding
            str(final_path)
        ]
        
        if self._run_ffmpeg(cmd):
            logger.info("Final video created successfully")
            return str(final_path)
        else:
            raise RuntimeError("Failed to create final video")
    
    def _check_gcs_file(self, gcs_uri: str) -> bool:
        """Check if a GCS file exists."""
        cmd = ['gsutil', 'ls', gcs_uri]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0
    
    def _download_files_for_concat(self, concat_file: Path):
        """Download files needed for concatenation."""
        logger.info("Downloading files for concatenation")
        
        with open(concat_file, 'r') as f:
            for line in f:
                if line.startswith('file '):
                    gcs_uri = line.strip()[6:-1]  # Remove 'file ' and quotes
                    local_path = self.job_scratch / 'temp' / Path(gcs_uri).name
                    
                    cmd = ['gsutil', 'cp', gcs_uri, str(local_path)]
                    if subprocess.run(cmd).returncode == 0:
                        logger.info(f"Downloaded: {Path(gcs_uri).name}")
                    else:
                        logger.warning(f"Failed to download: {gcs_uri}")
    
    def _upload_final_video(self, local_path: str) -> str:
        """Upload final video to GCS."""
        gcs_uri = f"{self.jobs_root}/{self.job_id}/final/final_video.mp4"
        
        logger.info("Uploading final video to GCS")
        cmd = ['gsutil', 'cp', local_path, gcs_uri]
        
        if subprocess.run(cmd).returncode == 0:
            logger.info("Final video uploaded successfully")
            return gcs_uri
        else:
            raise RuntimeError("Failed to upload final video")
    
    def _create_manifest(self, questions: List[Dict[str, str]], clips: List[str], final_video: str) -> str:
        """Create manifest file with job metadata."""
        logger.info("Creating manifest file")
        
        manifest = {
            "job_id": self.job_id,
            "channel_id": self.channel_id,
            "created_at": datetime.now().isoformat(),
            "dataset_uri": self.dataset_uri,
            "questions_count": len(questions),
            "clips": clips,
            "final_video": final_video,
            "encoding_profile": {
                "nvenc_used": self.nvenc_required and self._check_nvenc(),
                "resolution": "1280x720",
                "fps": 24,
                "codec": "h264_nvenc" if (self.nvenc_required and self._check_nvenc()) else "h264"
            },
            "storage": {
                "gcs_bucket": self.bucket,
                "scratch_cleaned": True
            }
        }
        
        # Write manifest locally first
        manifest_path = self.job_scratch / 'final' / '_MANIFEST.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Upload to GCS
        gcs_uri = f"{self.manifests_root}/{self.job_id}/_MANIFEST.json"
        cmd = ['gsutil', 'cp', str(manifest_path), gcs_uri]
        
        if subprocess.run(cmd).returncode == 0:
            logger.info("Manifest uploaded successfully")
            return gcs_uri
        else:
            raise RuntimeError("Failed to upload manifest")
    
    def _cleanup_scratch(self):
        """Clean up local scratch directory."""
        logger.info("Cleaning up scratch directory")
        
        try:
            import shutil
            shutil.rmtree(self.job_scratch)
            logger.info("Scratch directory cleaned successfully")
        except Exception as e:
            logger.warning(f"Failed to cleanup scratch: {e}")
    
    def run(self):
        """Execute the complete video generation pipeline."""
        logger.info(f"🚀 Starting video generation pipeline for job: {self.job_id}")
        
        try:
            # Step 1: Download and parse dataset
            questions = self._download_dataset()
            
            # Step 2: Render individual question clips
            clips = []
            for i, question in enumerate(questions, 1):
                clip_path = self._render_question_clip(question, i)
                gcs_uri = self._upload_clip(clip_path, i)
                clips.append(gcs_uri)
                
                # Clean up local clip
                os.remove(clip_path)
            
            # Step 3: Create final concatenated video
            final_path = self._create_final_video(questions)
            final_video_uri = self._upload_final_video(final_path)
            
            # Step 4: Create and upload manifest
            manifest_uri = self._create_manifest(questions, clips, final_video_uri)
            
            # Step 5: Cleanup
            self._cleanup_scratch()
            
            logger.info(f"🎉 Pipeline completed successfully!")
            logger.info(f"Job ID: {self.job_id}")
            logger.info(f"Questions processed: {len(questions)}")
            logger.info(f"Clips created: {len(clips)}")
            logger.info(f"Final video: {final_video_uri}")
            logger.info(f"Manifest: {manifest_uri}")
            
            return True
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return False

def main():
    """Main entry point."""
    try:
        runner = LeanRunner()
        success = runner.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Runner initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
