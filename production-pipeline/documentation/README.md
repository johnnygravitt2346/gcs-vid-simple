# 🚀 GPU Video Rendering System

A production-grade, cloud-native system capable of rendering 80,000+ trivia videos per day using a scalable pool of NVIDIA GPUs.

## 🏗️ System Architecture

### Core Components

1. **GPU Worker Pool**: Scalable fleet of NVIDIA T4-powered instances running Docker containers
2. **Job Queue**: GCS-based job management with atomic leasing and checkpointing
3. **Intelligent Autoscaler**: Automatically scales the worker pool based on demand and GPU utilization
4. **Video Rendering Engine**: FFmpeg with NVIDIA hardware acceleration (NVENC)

### Data Flow

```
Job Submission → GCS Job Queue → Worker Claim → Video Rendering → Final Video Storage
     ↓              ↓              ↓            ↓              ↓
  Config File   Status.json   Lease.lock   Checkpoints   Final Videos
```

## 🚀 Quick Start

### Prerequisites

- Google Cloud Project with billing enabled
- `gcloud` CLI configured and authenticated
- Docker installed locally
- NVIDIA GPU drivers (for local testing)

### 1. Deploy Infrastructure

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export ZONE="us-central1-a"

# Make deployment script executable
chmod +x deploy_infrastructure.sh

# Deploy the complete infrastructure
./deploy_infrastructure.sh
```

This will create:
- GCS bucket with proper lifecycle rules
- Instance template with NVIDIA T4 GPU
- Managed Instance Group (1-20 instances)
- Autoscaler configuration
- Health checks and monitoring

### 2. Submit a Test Job

```bash
# Submit a test job
./submit_job.sh channel-test test-001 sample_job_config.json
```

### 3. Monitor Progress

```bash
# Check job status
gsutil cat gs://trivia-automation/jobs/channel-test/test-001/status.json

# Monitor worker instances
gcloud compute instance-groups managed list-instances gpu-video-workers --zone=us-central1-a

# Check autoscaler status
gcloud compute instance-groups managed describe gpu-video-workers --zone=us-central1-a
```

## 📁 Project Structure

```
backend/
├── Dockerfile                    # GPU-enabled container definition
├── requirements.txt              # Python dependencies
├── cloud_worker.py              # Main GPU worker with job leasing
├── final_video_generator.py     # Core video rendering logic
├── autoscaler.py                # Intelligent autoscaler
├── deploy_infrastructure.sh     # Infrastructure deployment script
├── gcs_lifecycle.json           # Data retention policies
└── README.md                    # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GCS_BUCKET` | `trivia-automation` | GCS bucket for jobs and assets |
| `PROJECT_ID` | `your-project-id` | Google Cloud Project ID |
| `REGION` | `us-central1` | GCP region |
| `ZONE` | `us-central1-a` | GCP zone |
| `WORKER_ID` | `worker-{pid}` | Unique worker identifier |

### GPU Configuration

The system uses NVIDIA T4 GPUs with these FFmpeg NVENC settings:

```bash
-c:v h264_nvenc \
-preset p4 \
-profile:v high \
-rc vbr \
-cq 23 \
-b:v 3M \
-maxrate 5M \
-bufsize 6M \
-pix_fmt yuv420p \
-r 30 \
-g 60 \
-movflags +faststart
```

## 📊 Monitoring & Observability

### Health Endpoints

Each worker exposes these endpoints:

- **`/healthz`**: Health check (returns HTTP 200)
- **`/status`**: Current worker status and metrics

### Autoscaler Endpoints

The autoscaler provides:

- **`/status`**: Overall system status and scaling metrics
- **`/metrics`**: Prometheus-style metrics for monitoring

### Key Metrics

- Job queue depth (pending/running/completed/failed)
- GPU utilization across the fleet
- Instance count and scaling history
- Video throughput per GPU
- Processing time per job

## 🔄 Job Lifecycle

### 1. Job Submission

```json
{
  "channel": "channel-test",
  "total_questions": 10,
  "tts_voice": "en-US-Neural2-F",
  "tts_speed": 1.0,
  "questions": [
    {
      "question": "Which sport is known as 'the king of sports'?",
      "answer_a": "Basketball",
      "answer_b": "Baseball",
      "answer_c": "Tennis", 
      "answer_d": "Soccer",
      "correct_answer": "Soccer"
    }
  ]
}
```

### 2. Job Processing

1. **Claim**: Worker claims job using atomic GCS operation
2. **Download**: Job configuration and assets downloaded
3. **Rendering**: Video clips rendered with GPU acceleration
4. **Checkpointing**: Progress saved after each clip
5. **Concatenation**: Final video assembled from clips
6. **Upload**: Final video stored in permanent location

### 3. Job States

- `pending`: Waiting for available worker
- `running`: Currently being processed
- `completed`: Successfully finished
- `failed`: Error occurred during processing

## 🚀 Scaling Behavior

### Scale Up Triggers

- Pending job queue depth > threshold
- GPU utilization > 80%
- Manual scaling commands

### Scale Down Triggers

- Pending jobs < 5
- GPU utilization < 30%
- Idle for > 10 minutes

### Scaling Formula

```
desired_instances = ceil(pending_jobs / (200 * 0.5))
```

Where:
- 200 = jobs per GPU per day
- 0.5 = efficiency factor
- Bounded between 1-20 instances

## 🛡️ Fault Tolerance

### Preemption Handling

- Jobs automatically resume from last checkpoint
- Lease renewal every 60 seconds
- Graceful shutdown on SIGTERM/SIGINT

### Checkpointing

- Individual clips uploaded immediately after rendering
- Progress tracked in GCS
- Failed jobs can resume without losing work

### Health Monitoring

- Instance health checks every 30 seconds
- Automatic instance replacement on failure
- Load balancer integration ready

## 💰 Cost Optimization

### Preemptible Instances

- Use preemptible GPUs for cost savings
- Automatic job recovery on preemption
- Graceful degradation during interruptions

### Resource Management

- GPU utilization monitoring
- Parallel FFmpeg processes (up to 3 per GPU)
- Automatic scaling based on demand

### Data Lifecycle

- Temporary files deleted after 1 day
- Intermediate clips deleted after 7 days
- Job metadata deleted after 30 days
- Final videos never auto-deleted

## 🔍 Troubleshooting

### Common Issues

1. **GPU not available**: Check NVIDIA drivers and CUDA installation
2. **Job stuck in pending**: Verify worker instances are running
3. **Scaling not working**: Check autoscaler logs and permissions
4. **Video quality issues**: Verify NVENC settings and GPU memory

### Debug Commands

```bash
# Check worker logs
gcloud compute instances tail-serial-port-output <instance-name> --zone=<zone>

# SSH to worker instance
gcloud compute ssh <instance-name> --zone=<zone>

# Check GCS job status
gsutil ls gs://trivia-automation/jobs/

# Monitor autoscaler
curl http://<autoscaler-ip>:8080/status
```

### Log Locations

- **Worker logs**: Container stdout/stderr
- **Autoscaler logs**: Application logs
- **Infrastructure logs**: Cloud Logging

## 📈 Performance Tuning

### GPU Optimization

- Monitor GPU utilization with `nvidia-smi`
- Adjust parallel FFmpeg processes based on GPU memory
- Use appropriate NVENC presets for quality/speed balance

### Network Optimization

- Use GCS transfer acceleration for large files
- Implement connection pooling for GCS operations
- Monitor network bandwidth usage

### Memory Management

- Monitor container memory usage
- Implement proper cleanup of temporary files
- Use streaming for large video files

## 🔮 Future Enhancements

### Planned Features

- **Multi-GPU support**: Scale across multiple GPUs per instance
- **Advanced scheduling**: Priority queues and job dependencies
- **Real-time monitoring**: Web dashboard for system status
- **Cost analytics**: Detailed cost tracking and optimization
- **Custom video formats**: Support for additional output formats

### Integration Points

- **Cloud Functions**: Event-driven job submission
- **Pub/Sub**: Real-time job notifications
- **BigQuery**: Analytics and reporting
- **Cloud Monitoring**: Advanced metrics and alerting

## 📚 Additional Resources

- [Google Cloud GPU Documentation](https://cloud.google.com/compute/docs/gpus)
- [FFmpeg NVENC Guide](https://trac.ffmpeg.org/wiki/Encode/H.264)
- [Managed Instance Groups](https://cloud.google.com/compute/docs/instance-groups)
- [GCS Lifecycle Management](https://cloud.google.com/storage/docs/lifecycle)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with ❤️ for high-scale video processing**
