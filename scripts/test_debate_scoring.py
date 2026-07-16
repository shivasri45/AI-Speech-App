"""Test script for debate content scoring.

Tests the full debate scoring pipeline including:
1. LLM client (Groq/Ollama)
2. Content scoring
3. Full AI score computation

Run from repo root:
    python scripts/test_debate_scoring.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


async def test_llm_client():
    """Test the LLM client connection."""
    print("\n" + "="*60)
    print("TEST 1: LLM Client Connection")
    print("="*60)
    
    from app.core.llm_client import llm
    
    print(f"Provider: {llm.provider}")
    print(f"Available: {llm.is_available}")
    
    if llm.provider == "groq":
        print(f"Groq API Key: {'✓ Set' if os.getenv('GROQ_API_KEY') else '✗ Not set'}")
    else:
        print(f"Ollama URL: {llm.ollama_url}")
    
    if not llm.is_available:
        print("\n❌ No LLM configured. Set GROQ_API_KEY in .env")
        return False
    
    # Test simple generation
    print("\nTesting simple generation...")
    try:
        response = await llm.generate("Say 'Hello, I am working!' in exactly 5 words.")
        print(f"Response: {response[:100]}...")
        print("✓ LLM client working!")
        return True
    except Exception as e:
        print(f"✗ LLM Error: {type(e).__name__}: {e}")
        return False


async def test_content_scoring():
    """Test content scoring with sample transcript."""
    print("\n" + "="*60)
    print("TEST 2: Content Scoring")
    print("="*60)
    
    from app.debate.content_scoring import score_debate_content
    
    # Sample debate data
    motion_title = "Social Media's Impact on Youth"
    motion_text = "This house believes that social media does more harm than good to young people's mental health and social development."
    
    # Test Case 1: Good relevant speech
    transcript_good = """
    I strongly support this motion. Social media has created an epidemic of anxiety 
    and depression among young people. Studies show that teenagers who spend more 
    than 3 hours daily on social media have double the risk of mental health issues.
    The constant comparison with edited, perfect lives leads to low self-esteem.
    Cyberbullying is rampant and has even led to tragic suicides.
    We must acknowledge that while social media connects us, it fundamentally 
    damages the mental wellbeing of our youth. Thank you.
    """
    
    # Test Case 2: Off-topic speech
    transcript_bad = """
    I think pizza is the best food in the world. My favorite toppings are 
    pepperoni and mushrooms. Last week I went to a new pizza place and it was 
    amazing. The cheese was so melty and delicious. Everyone should eat more pizza.
    """
    
    # Test Case 3: Short speech
    transcript_short = "I agree with this."
    
    print("\n--- Test Case 1: Relevant Speech ---")
    result1 = await score_debate_content(transcript_good, motion_title, motion_text)
    print(f"Available: {result1.available}")
    if result1.available:
        print(f"Relevance: {result1.relevance}/15")
        print(f"Arguments: {result1.arguments}/15")
        print(f"Structure: {result1.structure}/10")
        print(f"Vocabulary: {result1.vocabulary}/10")
        print(f"TOTAL: {result1.total}/50")
        print(f"Feedback: {result1.feedback}")
    else:
        print(f"Error: {result1.error}")
    
    print("\n--- Test Case 2: Off-Topic Speech ---")
    result2 = await score_debate_content(transcript_bad, motion_title, motion_text)
    print(f"Available: {result2.available}")
    if result2.available:
        print(f"Relevance: {result2.relevance}/15")
        print(f"Arguments: {result2.arguments}/15")
        print(f"TOTAL: {result2.total}/50")
        print(f"Feedback: {result2.feedback}")
    else:
        print(f"Error: {result2.error}")
    
    print("\n--- Test Case 3: Too Short ---")
    result3 = await score_debate_content(transcript_short, motion_title, motion_text)
    print(f"Available: {result3.available}")
    print(f"Error: {result3.error}")
    
    # Verify good > bad
    if result1.available and result2.available:
        if result1.total > result2.total:
            print("\n✓ Content scoring correctly ranks relevant > off-topic")
            return True
        else:
            print("\n✗ Scoring issue: off-topic scored higher than relevant!")
            return False
    return result1.available


async def test_full_ai_scoring():
    """Test the full AI scoring with content."""
    print("\n" + "="*60)
    print("TEST 3: Full AI Score Computation")
    print("="*60)
    
    from app.debate.service import compute_ai_score_with_content
    from app.schemas.pronunciation_schema import PronunciationResult
    from app.fluency.schemas import FluencyResult
    
    # Mock pronunciation result
    pronunciation = PronunciationResult(
        available=True,
        provider="mock",
        overall_score=75.0,
        per_word_results=[],
    )
    
    # Mock fluency result
    fluency = FluencyResult(
        words_per_minute=120,
        clarity_score=80.0,
        filler_word_count=2,
        pause_count=3,
        speech_rate_category="normal",
    )
    
    # Transcript and motion
    transcript = """
    I believe social media is harmful for youth mental health. The constant 
    scrolling and comparison creates anxiety. Studies prove this correlation.
    We need stricter regulations on social media usage for minors.
    """
    motion_title = "Social Media's Impact"
    motion_text = "Social media harms youth mental health."
    
    print("\nInputs:")
    print(f"  Pronunciation Score: {pronunciation.overall_score}")
    print(f"  Fluency Clarity: {fluency.clarity_score}")
    print(f"  Transcript length: {len(transcript)} chars")
    
    final_score, unavailable, breakdown = await compute_ai_score_with_content(
        pronunciation=pronunciation,
        fluency=fluency,
        transcript=transcript,
        motion_title=motion_title,
        motion_text=motion_text,
    )
    
    print(f"\nResults:")
    print(f"  Final Score: {final_score}/100")
    print(f"  Scoring Unavailable: {unavailable}")
    print(f"\nBreakdown:")
    
    if breakdown:
        pron = breakdown.get("pronunciation", {})
        flu = breakdown.get("fluency", {})
        cont = breakdown.get("content", {})
        
        print(f"  Pronunciation: {pron.get('weighted', 'N/A')}/25 (raw: {pron.get('raw')})")
        print(f"  Fluency: {flu.get('weighted', 'N/A')}/25 (raw: {flu.get('raw')})")
        print(f"  Content: {cont.get('total', 'N/A')}/50")
        print(f"  Content Feedback: {cont.get('feedback', 'N/A')}")
    
    if final_score > 0:
        print("\n✓ Full AI scoring working!")
        return True
    else:
        print("\n✗ Scoring failed")
        return False


async def test_without_content():
    """Test fallback when content scoring unavailable."""
    print("\n" + "="*60)
    print("TEST 4: Fallback Without Content Scoring")
    print("="*60)
    
    from app.debate.service import compute_ai_score_with_content
    from app.schemas.pronunciation_schema import PronunciationResult
    from app.fluency.schemas import FluencyResult
    
    pronunciation = PronunciationResult(
        available=True,
        provider="mock",
        overall_score=80.0,
        per_word_results=[],
    )
    
    fluency = FluencyResult(
        words_per_minute=120,
        clarity_score=70.0,
        filler_word_count=2,
        pause_count=3,
        speech_rate_category="normal",
    )
    
    # Empty transcript - should trigger fallback
    final_score, unavailable, breakdown = await compute_ai_score_with_content(
        pronunciation=pronunciation,
        fluency=fluency,
        transcript="",  # Empty
        motion_title="Test",
        motion_text="Test motion",
    )
    
    print(f"Final Score (no content): {final_score}/100")
    print(f"Expected: ~75 (scaled from pron 80 + fluency 70)")
    
    # With only pron+fluency, score should be scaled
    expected = (80 * 0.25 + 70 * 0.25) * 2  # = 75
    if 70 <= final_score <= 80:
        print("✓ Fallback scoring working correctly!")
        return True
    else:
        print(f"✗ Expected ~75, got {final_score}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("#  DEBATE CONTENT SCORING TEST SUITE")
    print("#"*60)
    
    results = []
    
    # Test 1: LLM Client
    results.append(("LLM Client", await test_llm_client()))
    
    # Test 2: Content Scoring (only if LLM works)
    if results[0][1]:
        results.append(("Content Scoring", await test_content_scoring()))
        results.append(("Full AI Scoring", await test_full_ai_scoring()))
    else:
        print("\n⚠ Skipping content tests - LLM not available")
        results.append(("Content Scoring", None))
        results.append(("Full AI Scoring", None))
    
    # Test 4: Fallback (always run)
    results.append(("Fallback Scoring", await test_without_content()))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for name, passed in results:
        if passed is True:
            print(f"  ✓ {name}")
        elif passed is False:
            print(f"  ✗ {name}")
        else:
            print(f"  ⚠ {name} (skipped)")
    
    all_passed = all(r[1] is not False for r in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
