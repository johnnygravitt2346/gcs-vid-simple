# 🎬 VM Operator Quick Reference Card

**First Test Topology: API + Worker + UI on Same VM**

---

## 🚀 Quick Start Commands

### **1. Test Environment**
```bash
# Verify everything is ready
python3 test_vm_setup.py

# Check GPU
nvidia-smi

# Check ffmpeg
ffmpeg -version
```

### **2. Start All Services**
```bash
# Automated startup
./start_vm_services.sh

# Or manual (3 terminals):
# Terminal 1: API
cd backend && uvicorn src.main:app --host 0.00.0 --port 8000

# Terminal 2: Worker  
cd backend && python3 worker.py

# Terminal 3: UI
cd backend && streamlit run pipeline_tester_ui.py --server.port 8501 --server.address 0.0.0.0
```

### **3. Stop All Services**
```bash
./stop_vm_services.sh
```

---

## 🌐 Access URLs

**Replace `localhost` with your VM's external IP:**

- **🎬 Streamlit UI**: `http://<VM_EXTERNAL_IP>:8501`
- **🔌 API Docs**: `http://<VM_EXTERNAL_IP>:8000/docs`  
- **🏥 Health Check**: `http://<VM_EXTERNAL_IP>:8000/test/health`

---

## 📝 Logs & Monitoring

### **View Logs**
```bash
# API logs
tail -f logs/api.log

# Worker logs  
tail -f logs/worker.log

# UI logs
tail -f logs/ui.log

# All logs
tail -f logs/*.log
```

### **Check Service Status**
```bash
# Check if ports are in use
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :8501

# Check service PIDs
cat logs/api.pid
cat logs/worker.pid  
cat logs/ui.pid
```

---

## 🔧 Troubleshooting

### **Service Won't Start**
```bash
# Check dependencies
pip3 list | grep -E "(fastapi|uvicorn|streamlit)"

# Check environment
cat backend/.env

# Check permissions
ls -la start_vm_services.sh
```

### **Port Already in Use**
```bash
# Find what's using the port
sudo lsof -i :8000
sudo lsof -i :8501

# Kill process
sudo kill -9 <PID>
```

### **GCS Access Issues**
```bash
# Test GCS access
gsutil ls gs://<your-bucket>

# Check service account
gcloud auth list
gcloud config get-value project
```

---

## 📊 Health Checks

### **API Health**
```bash
curl http://localhost:8000/test/health
```

### **UI Health**
```bash
curl http://localhost:8501
```

### **Worker Status**
```bash
# Check if worker is processing jobs
grep "processing" logs/worker.log | tail -5
```

---

## 🎯 Pipeline Testing

### **1. Create Job**
- Open UI: `http://<VM_IP>:8501`
- Go to "Create Job" tab
- Fill in topic, difficulty, question count
- Click "Create Job"

### **2. Monitor Progress**
- Go to "Job Monitor" tab
- Watch milestones: Health → Questions → Segments → Concat → Finalize
- Chips should turn blue→green per stage

### **3. Check Outputs**
- Go to "Job Outputs" tab
- Verify artifacts in GCS: `gs://<bucket>/jobs/<job_id>/`
- Look for `_MANIFEST.json` in `final/`

---

## 🔒 Security Notes

- **Firewall**: Ensure ports 8000, 8501, 22 are open to your IP
- **Service Account**: VM should have attached service account with `storage.objectAdmin`
- **No Local Credentials**: Service account handles authentication automatically

---

## 📞 Emergency Commands

### **Force Stop Everything**
```bash
# Kill all related processes
pkill -f "uvicorn.*main:app"
pkill -f "python3.*worker.py"  
pkill -f "streamlit.*pipeline_tester_ui.py"

# Remove PID files
rm -f logs/*.pid
```

### **Restart Everything**
```bash
./stop_vm_services.sh
sleep 5
./start_vm_services.sh
```

---

## ✅ Success Criteria

- [ ] API responds to `/test/health` from laptop
- [ ] Streamlit UI loads and shows milestone cards
- [ ] End-to-end job completes: Health → Questions → Segments → Concat → Finalize
- [ ] GCS artifacts created with `_MANIFEST.json`
- [ ] NVENC rendering working on T4 GPU

---

**🎉 When all criteria pass = First test successful!**
