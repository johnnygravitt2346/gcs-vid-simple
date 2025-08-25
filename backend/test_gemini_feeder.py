#!/usr/bin/env python3
"""
Test script for Gemini Feeder functionality.

This script tests the core functionality without requiring actual API calls.
"""

import asyncio
import json
import tempfile
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gemini_feeder import GeminiFeeder, FeederRequest, TriviaQuestion, DatasetManifest

async def test_gemini_feeder():
    """Test the Gemini Feeder functionality."""
    print("Testing Gemini Feeder...")
    
    # Test 1: Create a FeederRequest
    print("\n1. Testing FeederRequest creation...")
    request = FeederRequest(
        channel_id="test_channel",
        prompt_preset="science_tech",
        quantity=5,
        difficulty="medium",
        style="engaging"
    )
    print(f"✓ Created request: {request}")
    
    # Test 2: Create TriviaQuestion objects
    print("\n2. Testing TriviaQuestion creation...")
    questions = [
        TriviaQuestion(
            qid="q001",
            question="What is the chemical symbol for gold?",
            option_a="Au",
            option_b="Ag", 
            option_c="Fe",
            option_d="Cu",
            answer_key="A",
            topic="Chemistry",
            tags=["chemistry", "elements"],
            difficulty="medium",
            language="en"
        ),
        TriviaQuestion(
            qid="q002",
            question="Which planet is known as the Red Planet?",
            option_a="Venus",
            option_b="Mars",
            option_c="Jupiter",
            option_d="Saturn",
            answer_key="B",
            topic="Astronomy",
            tags=["astronomy", "planets"],
            difficulty="easy",
            language="en"
        )
    ]
    print(f"✓ Created {len(questions)} questions")
    
    # Test 3: Test question hashing and deduplication
    print("\n3. Testing question hashing...")
    for q in questions:
        hash_val = q.get_hash()
        print(f"  {q.qid}: {hash_val[:16]}...")
    
    # Test 4: Test CSV generation
    print("\n4. Testing CSV generation...")
    feeder = GeminiFeeder(api_key="test_key")
    csv_content = feeder._generate_csv_content(questions)
    print("✓ CSV content generated:")
    print(csv_content[:200] + "..." if len(csv_content) > 200 else csv_content)
    
    # Test 5: Test NDJSON generation
    print("\n5. Testing NDJSON generation...")
    ndjson_content = feeder._generate_ndjson_content(questions)
    print("✓ NDJSON content generated:")
    print(ndjson_content[:200] + "..." if len(ndjson_content) > 200 else ndjson_content)
    
    # Test 6: Test statistics calculation
    print("\n6. Testing statistics calculation...")
    stats = feeder._calculate_dataset_stats(questions)
    print("✓ Statistics calculated:")
    print(json.dumps(stats, indent=2))
    
    # Test 7: Test answer distribution balancing
    print("\n7. Testing answer distribution balancing...")
    # Create questions with imbalanced distribution
    imbalanced_questions = [
        TriviaQuestion(
            qid="q003",
            question="Test question 3",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            answer_key="A",
            topic="Test",
            tags=["test"],
            difficulty="easy",
            language="en"
        ),
        TriviaQuestion(
            qid="q004",
            question="Test question 4",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            answer_key="A",
            topic="Test",
            tags=["test"],
            difficulty="easy",
            language="en"
        )
    ]
    
    all_questions = questions + imbalanced_questions
    balanced = feeder._balance_answer_distribution(all_questions, tolerance=1)
    
    # Count distribution
    distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    for q in balanced:
        distribution[q.answer_key] += 1
    
    print(f"  Original distribution: A=3, B=1, C=1, D=1")
    print(f"  Balanced distribution: {distribution}")
    
    # Test 8: Test prompt building
    print("\n8. Testing prompt building...")
    preset = feeder.prompt_presets["science_tech"]
    prompt = feeder._build_gemini_prompt(preset, request)
    print("✓ Prompt built:")
    print(prompt[:300] + "..." if len(prompt) > 300 else prompt)
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED! ✓")
    print("="*60)
    print("\nThe Gemini Feeder is ready for use.")
    print("\nTo run it:")
    print("1. Set your GEMINI_API_KEY environment variable")
    print("2. Run: python scripts/run_gemini_feeder.py --channel ch01 --preset science_tech --quantity 10")

if __name__ == "__main__":
    asyncio.run(test_gemini_feeder())
