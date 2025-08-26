#!/usr/bin/env python3
"""
🔊 Test Suite for Text-to-Speech
Test TTS generation with different voices and text lengths
"""

import os
import sys
import tempfile
from pathlib import Path

# Add core modules to path
sys.path.append(str(Path(__file__).parent / "core"))

from google.cloud import texttospeech

# Configuration
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

def test_tts_voices():
    """Test different TTS voices"""
    print("🔊 Testing TTS Voices")
    print("=" * 60)
    
    if not GOOGLE_APPLICATION_CREDENTIALS:
        print("❌ Error: GOOGLE_APPLICATION_CREDENTIALS environment variable is required")
        print("Set it with: export GOOGLE_APPLICATION_CREDENTIALS='path/to/credentials.json'")
        return
    
    client = texttospeech.TextToSpeechClient()
    
    # Test different voices
    test_voices = [
        ("en-US-Neural2-F", "Female voice"),
        ("en-US-Neural2-M", "Male voice"),
        ("en-US-Neural2-A", "Female voice (alternative)"),
        ("en-US-Neural2-C", "Male voice (alternative)"),
        ("en-US-Neural2-D", "Female voice (alternative)"),
        ("en-US-Neural2-E", "Male voice (alternative)")
    ]
    
    test_text = "This is a test of the text-to-speech system. How does this voice sound?"
    
    results = {}
    
    for voice_name, description in test_voices:
        print(f"\n🎤 Testing voice: {voice_name} ({description})")
        
        try:
            # Create synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=test_text)
            
            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_name
            )
            
            # Select the type of audio file
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0
            )
            
            # Perform the text-to-speech request
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            
            # Save the audio to a file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                f.write(response.audio_content)
                temp_file = f.name
            
            # Get file size
            file_size = os.path.getsize(temp_file)
            file_size_kb = file_size / 1024
            
            print(f"   ✅ Generated audio: {file_size_kb:.1f} KB")
            
            # Clean up
            os.unlink(temp_file)
            
            results[voice_name] = "✅ PASS"
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results[voice_name] = "❌ FAIL"
    
    # Summary
    print(f"\n📊 Voice Test Summary")
    print("=" * 60)
    for voice_name, result in results.items():
        print(f"   {voice_name}: {result}")

def test_tts_text_lengths():
    """Test TTS with different text lengths"""
    print(f"\n📏 Testing TTS with Different Text Lengths")
    print("=" * 60)
    
    if not GOOGLE_APPLICATION_CREDENTIALS:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
        return
    
    client = texttospeech.TextToSpeechClient()
    
    # Test different text lengths
    test_cases = [
        ("Short", "Hello world."),
        ("Medium", "This is a medium length sentence that tests the TTS system with more content."),
        ("Long", "This is a much longer sentence that contains significantly more words and should test how the text-to-speech system handles extended content without breaking or producing poor quality audio."),
        ("Very Long", "This is an extremely long sentence that pushes the boundaries of what the text-to-speech system can handle gracefully. It contains many words, multiple clauses, and complex sentence structure to thoroughly test the robustness and quality of the TTS generation process.")
    ]
    
    voice_name = "en-US-Neural2-F"  # Use a reliable voice
    
    results = {}
    
    for test_name, test_text in test_cases:
        print(f"\n📝 Testing: {test_name} text ({len(test_text)} characters)")
        
        try:
            # Create synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=test_text)
            
            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_name
            )
            
            # Select the type of audio file
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0
            )
            
            # Perform the text-to-speech request
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            
            # Save the audio to a file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                f.write(response.audio_content)
                temp_file = f.name
            
            # Get file size and estimate duration
            file_size = os.path.getsize(temp_file)
            file_size_kb = file_size / 1024
            
            # Rough estimate: 1KB ≈ 1 second of audio
            estimated_duration = file_size_kb
            
            print(f"   ✅ Generated: {file_size_kb:.1f} KB (~{estimated_duration:.1f}s)")
            
            # Clean up
            os.unlink(temp_file)
            
            results[test_name] = "✅ PASS"
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results[test_name] = "❌ FAIL"
    
    # Summary
    print(f"\n📊 Text Length Test Summary")
    print("=" * 60)
    for test_name, result in results.items():
        print(f"   {test_name}: {result}")

def test_tts_speaking_rates():
    """Test TTS with different speaking rates"""
    print(f"\n⚡ Testing TTS with Different Speaking Rates")
    print("=" * 60)
    
    if not GOOGLE_APPLICATION_CREDENTIALS:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
        return
    
    client = texttospeech.TextToSpeechClient()
    
    # Test different speaking rates
    test_rates = [
        (0.5, "Slow"),
        (0.75, "Slow-Normal"),
        (1.0, "Normal"),
        (1.25, "Fast-Normal"),
        (1.5, "Fast"),
        (2.0, "Very Fast")
    ]
    
    test_text = "This sentence tests different speaking rates for the text-to-speech system."
    voice_name = "en-US-Neural2-F"
    
    results = {}
    
    for rate, description in test_rates:
        print(f"\n🎯 Testing rate: {rate}x ({description})")
        
        try:
            # Create synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=test_text)
            
            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_name
            )
            
            # Select the type of audio file
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=rate,
                pitch=0.0
            )
            
            # Perform the text-to-speech request
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            
            # Save the audio to a file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                f.write(response.audio_content)
                temp_file = f.name
            
            # Get file size
            file_size = os.path.getsize(temp_file)
            file_size_kb = file_size / 1024
            
            print(f"   ✅ Generated: {file_size_kb:.1f} KB")
            
            # Clean up
            os.unlink(temp_file)
            
            results[f"{rate}x"] = "✅ PASS"
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results[f"{rate}x"] = "❌ FAIL"
    
    # Summary
    print(f"\n📊 Speaking Rate Test Summary")
    print("=" * 60)
    for rate, result in results.items():
        print(f"   {rate}: {result}")

def main():
    """Main test runner"""
    print("🔊 Text-to-Speech Test Suite")
    print("=" * 60)
    
    # Test voices
    test_tts_voices()
    
    # Test text lengths
    test_tts_text_lengths()
    
    # Test speaking rates
    test_tts_speaking_rates()
    
    print(f"\n🎉 TTS Test Suite Complete!")

if __name__ == "__main__":
    main()
