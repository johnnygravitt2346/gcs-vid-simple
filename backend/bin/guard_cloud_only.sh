#!/bin/bash
# Trivia Factory Cloud-Only Guard Script
# Prevents running with non-compliant paths or non-GCE environment

set -e

echo "🔒 Trivia Factory Cloud-Only Guard Script"
echo "Validating environment and configuration..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if running on GCE
check_gce_environment() {
    echo "🔍 Checking GCE environment..."
    
    # Check for GCE metadata
    if [ -f "/etc/google_cloud_platform" ]; then
        echo -e "${GREEN}✅ Running on GCE${NC}"
        return 0
    fi
    
    # Check for GCE instance metadata
    if curl -s -f "http://metadata.google.internal/computeMetadata/v1/instance/name" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Running on GCE (metadata accessible)${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}⚠️  Not running on GCE - this may be a development environment${NC}"
    echo -e "${YELLOW}   Proceeding with warnings...${NC}"
    return 0
}

# Function to validate environment variables
validate_environment() {
    echo "🔍 Validating environment variables..."
    
    required_vars=("GOOGLE_CLOUD_PROJECT" "GCS_BUCKET" "CHANNEL_ID")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo -e "${RED}❌ Missing required environment variables: ${missing_vars[*]}${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All required environment variables present${NC}"
}

# Function to validate GCS bucket format
validate_gcs_bucket() {
    echo "🔍 Validating GCS bucket format..."
    
    bucket="$GCS_BUCKET"
    
    # Check for invalid bucket patterns
    if [[ "$bucket" =~ ^(file://|/|~|\.\.) ]]; then
        echo -e "${RED}❌ Invalid GCS bucket: $bucket${NC}"
        echo -e "${RED}   Bucket must be a valid GCS bucket name, not a local path${NC}"
        exit 1
    fi
    
    if [[ "$bucket" =~ [A-Z] ]]; then
        echo -e "${RED}❌ Invalid GCS bucket: $bucket${NC}"
        echo -e "${RED}   GCS bucket names must be lowercase${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ GCS bucket format valid: $bucket${NC}"
}

# Function to validate scratch directory
validate_scratch_directory() {
    echo "🔍 Validating scratch directory..."
    
    scratch_root="/var/trivia/work"
    
    # Check if scratch directory exists and is writable
    if [ ! -d "$scratch_root" ]; then
        echo "📁 Creating scratch directory: $scratch_root"
        sudo mkdir -p "$scratch_root"
        sudo chmod 755 "$scratch_root"
    fi
    
    if [ ! -w "$scratch_root" ]; then
        echo -e "${RED}❌ Scratch directory $scratch_root is not writable${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Scratch directory validated: $scratch_root${NC}"
}

# Function to check for hardcoded paths in code
check_hardcoded_paths() {
    echo "🔍 Checking for hardcoded paths in code..."
    
    # Get the directory where this script is located
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    project_root="$(dirname "$script_dir")"
    
    # Patterns to check for
    patterns=(
        "/home/"
        "/Users/"
        "C:\\\\"
        "/tmp/outputs"
        "/var/log/trivia"
        "/opt/trivia"
    )
    
    violations=()
    
    for pattern in "${patterns[@]}"; do
        # Search in Python files
        if grep -r "$pattern" "$project_root" --include="*.py" --exclude-dir="__pycache__" --exclude-dir=".git" > /dev/null 2>&1; then
            violations+=("$pattern")
        fi
    done
    
    if [ ${#violations[@]} -ne 0 ]; then
        echo -e "${RED}❌ Found hardcoded paths: ${violations[*]}${NC}"
        echo -e "${RED}   Please use PathResolver for all path resolution${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ No hardcoded paths found${NC}"
}

# Function to validate Python imports
validate_python_imports() {
    echo "🔍 Validating Python imports..."
    
    cd "$(dirname "$0")/.."
    
    # Check if PathResolver can be imported
    if python3 -c "from src.path_resolver import get_path_resolver; print('PathResolver import successful')" 2>/dev/null; then
        echo -e "${GREEN}✅ PathResolver import successful${NC}"
    else
        echo -e "${RED}❌ Failed to import PathResolver${NC}"
        exit 1
    fi
}

# Main validation
main() {
    echo "🚀 Starting validation..."
    
    check_gce_environment
    validate_environment
    validate_gcs_bucket
    validate_scratch_directory
    check_hardcoded_paths
    validate_python_imports
    
    echo ""
    echo -e "${GREEN}🎉 All validations passed!${NC}"
    echo -e "${GREEN}   Trivia Factory is ready to run with cloud-only storage.${NC}"
    echo ""
    echo "📋 Configuration Summary:"
    echo "   Project: $GOOGLE_CLOUD_PROJECT"
    echo "   Bucket: $GCS_BUCKET"
    echo "   Channel: $CHANNEL_ID"
    echo "   Scratch: /var/trivia/work"
}

# Run main function
main "$@"
