#!/usr/bin/env python3
"""
Intelligent Autoscaler for GPU Video Rendering System
Monitors job queue depth and automatically scales the GPU worker pool.
"""

import os
import time
import json
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from google.cloud import storage
from flask import Flask, jsonify

# Configuration
GCS_BUCKET = os.getenv("GCS_BUCKET", "trivia-automation")
JOBS_PREFIX = "jobs"
PROJECT_ID = os.getenv("PROJECT_ID", "your-project-id")
ZONE = os.getenv("ZONE", "us-central1-a")
MIG_NAME = "gpu-video-workers"
SCALING_INTERVAL = 60  # seconds
SCALE_DOWN_DELAY = 600  # 10 minutes
MIN_INSTANCES = 1
MAX_INSTANCES = 20
JOBS_PER_GPU = 200
GPU_EFFICIENCY = 0.5  # 50% efficiency factor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ScalingMetrics:
    """Scaling decision metrics"""
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    current_instances: int
    desired_instances: int
    gpu_utilization: float
    last_scale_up: Optional[datetime] = None
    last_scale_down: Optional[datetime] = None

class JobQueueMonitor:
    """Monitors the GCS-based job queue"""
    
    def __init__(self, bucket_name: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    def get_job_counts(self) -> Dict[str, int]:
        """Count jobs by status"""
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0}
        
        try:
            blobs = self.client.list_blobs(self.bucket, prefix=f"{JOBS_PREFIX}/")
            for blob in blobs:
                if blob.name.endswith("/status.json"):
                    try:
                        content = blob.download_as_text()
                        status_data = json.loads(content)
                        status = status_data.get("status", "unknown")
                        if status in counts:
                            counts[status] += 1
                    except Exception as e:
                        logger.warning(f"Failed to parse status for {blob.name}: {e}")
        except Exception as e:
            logger.error(f"Failed to scan job queue: {e}")
        
        return counts
    
    def get_job_queue_depth(self) -> int:
        """Get total number of pending jobs"""
        counts = self.get_job_counts()
        return counts["pending"]

class MIGController:
    """Controls the Managed Instance Group"""
    
    def __init__(self, project_id: str, zone: str, mig_name: str):
        self.project_id = project_id
        self.zone = zone
        self.mig_name = mig_name
    
    def get_current_size(self) -> int:
        """Get current MIG size"""
        try:
            result = subprocess.run([
                "gcloud", "compute", "instance-groups", "managed", "describe",
                self.mig_name, "--zone", self.zone, "--project", self.project_id,
                "--format", "value(size)"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return int(result.stdout.strip())
        except Exception as e:
            logger.error(f"Failed to get MIG size: {e}")
        
        return 0
    
    def resize_mig(self, new_size: int) -> bool:
        """Resize the MIG to the specified size"""
        try:
            logger.info(f"Resizing MIG {self.mig_name} from {self.get_current_size()} to {new_size}")
            
            result = subprocess.run([
                "gcloud", "compute", "instance-groups", "managed", "resize",
                self.mig_name, "--zone", self.zone, "--project", self.project_id,
                "--size", str(new_size)
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info(f"Successfully resized MIG to {new_size} instances")
                return True
            else:
                logger.error(f"Failed to resize MIG: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to resize MIG: {e}")
            return False
    
    def get_gpu_utilization(self) -> float:
        """Get average GPU utilization across all instances"""
        try:
            # List all instances in the MIG
            result = subprocess.run([
                "gcloud", "compute", "instance-groups", "managed", "list-instances",
                self.mig_name, "--zone", self.zone, "--project", self.project_id,
                "--format", "value(instance)"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return 0.0
            
            instances = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            if not instances:
                return 0.0
            
            # Get GPU utilization from each instance
            total_util = 0.0
            valid_instances = 0
            
            for instance in instances:
                try:
                    # SSH to instance and get GPU utilization
                    gpu_result = subprocess.run([
                        "gcloud", "compute", "ssh", instance, "--zone", self.zone,
                        "--project", self.project_id, "--command",
                        "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits"
                    ], capture_output=True, text=True, timeout=30)
                    
                    if gpu_result.returncode == 0:
                        utilizations = [float(x.strip()) for x in gpu_result.stdout.strip().split('\n') if x.strip()]
                        if utilizations:
                            total_util += sum(utilizations) / len(utilizations)
                            valid_instances += 1
                except Exception as e:
                    logger.warning(f"Failed to get GPU utilization from {instance}: {e}")
            
            return total_util / valid_instances if valid_instances > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Failed to get GPU utilization: {e}")
            return 0.0

class IntelligentAutoscaler:
    """Main autoscaler logic"""
    
    def __init__(self):
        self.job_monitor = JobQueueMonitor(GCS_BUCKET)
        self.mig_controller = MIGController(PROJECT_ID, ZONE, MIG_NAME)
        self.last_scale_up = None
        self.last_scale_down = None
        self.scaling_history: List[Dict] = []
    
    def calculate_desired_instances(self, pending_jobs: int, gpu_util: float) -> int:
        """Calculate desired number of GPU instances"""
        # Base calculation: jobs / (jobs_per_gpu * efficiency)
        base_instances = max(0, int(pending_jobs / (JOBS_PER_GPU * GPU_EFFICIENCY)))
        
        # Apply bounds
        desired = max(MIN_INSTANCES, min(MAX_INSTANCES, base_instances))
        
        # Scale down logic: if queue is nearly empty and GPU utilization is low
        if pending_jobs < 5 and gpu_util < 30.0:
            # Check if we've been idle long enough
            if (self.last_scale_down is None or 
                datetime.utcnow() - self.last_scale_down > timedelta(seconds=SCALE_DOWN_DELAY)):
                desired = min(desired, 1)
        
        return desired
    
    def should_scale(self, current: int, desired: int, gpu_util: float) -> bool:
        """Determine if scaling is needed"""
        # Always scale if there's a significant difference
        if abs(current - desired) >= 2:
            return True
        
        # Scale up if utilization is high and we have pending jobs
        if gpu_util > 80.0 and desired > current:
            return True
        
        # Scale down if utilization is very low
        if gpu_util < 20.0 and desired < current:
            return True
        
        return False
    
    def execute_scaling(self, desired_instances: int) -> bool:
        """Execute the scaling operation"""
        current_size = self.mig_controller.get_current_size()
        
        if current_size == desired_instances:
            return True
        
        if desired_instances > current_size:
            # Scale up
            success = self.mig_controller.resize_mig(desired_instances)
            if success:
                self.last_scale_up = datetime.utcnow()
                logger.info(f"Scaled UP from {current_size} to {desired_instances} instances")
            return success
        else:
            # Scale down
            success = self.mig_controller.resize_mig(desired_instances)
            if success:
                self.last_scale_down = datetime.utcnow()
                logger.info(f"Scaled DOWN from {current_size} to {desired_instances} instances")
            return success
    
    def run_scaling_cycle(self) -> ScalingMetrics:
        """Run one complete scaling cycle"""
        # Get current metrics
        job_counts = self.job_monitor.get_job_counts()
        pending_jobs = job_counts["pending"]
        current_instances = self.mig_controller.get_current_size()
        gpu_utilization = self.mig_controller.get_gpu_utilization()
        
        # Calculate desired instances
        desired_instances = self.calculate_desired_instances(pending_jobs, gpu_utilization)
        
        # Determine if scaling is needed
        should_scale = self.should_scale(current_instances, desired_instances, gpu_utilization)
        
        # Execute scaling if needed
        if should_scale:
            self.execute_scaling(desired_instances)
        
        # Record metrics
        metrics = ScalingMetrics(
            pending_jobs=pending_jobs,
            running_jobs=job_counts["running"],
            completed_jobs=job_counts["completed"],
            failed_jobs=job_counts["failed"],
            current_instances=current_instances,
            desired_instances=desired_instances,
            gpu_utilization=gpu_utilization,
            last_scale_up=self.last_scale_up,
            last_scale_down=self.last_scale_down
        )
        
        # Log metrics
        logger.info(f"Scaling cycle complete: {pending_jobs} pending jobs, "
                   f"{current_instances} instances, {gpu_utilization:.1f}% GPU util")
        
        return metrics
    
    def run_continuous(self):
        """Run the autoscaler continuously"""
        logger.info(f"Starting intelligent autoscaler for MIG {MIG_NAME}")
        logger.info(f"Target: {MIN_INSTANCES}-{MAX_INSTANCES} instances")
        logger.info(f"Scaling interval: {SCALING_INTERVAL} seconds")
        
        while True:
            try:
                metrics = self.run_scaling_cycle()
                
                # Store scaling history
                self.scaling_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "pending_jobs": metrics.pending_jobs,
                    "current_instances": metrics.current_instances,
                    "desired_instances": metrics.desired_instances,
                    "gpu_utilization": metrics.gpu_utilization
                })
                
                # Keep only last 1000 entries
                if len(self.scaling_history) > 1000:
                    self.scaling_history = self.scaling_history[-1000:]
                
                # Wait for next cycle
                time.sleep(SCALING_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Autoscaler interrupted, shutting down")
                break
            except Exception as e:
                logger.error(f"Error in scaling cycle: {e}")
                time.sleep(SCALING_INTERVAL)

# Flask app for monitoring
app = Flask(__name__)
autoscaler = None

@app.route('/healthz')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "intelligent-autoscaler",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/status')
def status():
    """Status endpoint for monitoring"""
    if not autoscaler:
        return jsonify({"error": "Autoscaler not initialized"}), 500
    
    try:
        job_counts = autoscaler.job_monitor.get_job_counts()
        current_instances = autoscaler.mig_controller.get_current_size()
        gpu_utilization = autoscaler.mig_controller.get_gpu_utilization()
        
        # Calculate throughput
        total_jobs = sum(job_counts.values())
        throughput_per_gpu = (total_jobs / max(1, current_instances)) if current_instances > 0 else 0
        
        return jsonify({
            "status": "running",
            "timestamp": datetime.utcnow().isoformat(),
            "job_queue": job_counts,
            "infrastructure": {
                "current_instances": current_instances,
                "min_instances": MIN_INSTANCES,
                "max_instances": MAX_INSTANCES,
                "gpu_utilization": gpu_utilization
            },
            "performance": {
                "throughput_per_gpu": round(throughput_per_gpu, 2),
                "total_jobs": total_jobs
            },
            "scaling": {
                "last_scale_up": autoscaler.last_scale_up.isoformat() if autoscaler.last_scale_up else None,
                "last_scale_down": autoscaler.last_scale_down.isoformat() if autoscaler.last_scale_down else None
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/metrics')
def metrics():
    """Prometheus-style metrics endpoint"""
    if not autoscaler:
        return jsonify({"error": "Autoscaler not initialized"}), 500
    
    try:
        job_counts = autoscaler.job_monitor.get_job_counts()
        current_instances = autoscaler.mig_controller.get_current_size()
        gpu_utilization = autoscaler.mig_controller.get_gpu_utilization()
        
        metrics_data = {
            "gpu_video_autoscaler_pending_jobs": job_counts["pending"],
            "gpu_video_autoscaler_running_jobs": job_counts["running"],
            "gpu_video_autoscaler_completed_jobs": job_counts["completed"],
            "gpu_video_autoscaler_failed_jobs": job_counts["failed"],
            "gpu_video_autoscaler_current_instances": current_instances,
            "gpu_video_autoscaler_gpu_utilization": gpu_utilization,
            "gpu_video_autoscaler_scaling_cycles_total": len(autoscaler.scaling_history)
        }
        
        return jsonify(metrics_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def main():
    """Main entry point"""
    global autoscaler
    
    # Start Flask app in background thread
    def run_flask():
        app.run(host='0.0.0.0', port=8080, debug=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Initialize and run autoscaler
    autoscaler = IntelligentAutoscaler()
    
    try:
        autoscaler.run_continuous()
    except KeyboardInterrupt:
        logger.info("Autoscaler interrupted")
    finally:
        logger.info("Autoscaler shutting down")

if __name__ == "__main__":
    import threading
    main()
