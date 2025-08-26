#!/usr/bin/env python3
"""Backup verification script for gcs-video-automations-v1"""

import os

def verify_backup():
    """Verify that all critical files are present in the backup"""
    
    print("🔍 Verifying GCS Video Automations v1.0 Backup...")
    print("=" * 60)
    
    # Critical files that must be present
    critical_files = [
        "core/cloud_video_generator_fixed.py",
        "core/gemini_feeder.py", 
        "core/cloud_storage.py",
        "core/path_resolver.py",
        "core/requirements.txt",
        "examples/complete_cloud_pipeline.py",
        "examples/test_video_visuals.py",
        "examples/test_gemini_feeder.py",
        "cloud-infrastructure/cloud_worker.py",
        "cloud-infrastructure/Dockerfile",
        "Dockerfile.fonts",
        "cloudbuild-worker.yaml",
        "README.md"
    ]
    
    missing_files = []
    present_files = []
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            present_files.append(file_path)
            print(f"✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path}")
    
    print(f"\n📊 Backup Verification Results:")
    print(f"   ✅ Present: {len(present_files)} files")
    print(f"   ❌ Missing: {len(missing_files)} files")
    
    if missing_files:
        print(f"\n⚠️  Missing critical files:")
        for file_path in missing_files:
            print(f"   • {file_path}")
        return False
    else:
        print(f"\n🎉 Backup is COMPLETE - all critical files present!")
        return True

if __name__ == "__main__":
    success = verify_backup()
    if success:
        print("\n🚀 This backup can reproduce the working pipeline!")
        print("   Next steps:")
        print("   1. Set up environment variables")
        print("   2. Install dependencies: pip install -r core/requirements.txt")
        print("   3. Test with: python examples/test_video_visuals.py")
    else:
        print("\n❌ Backup is INCOMPLETE!")
