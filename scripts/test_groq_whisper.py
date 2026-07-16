"""Test Groq Whisper transcription vs local."""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


async def test_groq_whisper():
    """Test Groq Whisper API."""
    print("\n" + "="*60)
    print("TEST: Groq Whisper API")
    print("="*60)
    
    from app.asr.groq_whisper import is_groq_configured, transcribe_with_groq
    
    if not is_groq_configured():
        print("❌ GROQ_API_KEY not set")
        return False
    
    print("✓ Groq API key configured")
    
    # Find test audio
    test_audio = Path("tests/fixtures/short_sample.wav")
    if not test_audio.exists():
        print(f"❌ Test audio not found: {test_audio}")
        print("Run: python scripts/generate_sample_audio.py")
        return False
    
    print(f"✓ Test audio: {test_audio} ({test_audio.stat().st_size} bytes)")
    
    # Test Groq
    print("\nTranscribing with Groq...")
    start = time.time()
    result = await transcribe_with_groq(test_audio)
    duration = time.time() - start
    
    if result is None:
        print("❌ Groq transcription failed")
        return False
    
    print(f"✓ Transcribed in {duration:.2f}s")
    print(f"  Text: '{result.text}'")
    print(f"  Words: {len(result.words)}")
    print(f"  Provider: {result.provider}")
    print(f"  Model: {result.model}")
    
    return True


def test_local_whisper():
    """Test local Whisper for comparison."""
    print("\n" + "="*60)
    print("TEST: Local Whisper")
    print("="*60)
    
    from app.asr.whisper_service import _transcribe_local, get_model
    
    test_audio = Path("tests/fixtures/short_sample.wav")
    if not test_audio.exists():
        print(f"❌ Test audio not found")
        return False
    
    # Preload model
    print("Loading model...")
    get_model()
    print("✓ Model loaded")
    
    print("\nTranscribing with local Whisper...")
    start = time.time()
    result = _transcribe_local(str(test_audio))
    duration = time.time() - start
    
    print(f"✓ Transcribed in {duration:.2f}s")
    print(f"  Text: '{result.text}'")
    print(f"  Provider: {result.provider}")
    
    return True


async def main():
    print("\n" + "#"*60)
    print("#  WHISPER PERFORMANCE COMPARISON")
    print("#"*60)
    
    groq_ok = await test_groq_whisper()
    local_ok = test_local_whisper()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  Groq Whisper: {'✓' if groq_ok else '✗'}")
    print(f"  Local Whisper: {'✓' if local_ok else '✗'}")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
