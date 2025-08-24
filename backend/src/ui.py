#!/usr/bin/env python3
"""
Trivia Factory Pipeline Tester UI

FastAPI-based web interface for creating, monitoring, and testing pipeline jobs.
Provides real-time status updates and output previews.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .pipeline import TriviaFactoryPipeline, JobStatus
from .gemini_generator import GeminiQuestionGenerator
from .video_generator import VideoGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="Trivia Factory Pipeline Tester", version="1.0.0")

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipeline
pipeline = TriviaFactoryPipeline()
gemini_generator = None  # Will be initialized when API key is available
video_generator = VideoGenerator({})

# API-only backend - no templates or static files needed
# templates = Jinja2Templates(directory="ui/templates")
# app.mount("/static", StaticFiles(directory="ui/static"), name="static")

# Pydantic models
class JobCreateRequest(BaseModel):
    topic: str
    difficulty: str = "Medium"
    question_count: int = 5
    category: str = "General"
    video_style: str = "modern"
    quality: str = "medium"

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Dict[str, Any]
    created_at: str
    updated_at: str
    error_message: Optional[str] = None



@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/jobs", response_model=List[JobStatusResponse])
async def list_jobs():
    """List all active jobs."""
    jobs = pipeline.list_jobs()
    return [JobStatusResponse(**job.__dict__) for job in jobs]

@app.post("/api/jobs", response_model=Dict[str, str])
async def create_job(request: JobCreateRequest, background_tasks: BackgroundTasks):
    """Create a new pipeline job."""
    try:
        # Create job configuration
        config = {
            "topic": request.topic,
            "difficulty": request.difficulty,
            "question_count": request.question_count,
            "category": request.category,
            "video_style": request.video_style,
            "quality": request.quality
        }
        
        # Create job
        job_id = await pipeline.create_job(config)
        
        # Start job in background
        background_tasks.add_task(pipeline.start_job, job_id)
        
        return {"job_id": job_id, "status": "created"}
        
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get status of a specific job."""
    job = pipeline.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(**job.__dict__)

@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    success = await pipeline.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"status": "cancelled"}

@app.get("/api/jobs/{job_id}/output")
async def get_job_output(job_id: str):
    """Get output files for a completed job."""
    job = pipeline.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    # This would return the actual output files from GCS
    # For now, return placeholder
    return {
        "final_video": f"gs://{pipeline.config['storage']['bucket_name']}/jobs/{job_id}/final_video.mp4",
        "individual_clips": f"gs://{pipeline.config['storage']['bucket_name']}/jobs/{job_id}/clips/",
        "questions": job.questions
    }

@app.post("/api/upload/assets")
async def upload_assets(file: UploadFile = File(...)):
    """Upload asset files (templates, fonts, etc.)."""
    try:
        # Save to assets directory
        assets_dir = Path("assets")
        assets_dir.mkdir(exist_ok=True)
        
        file_path = assets_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return {"filename": file.filename, "status": "uploaded"}
        
    except Exception as e:
        logger.error(f"Failed to upload asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# WebSocket for real-time updates (if needed)
@app.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket, job_id: str):
    """WebSocket endpoint for real-time job updates."""
    try:
        while True:
            # Get current job status
            job = pipeline.get_job_status(job_id)
            if job:
                await websocket.send_text(json.dumps(job.__dict__, default=str))
            
            # Wait before next update
            await asyncio.sleep(5)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

def main():
    """Run the FastAPI server."""
    uvicorn.run(
        "ui:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
