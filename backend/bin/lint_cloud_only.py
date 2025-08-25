#!/usr/bin/env python3
"""
Trivia Factory Cloud-Only Linting

Static analysis to prevent hardcoded paths and ensure cloud-only compliance.
"""

import os
import re
import sys
from pathlib import Path

# Patterns that indicate hardcoded paths
HARDCODED_PATTERNS = [
    r"/home/[^/]+",           # /home/username
    r"/Users/[^/]+",          # /Users/username (macOS)
    r"C:\\\\",                # C:\ (Windows)
    r"/tmp/outputs",          # /tmp/outputs
    r"/var/log/trivia",       # /var/log/trivia
    r"/opt/trivia",           # /opt/trivia
    r"~/",                    # ~/ (home directory)
    r"\.\./",                 # ../ (relative paths that might escape)
]

# Allowed patterns (these are OK)
ALLOWED_PATTERNS = [
    r"/var/trivia/work",      # Scratch directory
    r"gs://",                 # GCS URIs
    r"gsutil",                # gsutil commands
    r"gcloud",                # gcloud commands
]

def check_file_for_hardcoded_paths(file_path: Path) -> list:
    """Check a single file for hardcoded paths."""
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                for pattern in HARDCODED_PATTERNS:
                    if re.search(pattern, line):
                        # Check if this line contains an allowed pattern
                        is_allowed = False
                        for allowed in ALLOWED_PATTERNS:
                            if re.search(allowed, line):
                                is_allowed = True
                                break
                        
                        if not is_allowed:
                            violations.append({
                                'file': str(file_path),
                                'line': line_num,
                                'pattern': pattern,
                                'content': line.strip()
                            })
    
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
    
    return violations

def check_directory_for_hardcoded_paths(directory: Path) -> list:
    """Check a directory recursively for hardcoded paths."""
    all_violations = []
    
    # File extensions to check
    extensions = {'.py', '.sh', '.yaml', '.yml', '.json', '.md', '.txt'}
    
    # Directories to skip
    skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env'}
    
    # Files to skip (these contain the patterns we're checking for)
    skip_files = {'guard_cloud_only.sh', 'lint_cloud_only.py'}
    
    for root, dirs, files in os.walk(directory):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            file_path = Path(root) / file
            
            # Skip files that contain the patterns we're checking for
            if file in skip_files:
                continue
                
            # Only check files with relevant extensions
            if file_path.suffix in extensions:
                violations = check_file_for_hardcoded_paths(file_path)
                all_violations.extend(violations)
    
    return all_violations

def check_path_resolver_usage(directory: Path) -> list:
    """Check if PathResolver is being used instead of hardcoded paths."""
    missing_usage = []
    
    # Files that should use PathResolver
    python_files = list(directory.rglob("*.py"))
    
    for file_path in python_files:
        if file_path.name == "path_resolver.py":
            continue  # Skip the resolver itself
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check if file contains path operations
                if any(op in content for op in ['open(', 'Path(', 'os.path', 'pathlib']):
                    # Check if it imports or uses PathResolver
                    if 'path_resolver' not in content and 'PathResolver' not in content:
                        missing_usage.append({
                            'file': str(file_path),
                            'issue': 'File contains path operations but does not use PathResolver'
                        })
        
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
    
    return missing_usage

def main():
    """Main linting function."""
    print("🔒 Trivia Factory Cloud-Only Linting")
    print("=" * 50)
    
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print(f"Checking directory: {project_root}")
    print()
    
    # Check for hardcoded paths
    print("🔍 Checking for hardcoded paths...")
    hardcoded_violations = check_directory_for_hardcoded_paths(project_root)
    
    if hardcoded_violations:
        print(f"❌ Found {len(hardcoded_violations)} hardcoded path violations:")
        for violation in hardcoded_violations:
            print(f"   {violation['file']}:{violation['line']} - {violation['pattern']}")
            print(f"      {violation['content']}")
            print()
    else:
        print("✅ No hardcoded paths found")
    
    # Check PathResolver usage
    print("🔍 Checking PathResolver usage...")
    missing_usage = check_path_resolver_usage(project_root)
    
    if missing_usage:
        print(f"⚠️  Found {len(missing_usage)} files that should use PathResolver:")
        for issue in missing_usage:
            print(f"   {issue['file']} - {issue['issue']}")
        print()
    else:
        print("✅ All files properly use PathResolver")
    
    # Summary
    print("=" * 50)
    total_issues = len(hardcoded_violations) + len(missing_usage)
    
    if total_issues == 0:
        print("🎉 All checks passed! Trivia Factory is cloud-only compliant.")
        return 0
    else:
        print(f"⚠️  Found {total_issues} issues to address:")
        print(f"   - {len(hardcoded_violations)} hardcoded path violations")
        print(f"   - {len(missing_usage)} missing PathResolver usage")
        print()
        print("💡 Recommendations:")
        print("   1. Replace hardcoded paths with PathResolver calls")
        print("   2. Import and use PathResolver in files with path operations")
        print("   3. Use cloud storage helper for all file operations")
        return 1

if __name__ == "__main__":
    sys.exit(main())
