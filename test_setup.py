#!/usr/bin/env python3
"""
Test script to verify Trivia Factory setup
"""

import sys
import os
import importlib

def test_imports():
    """Test if all required modules can be imported."""
    print("🧪 Testing module imports...")
    
    required_modules = [
        'google.cloud.storage',
        'google.cloud.aiplatform', 
        'google.cloud.texttospeech',
        'fastapi',
        'uvicorn',
        'PIL',
        'cv2',
        'numpy'
    ]
    
    failed_imports = []
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        return False
    else:
        print("\n✅ All modules imported successfully!")
        return True

def test_file_structure():
    """Test if all required files and directories exist."""
    print("\n📁 Testing file structure...")
    
    required_files = [
        'requirements.txt',
        'config/config.yaml',
        'src/pipeline.py',
        'src/gemini_generator.py',
        'src/video_generator.py',
        'src/ui.py',
        'ui/templates/index.html',
        'ui/static/css/style.css',
        'ui/static/js/app.js',
        'Dockerfile',
        'deploy.sh',
        'README.md'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ Missing files: {', '.join(missing_files)}")
        return False
    else:
        print("\n✅ All required files present!")
        return True

def test_config():
    """Test if configuration files are valid."""
    print("\n⚙️ Testing configuration...")
    
    try:
        import yaml
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        required_keys = ['gcp', 'storage', 'gemini', 'video', 'pipeline', 'ui']
        missing_keys = []
        
        for key in required_keys:
            if key in config:
                print(f"✅ {key}")
            else:
                print(f"❌ {key}")
                missing_keys.append(key)
        
        if missing_keys:
            print(f"\n❌ Missing config keys: {', '.join(missing_keys)}")
            return False
        else:
            print("\n✅ Configuration valid!")
            return True
            
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_python_files():
    """Test if Python files have valid syntax."""
    print("\n🐍 Testing Python syntax...")
    
    python_files = [
        'src/pipeline.py',
        'src/gemini_generator.py', 
        'src/video_generator.py',
        'src/ui.py'
    ]
    
    syntax_errors = []
    
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                compile(f.read(), file_path, 'exec')
            print(f"✅ {file_path}")
        except SyntaxError as e:
            print(f"❌ {file_path}: {e}")
            syntax_errors.append(file_path)
        except Exception as e:
            print(f"⚠️ {file_path}: {e}")
    
    if syntax_errors:
        print(f"\n❌ Syntax errors in: {', '.join(syntax_errors)}")
        return False
    else:
        print("\n✅ All Python files have valid syntax!")
        return True

def main():
    """Run all tests."""
    print("�� Trivia Factory Setup Test\n")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_file_structure,
        test_config,
        test_python_files
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Trivia Factory is ready to deploy.")
        print("\nNext steps:")
        print("1. Set up Google Cloud credentials")
        print("2. Configure Gemini API key")
        print("3. Run: ./deploy.sh")
    else:
        print(f"\n❌ {total - passed} test(s) failed. Please fix issues before deploying.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
