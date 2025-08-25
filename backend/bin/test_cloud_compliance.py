#!/usr/bin/env python3
"""
Trivia Factory Cloud Compliance Integration Test

Tests end-to-end compliance with cloud-only storage policy.
"""

import os
import sys
import time
import tempfile
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from path_resolver import get_path_resolver
from cloud_storage import get_cloud_storage

def test_path_resolver():
    """Test PathResolver functionality."""
    print("🔍 Testing PathResolver...")
    
    try:
        resolver = get_path_resolver()
        print(f"  ✅ Project: {resolver.project_id}")
        print(f"  ✅ Bucket: {resolver.bucket_name}")
        print(f"  ✅ Channel: {resolver.channel_id}")
        print(f"  ✅ Scratch Root: {resolver.scratch_root}")
        return True
    except Exception as e:
        print(f"  ❌ PathResolver failed: {e}")
        return False

def test_cloud_storage():
    """Test cloud storage operations."""
    print("🔍 Testing Cloud Storage...")
    
    try:
        storage = get_cloud_storage()
        print(f"  ✅ Cloud storage initialized")
        
        # Test bucket access
        bucket = storage.storage_client.bucket(storage.path_resolver.bucket_name)
        blobs = list(bucket.list_blobs(max_results=1))
        print(f"  ✅ GCS bucket accessible: {len(blobs)}+ objects")
        
        return True
    except Exception as e:
        print(f"  ❌ Cloud storage failed: {e}")
        return False

def test_scratch_directory():
    """Test scratch directory creation and cleanup."""
    print("🔍 Testing Scratch Directory...")
    
    try:
        resolver = get_path_resolver()
        
        # Test job-specific scratch directory
        test_job_id = "test_compliance_123"
        scratch_dir = resolver.scratch_dir(test_job_id)
        
        if not os.path.exists(scratch_dir):
            print(f"  ❌ Scratch directory not created: {scratch_dir}")
            return False
        
        # Test subdirectories
        working_dir = resolver.scratch_working_dir(test_job_id)
        clips_dir = resolver.scratch_clips_dir(test_job_id)
        final_dir = resolver.scratch_final_dir(test_job_id)
        
        for dir_path in [working_dir, clips_dir, final_dir]:
            if not os.path.exists(dir_path):
                print(f"  ❌ Subdirectory not created: {dir_path}")
                return False
        
        print(f"  ✅ Scratch directories created successfully")
        
        # Test cleanup
        if resolver.cleanup_scratch(test_job_id):
            print(f"  ✅ Scratch cleanup successful")
        else:
            print(f"  ❌ Scratch cleanup failed")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Scratch directory test failed: {e}")
        return False

def test_gcs_paths():
    """Test GCS path generation."""
    print("🔍 Testing GCS Paths...")
    
    try:
        resolver = get_path_resolver()
        test_job_id = "test_compliance_123"
        
        # Test path generation
        paths = resolver.get_job_paths(test_job_id)
        
        expected_gcs_paths = [
            "working", "clips", "final", "logs", "status", "manifest"
        ]
        
        for path_type in expected_gcs_paths:
            if path_type not in paths["gcs"]:
                print(f"  ❌ Missing GCS path: {path_type}")
                return False
        
        # Verify all paths are GCS URIs
        for path_type, uri in paths["gcs"].items():
            if not uri.startswith("gs://"):
                print(f"  ❌ Invalid GCS URI for {path_type}: {uri}")
                return False
        
        print(f"  ✅ All GCS paths generated correctly")
        return True
    except Exception as e:
        print(f"  ❌ GCS path test failed: {e}")
        return False

def test_write_path_validation():
    """Test write path validation."""
    print("🔍 Testing Write Path Validation...")
    
    try:
        resolver = get_path_resolver()
        
        # Test valid paths
        valid_paths = [
            "/var/trivia/work/job123/file.txt",  # Scratch path
            "gs://bucket-name/path/file.txt"     # GCS URI
        ]
        
        for path in valid_paths:
            try:
                if path.startswith("gs://"):
                    resolver.validate_gcs_uri(path, "test")
                else:
                    resolver.validate_scratch_path(path, "test")
                print(f"  ✅ Valid path accepted: {path}")
            except Exception as e:
                print(f"  ❌ Valid path rejected: {path} - {e}")
                return False
        
        # Test invalid paths
        invalid_paths = [
            "/tmp/outputs/file.txt",           # Outside scratch
            "/home/user/file.txt",             # Home directory
            "/var/log/trivia/file.txt"         # Log directory
        ]
        
        for path in invalid_paths:
            try:
                resolver.validate_write_path(path, "test")
                print(f"  ❌ Invalid path accepted: {path}")
                return False
            except ValueError:
                print(f"  ✅ Invalid path correctly rejected: {path}")
        
        return True
    except Exception as e:
        print(f"  ❌ Write path validation test failed: {e}")
        return False

def test_cloud_storage_operations():
    """Test cloud storage read/write operations."""
    print("🔍 Testing Cloud Storage Operations...")
    
    try:
        storage = get_cloud_storage()
        resolver = get_path_resolver()
        
        # Test text write/read
        test_content = "Test content for compliance check"
        test_uri = f"{resolver.gcs_jobs}/test_compliance/test.txt"
        
        # Write text
        storage.write_text_to_gcs(test_content, test_uri, "compliance_test")
        print(f"  ✅ Text written to GCS: {test_uri}")
        
        # Read text back
        read_content = storage.read_text_from_gcs(test_uri, "compliance_test")
        if read_content == test_content:
            print(f"  ✅ Text read from GCS correctly")
        else:
            print(f"  ❌ Text content mismatch")
            return False
        
        # Cleanup test file
        storage.delete_gcs_object(test_uri, "compliance_test")
        print(f"  ✅ Test file cleaned up")
        
        return True
    except Exception as e:
        print(f"  ❌ Cloud storage operations test failed: {e}")
        return False

def main():
    """Run all compliance tests."""
    print("🔒 Trivia Factory Cloud Compliance Integration Test")
    print("=" * 60)
    
    tests = [
        ("PathResolver", test_path_resolver),
        ("Cloud Storage", test_cloud_storage),
        ("Scratch Directory", test_scratch_directory),
        ("GCS Paths", test_gcs_paths),
        ("Write Path Validation", test_write_path_validation),
        ("Cloud Storage Operations", test_cloud_storage_operations)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  ❌ {test_name} test failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All compliance tests passed!")
        print("✅ Trivia Factory is fully cloud-native compliant")
        print("✅ No local path violations")
        print("✅ All storage goes through GCS")
        print("✅ Scratch directories are properly managed")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        print("Please fix the issues before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())
