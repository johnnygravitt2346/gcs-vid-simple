# 🎬 Trivia Factory First Test Setup Guide

**WORK ORDER — Control Point & First-Test Topology**

## 🎯 Objective
Run the **entire pipeline on one GCP DEV GPU VM (preemptible T4)** so you can test end-to-end with real NVENC performance. Your **laptop (Cursor)** is only for viewing the UI in a browser. No SSH tunnels or local wiring for the first test.

---

## 🏗️ Roles & Topology

### **Operator (your laptop / Cursor)**
- Open browser to the VM's UI
- Click buttons, view status
- Monitor pipeline progress

### **Compute (DEV GPU VM – preemptible T4)**
- Run **FastAPI (backend)** on port 8000
- Run **Worker** process for job processing
- Run **Streamlit UI** on port 8501
- All rendering happens here using NVENC
- All artifacts go to **GCS**

---

## 🚀 Quick Start (3 Steps)

### 1. **Environment Setup** (on the VM)
```bash
# Copy environment template
cp backend/env.example backend/.env

# Edit .env with your values
nano backend/.env
```

**Required .env contents:**
```bash
GOOGLE_CLOUD_PROJECT=<YOUR_PROJECT_ID>
GCS_BUCKET=<YOUR_BUCKET>
API_BASE_URL=http://localhost:8000
CHANNEL_ID=default
VM_EXTERNAL_IP=<YOUR_VM_EXTERNAL_IP>
```

### 2. **Install Dependencies** (on the VM)
```bash
cd backend
pip3 install -r requirements.txt
cd ..
```

### 3. **Start All Services** (on the VM)
```bash
./start_vm_services.sh
```

---

## 🔧 Detailed Setup

### **Prerequisites**
- GCP VM with T4 GPU (preemptible recommended)
- Service account attached with `storage.objectAdmin` on bucket
- Python 3.8+ installed
- Firewall rules for ports 8000, 8501, and 22

### **Firewall Configuration**
```bash
# Allow your IP to access VM ports
gcloud compute firewall-rules create trivia-factory-test \
    --allow tcp:8000,tcp:8501,tcp:22 \
    --source-ranges=<YOUR_IP>/32 \
    --target-tags=trivia-factory-test
```

### **Service Account Setup**
```bash
# Create service account (if not exists)
gcloud iam service-accounts create trivia-factory-worker \
    --display-name="Trivia Factory Worker"

# Grant storage permissions
gcloud projects add-iam-policy-binding <PROJECT_ID> \
    --member="serviceAccount:trivia-factory-worker@<PROJECT_ID>.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Attach to VM
gcloud compute instances set-service-account <VM_NAME> \
    --service-account=trivia-factory-worker@<PROJECT_ID>.iam.gserviceaccount.com
```

---

## 🚀 Starting Services

### **Option A: Automated (Recommended)**
```bash
./start_vm_services.sh
```

### **Option B: Manual (3 Terminal Sessions)**
```bash
# Terminal 1: API
cd backend
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Worker
cd backend
python3 worker.py

# Terminal 3: Streamlit UI
cd backend
streamlit run pipeline_tester_ui.py --server.port 8501 --server.address 0.0.0.0
```

---

## 🌐 Access URLs

**Replace `localhost` with your VM's external IP:**

- **🎬 Streamlit UI**: `http://<VM_EXTERNAL_IP>:8501`
- **🔌 API Docs**: `http://<VM_EXTERNAL_IP>:8000/docs`
- **🏥 Health Check**: `http://<VM_EXTERNAL_IP>:8000/test/health`

---

## ✅ Acceptance Criteria

### **1. API Up**
- `/test/health` returns JSON OK from your laptop
- CORS enabled for Streamlit UI access

### **2. UI Visible**
- Pipeline Tester renders milestone cards (not just a title)
- Health check shows API is accessible

### **3. End-to-End Smoke Run**
From the UI, run: **Health → Questions → Segments → Concat → Finalize**

- ✅ Chips turn blue→green per stage
- ✅ Artifacts appear in `gs://<bucket>/jobs/<job_id>/…`
- ✅ `_MANIFEST.json` present in `final/`

---

## 🔍 Troubleshooting

### **Service Won't Start**
```bash
# Check logs
tail -f logs/api.log
tail -f logs/worker.log
tail -f logs/ui.log

# Check if ports are in use
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :8501
```

### **API Health Check Fails**
```bash
# Check if API is running
curl http://localhost:8000/test/health

# Check CORS configuration
curl -H "Origin: http://localhost:8501" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS http://localhost:8000/api/jobs
```

### **Worker Not Processing Jobs**
```bash
# Check worker logs
tail -f logs/worker.log

# Verify environment variables
cd backend && python3 -c "import os; print('GCS_BUCKET:', os.getenv('GCS_BUCKET'))"
```

### **Streamlit UI Not Loading**
```bash
# Check if Streamlit is running
curl http://localhost:8501

# Check firewall rules
gcloud compute firewall-rules list --filter="name:trivia-factory-test"
```

---

## 🛑 Stopping Services

```bash
# Graceful shutdown
./stop_vm_services.sh

# Or manually stop each service
pkill -f "uvicorn.*main:app"
pkill -f "python3.*worker.py"
pkill -f "streamlit.*pipeline_tester_ui.py"
```

---

## 📁 File Structure

```
gcs-video-automations/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── ui.py                # API endpoints
│   │   ├── pipeline.py          # Pipeline logic
│   │   ├── gemini_generator.py  # AI question generation
│   │   └── video_generator.py   # Video rendering
│   ├── worker.py                # Background job processor
│   ├── pipeline_tester_ui.py    # Streamlit interface
│   ├── requirements.txt         # Python dependencies
│   └── .env                     # Environment variables
├── start_vm_services.sh         # Service startup script
├── stop_vm_services.sh          # Service shutdown script
└── FIRST_TEST_SETUP.md          # This guide
```

---

## 🎯 Next Steps (After First Test)

1. **Verify NVENC Performance**: Check GPU utilization during video generation
2. **GCS Artifact Validation**: Confirm all pipeline outputs are stored correctly
3. **Error Handling**: Test various failure scenarios
4. **Performance Metrics**: Measure end-to-end job completion time
5. **Move UI to Laptop**: After first test passes, consider moving UI to your laptop

---

## 📞 Support

**Common Issues:**
- **Port conflicts**: Check if 8000/8501 are already in use
- **Permission denied**: Ensure service account has proper GCS permissions
- **CORS errors**: Verify VM_EXTERNAL_IP is set correctly in .env
- **Worker not processing**: Check if GCS_BUCKET is set and accessible

**Debug Commands:**
```bash
# Check GPU availability
nvidia-smi

# Verify ffmpeg
ffmpeg -version

# Test GCS access
gsutil ls gs://<your-bucket>

# Check service status
curl http://localhost:8000/test/health
curl http://localhost:8501
```

---

**✅ Done =** One VM runs **API + Worker + UI**; you can drive it from your laptop's browser and complete a smoke test with real NVENC rendering and GCS artifacts.
