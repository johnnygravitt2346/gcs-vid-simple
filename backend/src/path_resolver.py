#!/usr/bin/env python3
"""
Trivia Factory Path Resolver

Cloud-native path resolution with strict validation.
All persistent paths go to GCS, only ephemeral scratch on VM.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class PathResolver:
    """Resolves all paths for the Trivia Factory pipeline."""
    
    def __init__(self):
        """Initialize path resolver with environment validation."""
        self._validate_environment()
        self._setup_paths()
        self._validate_scratch_directory()
    
    def _validate_environment(self):
        """Validate all required environment variables are present."""
        required_vars = [
            "GOOGLE_CLOUD_PROJECT",
            "GCS_BUCKET", 
            "CHANNEL_ID"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
        
        # Validate GCS bucket format
        bucket = os.getenv("GCS_BUCKET")
        if not bucket or bucket.startswith(("file://", "/", "~")):
            raise ValueError(f"Invalid GCS bucket: {bucket}. Must be a valid bucket name.")
    
    def _setup_paths(self):
        """Setup all path configurations from environment."""
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.bucket_name = os.getenv("GCS_BUCKET")
        self.channel_id = os.getenv("CHANNEL_ID")
        
        # GCS base paths
        self.gcs_base = f"gs://{self.bucket_name}"
        self.gcs_channels = f"{self.gcs_base}/channels/{self.channel_id}"
        self.gcs_jobs = f"{self.gcs_base}/jobs"
        
        # VM scratch directory
        self.scratch_root = "/var/trivia/work"
    
    def _validate_scratch_directory(self):
        """Ensure scratch directory exists and is writable."""
        scratch_path = Path(self.scratch_root)
        
        if not scratch_path.exists():
            try:
                scratch_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created scratch directory: {self.scratch_root}")
            except Exception as e:
                raise RuntimeError(f"Failed to create scratch directory {self.scratch_root}: {e}")
        
        if not os.access(self.scratch_root, os.W_OK):
            raise RuntimeError(f"Scratch directory {self.scratch_root} is not writable")
        
        logger.info(f"Scratch directory validated: {self.scratch_root}")
    
    def _validate_gce_environment(self):
        """Ensure we're running on GCE (not laptop)."""
        # Check for GCE metadata
        gce_metadata = "/etc/google_cloud_platform"
        if not os.path.exists(gce_metadata):
            logger.warning("Not running on GCE - this may be a development environment")
    
    def templates_uri(self) -> str:
        """Get GCS URI for channel templates."""
        return f"{self.gcs_channels}/templates"
    
    def job_working_uri(self, job_id: str) -> str:
        """Get GCS URI for job working directory."""
        return f"{self.gcs_jobs}/{job_id}/working"
    
    def job_clips_uri(self, job_id: str) -> str:
        """Get GCS URI for job video clips."""
        return f"{self.gcs_jobs}/{job_id}/clips"
    
    def job_final_uri(self, job_id: str) -> str:
        """Get GCS URI for job final output."""
        return f"{self.gcs_jobs}/{job_id}/final"
    
    def job_logs_uri(self, job_id: str) -> str:
        """Get GCS URI for job logs."""
        return f"{self.gcs_jobs}/{job_id}/logs"
    
    def job_status_uri(self, job_id: str) -> str:
        """Get GCS URI for job status file."""
        return f"{self.gcs_jobs}/{job_id}/status.json"
    
    def job_manifest_uri(self, job_id: str) -> str:
        """Get GCS URI for job manifest file."""
        return f"{self.gcs_jobs}/{job_id}/final/_MANIFEST.json"
    
    def scratch_dir(self, job_id: str) -> str:
        """Get local scratch directory for job (create if missing)."""
        scratch_path = Path(self.scratch_root) / job_id
        scratch_path.mkdir(parents=True, exist_ok=True)
        return str(scratch_path)
    
    def scratch_working_dir(self, job_id: str) -> str:
        """Get local working directory for job."""
        working_path = Path(self.scratch_root) / job_id / "working"
        working_path.mkdir(parents=True, exist_ok=True)
        return str(working_path)
    
    def scratch_clips_dir(self, job_id: str) -> str:
        """Get local clips directory for job."""
        clips_path = Path(self.scratch_root) / job_id / "clips"
        clips_path.mkdir(parents=True, exist_ok=True)
        return str(clips_path)
    
    def scratch_final_dir(self, job_id: str) -> str:
        """Get local final output directory for job."""
        final_path = Path(self.scratch_root) / job_id / "final"
        final_path.mkdir(parents=True, exist_ok=True)
        return str(final_path)
    
    def is_gcs_uri(self, path: str) -> bool:
        """Check if path is a valid GCS URI."""
        return path.startswith("gs://")
    
    def is_scratch_path(self, path: str) -> bool:
        """Check if path is under scratch directory."""
        return path.startswith(self.scratch_root)
    
    def validate_write_path(self, path: str, context: str = "unknown"):
        """Validate that a write path is compliant with cloud-only policy."""
        if not self.is_gcs_uri(path) and not self.is_scratch_path(path):
            raise ValueError(
                f"Invalid write path '{path}' in {context}. "
                f"Must be GCS URI (gs://...) or under scratch directory ({self.scratch_root})"
            )
    
    def cleanup_scratch(self, job_id: str) -> bool:
        """Clean up all scratch files for a job."""
        try:
            scratch_path = Path(self.scratch_root) / job_id
            if scratch_path.exists():
                import shutil
                shutil.rmtree(scratch_path)
                logger.info(f"Cleaned up scratch directory for job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup scratch for job {job_id}: {e}")
            return False
    
    def get_job_paths(self, job_id: str) -> dict:
        """Get all paths for a specific job."""
        return {
            "gcs": {
                "working": self.job_working_uri(job_id),
                "clips": self.job_clips_uri(job_id),
                "final": self.job_final_uri(job_id),
                "logs": self.job_logs_uri(job_id),
                "status": self.job_status_uri(job_id),
                "manifest": self.job_manifest_uri(job_id)
            },
            "scratch": {
                "root": self.scratch_dir(job_id),
                "working": self.scratch_working_dir(job_id),
                "clips": self.scratch_clips_dir(job_id),
                "final": self.scratch_final_dir(job_id)
            }
        }

# Global instance
path_resolver = None

def get_path_resolver() -> PathResolver:
    """Get the global path resolver instance."""
    global path_resolver
    if path_resolver is None:
        path_resolver = PathResolver()
    return path_resolver
