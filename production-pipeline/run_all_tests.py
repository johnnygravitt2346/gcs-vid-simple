#!/usr/bin/env python3
"""
🧪 Master Test Runner for GCS Video Automations
Run individual component tests or full system tests
"""

import os
import sys
import argparse
from pathlib import Path

# Add core modules to path
sys.path.append(str(Path(__file__).parent / "core"))

def run_gemini_tests():
    """Run Gemini feeder tests"""
    print("🧠 Running Gemini Feeder Tests...")
    print("=" * 60)
    
    try:
        from test_gemini_feeder import main as gemini_main
        gemini_main()
        return True
    except Exception as e:
        print(f"❌ Gemini tests failed: {e}")
        return False

def run_tts_tests():
    """Run TTS tests"""
    print("\n🔊 Running TTS Tests...")
    print("=" * 60)
    
    try:
        from test_tts import main as tts_main
        tts_main()
        return True
    except Exception as e:
        print(f"❌ TTS tests failed: {e}")
        return False

def run_video_tests():
    """Run video generation tests"""
    print("\n🎬 Running Video Generation Tests...")
    print("=" * 60)
    
    try:
        from test_video_generation import main as video_main
        video_main()
        return True
    except Exception as e:
        print(f"❌ Video tests failed: {e}")
        return False

def run_full_pipeline_test(question_count: int = 5):
    """Run full pipeline test from Gemini to final video"""
    print(f"\n🚀 Running Full Pipeline Test - {question_count} Questions...")
    print("=" * 60)
    
    try:
        from trivia_generator_cli import main as pipeline_main
        # This will run the full pipeline interactively
        print(f"📝 This will test the complete pipeline with {question_count} questions")
        print("🎯 The pipeline will: Generate questions → Create TTS → Build video → Upload to GCS")
        print("⏱️  Estimated time: 3-8 minutes")
        
        # Run the pipeline
        import asyncio
        asyncio.run(pipeline_main())
        return True
    except Exception as e:
        print(f"❌ Full pipeline test failed: {e}")
        return False

def check_environment():
    """Check if required environment variables are set"""
    print("🔍 Checking Environment Variables...")
    print("=" * 60)
    
    required_vars = {
        "GEMINI_API_KEY": "Gemini AI API key for question generation",
        "GOOGLE_APPLICATION_CREDENTIALS": "Google Cloud credentials for TTS and storage"
    }
    
    missing_vars = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set ({description})")
        else:
            print(f"❌ {var}: Missing ({description})")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Set them before running tests:")
        for var in missing_vars:
            print(f"   export {var}='your-value'")
        return False
    
    print(f"\n✅ All required environment variables are set!")
    return True

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Run GCS Video Automation Tests")
    parser.add_argument("--component", choices=["gemini", "tts", "video", "pipeline"], 
                       help="Test specific component only")
    parser.add_argument("--questions", type=int, default=5,
                       help="Number of questions for pipeline test (default: 5)")
    parser.add_argument("--all", action="store_true",
                       help="Run all component tests")
    parser.add_argument("--env-check", action="store_true",
                       help="Only check environment variables")
    
    args = parser.parse_args()
    
    print("🧪 GCS Video Automation Test Suite")
    print("=" * 60)
    
    # Check environment first
    if not check_environment():
        print("\n❌ Environment check failed. Please set required variables.")
        sys.exit(1)
    
    if args.env_check:
        print("\n✅ Environment check complete.")
        return
    
    # Run specific component test
    if args.component:
        if args.component == "gemini":
            success = run_gemini_tests()
        elif args.component == "tts":
            success = run_tts_tests()
        elif args.component == "video":
            success = run_video_tests()
        elif args.component == "pipeline":
            success = run_full_pipeline_test(args.questions)
        
        if success:
            print(f"\n🎉 {args.component.upper()} tests completed successfully!")
        else:
            print(f"\n❌ {args.component.upper()} tests failed!")
            sys.exit(1)
    
    # Run all component tests
    elif args.all:
        print("\n🧪 Running All Component Tests...")
        print("=" * 60)
        
        results = {}
        
        # Test Gemini
        results["Gemini"] = run_gemini_tests()
        
        # Test TTS
        results["TTS"] = run_tts_tests()
        
        # Test Video Generation
        results["Video Generation"] = run_video_tests()
        
        # Summary
        print(f"\n🎯 Component Test Summary")
        print("=" * 60)
        all_passed = True
        for component, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {component}: {status}")
            if not result:
                all_passed = False
        
        if all_passed:
            print(f"\n🎉 All component tests passed!")
        else:
            print(f"\n⚠️  Some component tests failed!")
            sys.exit(1)
    
    # Default: show help
    else:
        print("\n📋 Available Test Options:")
        print("   --component gemini     Test Gemini question generation")
        print("   --component tts        Test Text-to-Speech functionality")
        print("   --component video      Test video generation")
        print("   --component pipeline   Test full pipeline")
        print("   --all                  Test all components")
        print("   --env-check            Check environment variables only")
        print("   --questions N          Set question count for pipeline test")
        print("\nExample: python run_all_tests.py --component gemini")
        print("Example: python run_all_tests.py --all")
        print("Example: python run_all_tests.py --component pipeline --questions 7")

if __name__ == "__main__":
    main()
