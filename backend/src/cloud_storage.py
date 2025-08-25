#!/usr/bin/env python3
"""
Trivia Factory Cloud Storage Helper

Enforces cloud-only storage policy with safe read/write operations.
All persistent storage goes to GCS, only ephemeral scratch on VM.
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional, BinaryIO, Union
from google.cloud import storage
from .path_resolver import get_path_resolver

logger = logging.getLogger(__name__)

class CloudStorage:
    """Cloud storage operations with strict path validation."""
    
    def __init__(self):
        """Initialize cloud storage with path resolver."""
        self.path_resolver = get_path_resolver()
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.path_resolver.bucket_name)
    
    def validate_gcs_uri(self, uri: str, context: str = "unknown") -> str:
        """Validate and return a GCS URI."""
        if not uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI '{uri}' in {context}. Must start with 'gs://'")
        return uri
    
    def validate_scratch_path(self, path: str, context: str = "unknown") -> str:
        """Validate and return a scratch path."""
        if not path.startswith(self.path_resolver.scratch_root):
            raise ValueError(
                f"Invalid scratch path '{path}' in {context}. "
                f"Must be under {self.path_resolver.scratch_root}"
            )
        return path
    
    def download_to_scratch(self, gcs_uri: str, local_path: str, context: str = "unknown") -> str:
        """Download from GCS to scratch directory."""
        self.validate_gcs_uri(gcs_uri, context)
        self.validate_scratch_path(local_path, context)
        
        # Extract blob name from GCS URI
        blob_name = gcs_uri.replace(f"gs://{self.path_resolver.bucket_name}/", "")
        blob = self.bucket.blob(blob_name)
        
        # Ensure local directory exists
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Download to scratch
        logger.info(f"Downloading {gcs_uri} to {local_path}")
        blob.download_to_filename(local_path)
        
        return local_path
    
    def upload_from_scratch(self, local_path: str, gcs_uri: str, context: str = "unknown") -> str:
        """Upload from scratch directory to GCS."""
        self.validate_scratch_path(local_path, context)
        self.validate_gcs_uri(gcs_uri, context)
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        # Extract blob name from GCS URI
        blob_name = gcs_uri.replace(f"gs://{self.path_resolver.bucket_name}/", "")
        blob = self.bucket.blob(blob_name)
        
        # Upload to GCS
        logger.info(f"Uploading {local_path} to {gcs_uri}")
        blob.upload_from_filename(local_path)
        
        return gcs_uri
    
    def write_text_to_gcs(self, content: str, gcs_uri: str, context: str = "unknown") -> str:
        """Write text content directly to GCS."""
        self.validate_gcs_uri(gcs_uri, context)
        
        # Extract blob name from GCS URI
        blob_name = gcs_uri.replace(f"gs://{self.path_resolver.bucket_name}/", "")
        blob = self.bucket.blob(blob_name)
        
        # Upload text content
        logger.info(f"Writing text to {gcs_uri}")
        blob.upload_from_string(content, content_type="text/plain")
        
        return gcs_uri
    
    def write_json_to_gcs(self, data: dict, gcs_uri: str, context: str = "unknown") -> str:
        """Write JSON data directly to GCS."""
        import json
        content = json.dumps(data, indent=2, default=str)
        return self.write_text_to_gcs(content, gcs_uri, context)
    
    def read_text_from_gcs(self, gcs_uri: str, context: str = "unknown") -> str:
        """Read text content from GCS."""
        self.validate_gcs_uri(gcs_uri, context)
        
        # Extract blob name from GCS URI
        blob_name = gcs_uri.replace(f"gs://{self.path_resolver.bucket_name}/", "")
        blob = self.bucket.blob(blob_name)
        
        # Download text content
        logger.info(f"Reading text from {gcs_uri}")
        return blob.download_as_text()
    
    def read_json_from_gcs(self, gcs_uri: str, context: str = "unknown") -> dict:
        """Read JSON data from GCS."""
        import json
        content = self.read_text_from_gcs(gcs_uri, context)
        return json.loads(content)
    
    def list_gcs_objects(self, gcs_prefix: str, context: str = "unknown") -> list:
        """List objects in GCS with given prefix."""
        if not gcs_prefix.startswith("gs://"):
            gcs_prefix = f"gs://{self.path_resolver.bucket_name}/{gcs_prefix}"
        
        self.validate_gcs_uri(gcs_prefix, context)
        
        # Extract prefix from GCS URI
        prefix = gcs_prefix.replace(f"gs://{self.path_resolver.bucket_name}/", "")
        
        # List objects
        blobs = list(self.bucket.list_blobs(prefix=prefix))
        return [f"gs://{self.path_resolver.bucket_name}/{blob.name}" for blob in blobs]
    
    def delete_gcs_object(self, gcs_uri: str, context: str = "unknown") -> bool:
        """Delete an object from GCS."""
        self.validate_gcs_uri(gcs_uri, context)
        
        # Extract blob name from GCS URI
        blob_name = gcs_uri.replace(f"gs://{self.path_resolver.bucket_name}/", "")
        blob = self.bucket.blob(blob_name)
        
        # Delete object
        logger.info(f"Deleting {gcs_uri}")
        blob.delete()
        
        return True
    
    def cleanup_scratch_after_upload(self, local_path: str, gcs_uri: str, context: str = "unknown") -> bool:
        """Upload file to GCS and then delete local copy."""
        try:
            # Upload to GCS
            self.upload_from_scratch(local_path, gcs_uri, context)
            
            # Delete local file
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.info(f"Cleaned up local file: {local_path}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup scratch after upload: {e}")
            return False
    
    def ensure_gcs_directory(self, gcs_uri: str, context: str = "unknown") -> str:
        """Ensure a GCS directory exists by creating a placeholder file."""
        self.validate_gcs_uri(gcs_uri, context)
        
        # Create a placeholder file to ensure directory exists
        placeholder_uri = f"{gcs_uri}/.placeholder"
        placeholder_content = f"Directory created by Trivia Factory at {context}"
        
        self.write_text_to_gcs(placeholder_content, placeholder_uri, context)
        return gcs_uri
    
    def blob_exists(self, gcs_uri: str) -> bool:
        """Check if a blob exists in GCS."""
        try:
            self.validate_gcs_uri(gcs_uri, "blob_exists")
            
            # Extract blob name from GCS URI
            blob_name = gcs_uri.replace(f"gs://{self.path_resolver.bucket_name}/", "")
            blob = self.bucket.blob(blob_name)
            
            return blob.exists()
        except Exception as e:
            logger.warning(f"Failed to check blob existence for {gcs_uri}: {e}")
            return False
    
    def get_job_storage(self, job_id: str) -> dict:
        """Get storage operations for a specific job."""
        paths = self.path_resolver.get_job_paths(job_id)
        
        return {
            "upload_clip": lambda local_path, clip_name: self.cleanup_scratch_after_upload(
                local_path, 
                f"{paths['gcs']['clips']}/{clip_name}", 
                f"job_{job_id}_clip_upload"
            ),
            "upload_final": lambda local_path: self.cleanup_scratch_after_upload(
                local_path, 
                f"{paths['gcs']['final']}/final_video.mp4", 
                f"job_{job_id}_final_upload"
            ),
            "write_status": lambda status_data: self.write_json_to_gcs(
                status_data, 
                paths['gcs']['status'], 
                f"job_{job_id}_status"
            ),
            "write_manifest": lambda manifest_data: self.write_json_to_gcs(
                manifest_data, 
                paths['gcs']['manifest'], 
                f"job_{job_id}_manifest"
            ),
            "read_status": lambda: self.read_json_from_gcs(
                paths['gcs']['status'], 
                f"job_{job_id}_status"
            ),
            "ensure_directories": lambda: [
                self.ensure_gcs_directory(paths['gcs']['working'], f"job_{job_id}_working"),
                self.ensure_gcs_directory(paths['gcs']['clips'], f"job_{job_id}_clips"),
                self.ensure_gcs_directory(paths['gcs']['final'], f"job_{job_id}_final"),
                self.ensure_gcs_directory(paths['gcs']['logs'], f"job_{job_id}_logs")
            ]
        }

# Global instance
cloud_storage = None

def get_cloud_storage() -> CloudStorage:
    """Get the global cloud storage instance."""
    global cloud_storage
    if cloud_storage is None:
        cloud_storage = CloudStorage()
    return cloud_storage
