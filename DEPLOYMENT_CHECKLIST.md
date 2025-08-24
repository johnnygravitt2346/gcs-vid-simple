# 🚀 Trivia Factory Deployment Checklist

## ✅ Pre-Deployment Setup

### 1. Google Cloud Project Configuration
- [ ] Project ID: `mythic-groove-469801-b7` ✅
- [ ] Billing enabled ✅
- [ ] Required APIs enabled:
  - [ ] Compute Engine API
  - [ ] Cloud Storage API
  - [ ] AI Platform API
  - [ ] Text-to-Speech API
  - [ ] Cloud Build API

### 2. Service Account Setup
- [ ] Create service account with roles:
  - [ ] Storage Admin
  - [ ] AI Platform Developer
  - [ ] Compute Instance Admin
  - [ ] Cloud Build Service Account
- [ ] Download service account JSON key
- [ ] Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

### 3. Gemini AI Configuration
- [ ] Get Gemini API key from Google AI Studio
- [ ] Set `GEMINI_API_KEY` environment variable
- [ ] Test API access

### 4. Asset Preparation
- [ ] Video templates (1.mp4, 2.mp4, 3.mp4)
- [ ] Font files (.ttf format)
- [ ] Audio assets (timer, ticking, ding sounds)
- [ ] Upload to GCS bucket

## 🚀 Deployment Steps

### 1. Local Testing
```bash
# Test the setup
python3 test_setup.py

# Start local development server
./start_local.sh
```

### 2. Cloud Deployment
```bash
# Deploy to Google Cloud
./deploy.sh
```

### 3. Post-Deployment Verification
- [ ] Check Cloud Run service is running
- [ ] Verify GCS bucket structure
- [ ] Test worker instance template
- [ ] Validate auto-scaling group

## 🔧 Configuration Files

### Environment Variables (.env)
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=mythic-groove-469801-b7
GOOGLE_CLOUD_REGION=us-central1
GEMINI_API_KEY=your_gemini_api_key_here
GCS_BUCKET_NAME=trivia-factory-prod
```

### Configuration (config/config.yaml)
- GCP project settings
- Storage bucket configuration
- Gemini AI parameters
- Video generation settings
- Pipeline configuration
- UI settings

## 📊 Expected Costs

### Monthly Budget: $12-25k
- **Preemptible T4 Workers**: $0.11-0.15/hour (60-80% savings)
- **Storage**: $0.02/GB/month + lifecycle cleanup
- **Network**: $0.12/GB egress
- **Compute**: Cloud Run + auto-scaling

### Cost Optimization
- Use preemptible instances for video processing
- Implement GCS lifecycle policies
- Auto-scale to zero when not in use
- NVENC hardware acceleration

## 🧪 Testing Pipeline

### 1. Create Test Job
- Topic: "Space Exploration"
- Difficulty: "Medium"
- Question Count: 5
- Category: "Science"

### 2. Monitor Progress
- Question generation via Gemini
- TTS audio generation
- Video clip creation
- Final video concatenation

### 3. Verify Outputs
- Check GCS bucket for artifacts
- Download and play final video
- Validate individual clips
- Review job logs

## 🚨 Troubleshooting

### Common Issues
1. **NVENC not available**: Falls back to CPU encoding
2. **GCS permissions**: Check service account roles
3. **Gemini API limits**: Implement rate limiting
4. **Video generation failures**: Check ffmpeg installation

### Debug Commands
```bash
# Check GPU availability
nvidia-smi

# Verify ffmpeg
ffmpeg -version

# Test GCS access
gsutil ls gs://trivia-factory-prod

# Check service logs
gcloud logging read "resource.type=cloud_run_revision"
```

## 📈 Scaling Considerations

### Horizontal Scaling
- Auto-scaling worker pools (0-10 instances)
- Load balancing across regions
- Queue-based job distribution

### Vertical Scaling
- Configurable instance sizes
- GPU memory optimization
- Storage performance tuning

## 🔒 Security Checklist

- [ ] Service account with minimal permissions
- [ ] GCS bucket policies configured
- [ ] No hardcoded credentials
- [ ] Secure asset uploads
- [ ] API key rotation plan

## 📞 Support & Monitoring

### Health Checks
- Cloud Run health endpoints
- Worker instance monitoring
- GCS bucket accessibility
- API service status

### Alerting
- Job failure notifications
- Cost threshold alerts
- Performance degradation warnings
- Security incident alerts

---

**Ready for deployment! 🎯**
