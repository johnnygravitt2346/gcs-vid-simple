#!/usr/bin/env python3
"""
Trivia Factory Pipeline Orchestrator

Manages the complete pipeline from question generation to final video output.
Uses GCS as the single source of truth for all artifacts.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

import yaml
from google.cloud import storage
from google.cloud import aiplatform
from google.cloud import texttospeech

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobStatus(Enum):
    PENDING = "pending"
    GENERATING_QUESTIONS = "generating_questions"
    GENERATING_TTS = "generating_tts"
    GENERATING_VIDEOS = "generating_videos"
    CONCATENATING = "concatenating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TriviaQuestion:
    id: str
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    explanation: str
    category: str
    difficulty: str
    created_at: str

@dataclass
class PipelineJob:
    job_id: str
    status: JobStatus
    config: Dict[str, Any]
    questions: List[TriviaQuestion]
    progress: Dict[str, Any]
    created_at: str
    updated_at: str
    error_message: Optional[str] = None

class TriviaFactoryPipeline:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.config["storage"]["bucket_name"])
        
        # Initialize Gemini AI
        aiplatform.init(
            project=self.config["gcp"]["project_id"],
            location=self.config["gcp"]["region"]
        )
        
        self.active_jobs: Dict[str, PipelineJob] = {}
        self.job_history: List[PipelineJob] = []
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    async def create_job(self, config: Dict[str, Any]) -> str:
        """Create a new pipeline job."""
        job_id = f"job_{int(time.time())}_{len(self.active_jobs)}"
        
        job = PipelineJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            config=config,
            questions=[],
            progress={},
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        
        self.active_jobs[job_id] = job
        await self._save_job_status(job)
        
        logger.info(f"Created job {job_id}")
        return job_id
    
    async def start_job(self, job_id: str) -> bool:
        """Start processing a pipeline job."""
        if job_id not in self.active_jobs:
            logger.error(f"Job {job_id} not found")
            return False
        
        job = self.active_jobs[job_id]
        job.status = JobStatus.GENERATING_QUESTIONS
        job.updated_at = datetime.utcnow().isoformat()
        
        try:
            # Step 1: Generate questions using Gemini
            await self._generate_questions(job)
            
            # Step 2: Generate TTS for all questions
            await self._generate_tts(job)
            
            # Step 3: Generate individual video clips
            await self._generate_videos(job)
            
            # Step 4: Concatenate final video
            await self._concatenate_final_video(job)
            
            job.status = JobStatus.COMPLETED
            job.updated_at = datetime.utcnow().isoformat()
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.updated_at = datetime.utcnow().isoformat()
            logger.error(f"Job {job_id} failed: {e}")
        
        await self._save_job_status(job)
        return job.status == JobStatus.COMPLETED
    
    async def _generate_questions(self, job: PipelineJob) -> None:
        """Generate trivia questions using Gemini AI."""
        logger.info(f"Generating questions for job {job.job_id}")
        
        # This would integrate with Gemini API
        # For now, create sample questions
        sample_questions = [
            TriviaQuestion(
                id=f"q_{i}",
                question=f"Sample question {i}?",
                option_a=f"Option A {i}",
                option_b=f"Option B {i}",
                option_c=f"Option C {i}",
                option_d=f"Option D {i}",
                correct_answer=f"Option A {i}",
                explanation=f"Explanation for question {i}",
                category="General",
                difficulty="Medium",
                created_at=datetime.utcnow().isoformat()
            )
            for i in range(1, 6)
        ]
        
        job.questions = sample_questions
        job.progress["questions_generated"] = len(sample_questions)
        await self._save_job_status(job)
    
    async def _generate_tts(self, job: PipelineJob) -> None:
        """Generate TTS audio for all questions."""
        logger.info(f"Generating TTS for job {job.job_id}")
        
        # This would integrate with Google Cloud TTS
        job.progress["tts_generated"] = len(job.questions)
        await self._save_job_status(job)
    
    async def _generate_videos(self, job: PipelineJob) -> None:
        """Generate individual video clips for each question."""
        logger.info(f"Generating videos for job {job.job_id}")
        
        # This would use the video generation script
        job.progress["videos_generated"] = len(job.questions)
        await self._save_job_status(job)
    
    async def _concatenate_final_video(self, job: PipelineJob) -> None:
        """Concatenate all clips into final video."""
        logger.info(f"Concatenating final video for job {job.job_id}")
        
        # This would use ffmpeg to concatenate
        job.progress["final_video_created"] = True
        await self._save_job_status(job)
    
    async def _save_job_status(self, job: PipelineJob) -> None:
        """Save job status to GCS."""
        try:
            status_blob = self.bucket.blob(f"jobs/{job.job_id}/status.json")
            status_blob.upload_from_string(
                json.dumps(asdict(job), default=str),
                content_type="application/json"
            )
        except Exception as e:
            logger.error(f"Failed to save job status: {e}")
    
    def get_job_status(self, job_id: str) -> Optional[PipelineJob]:
        """Get current job status."""
        return self.active_jobs.get(job_id)
    
    def list_jobs(self) -> List[PipelineJob]:
        """List all active jobs."""
        return list(self.active_jobs.values())
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        if job_id not in self.active_jobs:
            return False
        
        job = self.active_jobs[job_id]
        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.utcnow().isoformat()
        
        await self._save_job_status(job)
        return True

# Example usage
async def main():
    pipeline = TriviaFactoryPipeline()
    
    # Create a sample job
    config = {
        "topic": "Science",
        "difficulty": "Medium",
        "question_count": 5,
        "video_style": "modern"
    }
    
    job_id = await pipeline.create_job(config)
    success = await pipeline.start_job(job_id)
    
    if success:
        print(f"Job {job_id} completed successfully")
    else:
        print(f"Job {job_id} failed")

if __name__ == "__main__":
    asyncio.run(main())
