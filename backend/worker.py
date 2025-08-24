#!/usr/bin/env python3
"""
Trivia Factory Worker

Background worker process that handles pipeline job execution.
Runs on the same VM as the API and UI for the first test.
"""

import os
import sys
import time
import logging
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from pipeline import TriviaFactoryPipeline, JobStatus
from gemini_generator import GeminiQuestionGenerator
from video_generator import VideoGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TriviaFactoryWorker:
    """Worker class for processing pipeline jobs"""
    
    def __init__(self):
        """Initialize the worker with pipeline components"""
        self.pipeline = TriviaFactoryPipeline()
        self.gemini_generator = None
        self.video_generator = VideoGenerator({})
        self.running = False
        self.poll_interval = 5  # seconds
        
        # Initialize Gemini generator if API key is available
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            try:
                self.gemini_generator = GeminiQuestionGenerator(gemini_api_key)
                logger.info("Gemini generator initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini generator: {e}")
        else:
            logger.warning("GEMINI_API_KEY not set - Gemini generation disabled")
    
    async def start(self):
        """Start the worker loop"""
        self.running = True
        logger.info("Trivia Factory Worker started")
        logger.info(f"Polling for jobs every {self.poll_interval} seconds")
        
        try:
            while self.running:
                await self.process_pending_jobs()
                await asyncio.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Worker shutdown requested")
        except Exception as e:
            logger.error(f"Worker error: {e}")
        finally:
            await self.shutdown()
    
    async def process_pending_jobs(self):
        """Process any pending jobs in the pipeline"""
        try:
            # Get pending jobs
            pending_jobs = self.pipeline.get_pending_jobs()
            
            if pending_jobs:
                logger.info(f"Found {len(pending_jobs)} pending jobs")
                
                for job in pending_jobs:
                    if self.running:
                        await self.process_job(job.job_id)
                    else:
                        break
            else:
                # Log every 10th poll to avoid spam
                if int(time.time()) % 50 == 0:
                    logger.debug("No pending jobs found")
                    
        except Exception as e:
            logger.error(f"Error processing pending jobs: {e}")
    
    async def process_job(self, job_id: str):
        """Process a single job through the pipeline"""
        try:
            logger.info(f"Starting job {job_id}")
            
            # Update job status to RUNNING
            self.pipeline.update_job_status(job_id, JobStatus.RUNNING)
            
            # Execute the pipeline steps
            success = await self.pipeline.execute_job(job_id)
            
            if success:
                logger.info(f"Job {job_id} completed successfully")
                self.pipeline.update_job_status(job_id, JobStatus.COMPLETED)
            else:
                logger.error(f"Job {job_id} failed")
                self.pipeline.update_job_status(job_id, JobStatus.FAILED)
                
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            self.pipeline.update_job_status(job_id, JobStatus.FAILED, str(e))
    
    async def shutdown(self):
        """Gracefully shutdown the worker"""
        logger.info("Shutting down worker...")
        self.running = False
        
        # Cancel any running jobs
        running_jobs = self.pipeline.get_running_jobs()
        for job in running_jobs:
            logger.info(f"Cancelling running job {job.job_id}")
            await self.pipeline.cancel_job(job.job_id)
        
        logger.info("Worker shutdown complete")

def main():
    """Main entry point for the worker"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check required environment variables
    required_vars = ["GOOGLE_CLOUD_PROJECT", "GCS_BUCKET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please set these in your .env file")
        sys.exit(1)
    
    # Log configuration
    logger.info("Trivia Factory Worker Configuration:")
    logger.info(f"Project: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    logger.info(f"Bucket: {os.getenv('GCS_BUCKET')}")
    logger.info(f"API Base URL: {os.getenv('API_BASE_URL', 'http://localhost:8000')}")
    
    # Create and start worker
    worker = TriviaFactoryWorker()
    
    try:
        # Run the worker
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
