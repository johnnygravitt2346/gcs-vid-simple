# 🚀 Trivia Factory Cloud-Native Architecture

**Complete cloud-only storage implementation with strict path validation and GCS-first design.**

## 🎯 **Overview**

Trivia Factory now implements a **100% cloud-native architecture** where:
- **All persistent storage** goes to Google Cloud Storage (GCS)
- **Only ephemeral scratch** exists on the VM for encoding
- **Zero hardcoded paths** - everything derives from environment variables
- **Strict validation** prevents any non-compliant writes

## 🏗️ **Architecture Components**

### **1. PathResolver (`src/path_resolver.py`)**
Central path resolution with environment validation.

```python
from src.path_resolver import get_path_resolver

resolver = get_path_resolver()

# GCS paths
templates_uri = resolver.templates_uri()
job_clips_uri = resolver.job_clips_uri(job_id)
job_final_uri = resolver.job_final_uri(job_id)

# Scratch paths
scratch_dir = resolver.scratch_dir(job_id)
working_dir = resolver.scratch_working_dir(job_id)
```

### **2. CloudStorage (`src/cloud_storage.py`)**
Safe storage operations with path validation.

```python
from src.cloud_storage import get_cloud_storage

storage = get_cloud_storage()

# Upload with automatic cleanup
storage.cleanup_scratch_after_upload(
    local_path="/var/trivia/work/job123/clip.mp4",
    gcs_uri="gs://bucket/jobs/job123/clips/clip.mp4",
    context="video_encoding"
)

# Direct GCS operations
storage.write_json_to_gcs(data, gcs_uri, context)
storage.read_json_from_gcs(gcs_uri, context)
```

### **3. Guard Script (`bin/guard_cloud_only.sh`)**
Prevents startup with non-compliant configuration.

```bash
# Run before starting services
backend/bin/guard_cloud_only.sh

# Checks:
# - Required environment variables
# - GCS bucket format
# - Scratch directory permissions
# - No hardcoded paths in code
```

### **4. Linting (`bin/lint_cloud_only.py`)**
Static analysis to prevent regressions.

```bash
# Check for compliance issues
backend/bin/lint_cloud_only.py

# Finds:
# - Hardcoded paths
# - Missing PathResolver usage
# - Non-compliant file operations
```

## 🔧 **Environment Configuration**

### **Required Variables**
```bash
# Cloud Identity (REQUIRED)
GOOGLE_CLOUD_PROJECT=mythic-groove-469801-b7
GCS_BUCKET=trivia-factory-prod
CHANNEL_ID=default

# API Configuration
API_BASE_URL=http://localhost:8000
API_HOST=0.0.0.0
API_PORT=8000

# Streamlit UI
STREAMLIT_PORT=8501

# VM Configuration
VM_EXTERNAL_IP=<YOUR_VM_IP>
```

### **Auto-Generated Paths**
```bash
# GCS Structure
GCS_BASE=gs://${GCS_BUCKET}
GCS_CHANNELS=${GCS_BASE}/channels/${CHANNEL_ID}
GCS_JOBS=${GCS_BASE}/jobs

# Scratch Directory
SCRATCH_ROOT=/var/trivia/work
```

## 📁 **Storage Structure**

### **GCS Organization**
```
gs://trivia-factory-prod/
├── channels/
│   └── default/
│       └── templates/          # Video templates, fonts, assets
└── jobs/
    └── {job_id}/
        ├── working/            # Intermediate files
        ├── clips/              # Individual video clips
        ├── final/              # Final video + manifest
        ├── logs/               # Job logs
        └── status.json         # Job status
```

### **VM Scratch Structure**
```
/var/trivia/work/
└── {job_id}/
    ├── working/                # Temporary working files
    ├── clips/                  # Video clips (deleted after upload)
    └── final/                  # Final video (deleted after upload)
```

## 🚫 **What's NOT Allowed**

### **Forbidden Paths**
- ❌ `/home/username/...`
- ❌ `/Users/username/...`
- ❌ `/tmp/outputs/...`
- ❌ `/var/log/trivia/...`
- ❌ `C:\...` (Windows paths)
- ❌ `~/...` (home directory)

### **Forbidden Operations**
- ❌ Writing outside scratch directory
- ❌ Writing to local paths without upload
- ❌ Hardcoded path strings
- ❌ Relative paths that could escape

## ✅ **What's Required**

### **Path Resolution**
- ✅ Use `PathResolver` for all paths
- ✅ All GCS paths start with `gs://`
- ✅ All scratch paths under `/var/trivia/work`

### **Storage Operations**
- ✅ Upload to GCS immediately after local write
- ✅ Delete local files after successful upload
- ✅ Use cloud storage helper for all operations
- ✅ Validate paths before any write operation

## 🧪 **Testing & Validation**

### **1. Static Linting**
```bash
# Check for compliance issues
backend/bin/lint_cloud_only.py
```

### **2. Environment Validation**
```bash
# Validate configuration
backend/bin/guard_cloud_only.sh
```

### **3. Integration Testing**
```bash
# Test end-to-end compliance
backend/bin/test_cloud_compliance.py
```

### **4. Runtime Validation**
```python
# Validate write paths at runtime
resolver.validate_write_path(path, context)
storage.validate_gcs_uri(uri, context)
storage.validate_scratch_path(path, context)
```

## 🔄 **Migration Guide**

### **From Old Code**
```python
# OLD: Hardcoded paths
output_path = "/home/user/outputs/video.mp4"
status_file = "gs://bucket/jobs/123/status.json"

# NEW: Use PathResolver
output_path = resolver.scratch_final_dir(job_id) + "/video.mp4"
status_file = resolver.job_status_uri(job_id)
```

### **From Old Storage**
```python
# OLD: Direct file operations
with open("/tmp/output.txt", "w") as f:
    f.write(content)

# NEW: Use cloud storage
storage.write_text_to_gcs(content, gcs_uri, context)
```

## 🚀 **Quick Start**

### **1. Setup Environment**
```bash
cp backend/env.example backend/.env
# Edit .env with your project details
```

### **2. Validate Configuration**
```bash
backend/bin/guard_cloud_only.sh
```

### **3. Start Services**
```bash
./start_vm_services.sh
```

### **4. Test Compliance**
```bash
backend/bin/test_cloud_compliance.py
```

## 🎯 **Success Criteria**

- [ ] **No hardcoded paths** in code
- [ ] **All persistent storage** goes to GCS
- [ ] **Only scratch files** on VM (deleted after upload)
- [ ] **PathResolver used** everywhere
- [ ] **Cloud storage helper** for all operations
- [ ] **Guard script passes** validation
- [ ] **Linting shows** no violations
- [ ] **Integration tests** pass

## 🔍 **Troubleshooting**

### **Common Issues**

#### **1. Missing Environment Variables**
```bash
❌ Missing required environment variables: ['GOOGLE_CLOUD_PROJECT']
```
**Solution**: Set all required variables in `.env` file

#### **2. Invalid GCS Bucket**
```bash
❌ Invalid GCS bucket: /tmp/bucket
```
**Solution**: Use valid bucket name (e.g., `trivia-factory-prod`)

#### **3. Scratch Directory Not Writable**
```bash
❌ Scratch directory /var/trivia/work is not writable
```
**Solution**: Run `sudo mkdir -p /var/trivia/work && sudo chmod 755 /var/trivia/work`

#### **4. Hardcoded Path Violations**
```bash
❌ Found hardcoded paths: ['/home/']
```
**Solution**: Replace with `PathResolver` calls

### **Debug Commands**
```bash
# Check environment
env | grep -E "(GOOGLE_CLOUD_PROJECT|GCS_BUCKET|CHANNEL_ID)"

# Test PathResolver
python3 -c "from src.path_resolver import get_path_resolver; print(get_path_resolver().project_id)"

# Test cloud storage
python3 -c "from src.cloud_storage import get_cloud_storage; print('Cloud storage OK')"

# Check scratch directory
ls -la /var/trivia/work/
```

## 📚 **API Reference**

### **PathResolver Methods**
- `templates_uri()` → GCS templates directory
- `job_working_uri(job_id)` → GCS working directory
- `job_clips_uri(job_id)` → GCS clips directory
- `job_final_uri(job_id)` → GCS final directory
- `scratch_dir(job_id)` → Local scratch directory
- `validate_write_path(path, context)` → Validate path compliance

### **CloudStorage Methods**
- `cleanup_scratch_after_upload(local, gcs, context)` → Upload + cleanup
- `write_json_to_gcs(data, uri, context)` → Write JSON to GCS
- `read_json_from_gcs(uri, context)` → Read JSON from GCS
- `list_gcs_objects(prefix, context)` → List GCS objects
- `delete_gcs_object(uri, context)` → Delete GCS object

## 🎉 **Benefits**

1. **🌤️ True Cloud-Native**: No local storage dependencies
2. **🔒 Security**: Strict path validation prevents escapes
3. **📈 Scalability**: GCS handles all storage needs
4. **🔄 Portability**: Works on any GCE VM
5. **🧪 Testability**: Comprehensive validation and testing
6. **🚫 Prevention**: Linting catches regressions early

---

**Trivia Factory is now a truly cloud-native application with zero local path dependencies! 🚀**
