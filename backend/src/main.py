#!/usr/bin/env python3
"""
Trivia Factory FastAPI Backend

Main entry point for the FastAPI backend service.
Configured for CORS to allow Streamlit UI access from the same VM.
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

# Import the UI app which contains all the endpoints
from .ui import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get VM external IP from environment or use localhost for development
VM_EXTERNAL_IP = os.getenv("VM_EXTERNAL_IP", "localhost")
STREAMLIT_PORT = os.getenv("STREAMLIT_PORT", "8501")

# Configure CORS for Streamlit UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://{VM_EXTERNAL_IP}:{STREAMLIT_PORT}",
        f"http://localhost:{STREAMLIT_PORT}",
        "http://localhost:8501",
        "http://127.0.0.1:8501"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add health check endpoint at root level
@app.get("/test/health")
async def health_check():
    """Health check endpoint accessible at /test/health"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "service": "trivia-factory-api",
        "cors_origins": [
            f"http://{VM_EXTERNAL_IP}:{STREAMLIT_PORT}",
            f"http://localhost:{STREAMLIT_PORT}"
        ]
    }

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Trivia Factory API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/test/health",
        "cors_enabled": True,
        "streamlit_ui": f"http://{VM_EXTERNAL_IP}:{STREAMLIT_PORT}"
    }

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    logger.info(f"Starting Trivia Factory API on {host}:{port}")
    logger.info(f"Streamlit UI expected at: http://{VM_EXTERNAL_IP}:{STREAMLIT_PORT}")
    logger.info(f"API docs available at: http://{host}:{port}/docs")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
