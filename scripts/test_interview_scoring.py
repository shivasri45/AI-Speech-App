"""Test Interview Studio answer content scoring end-to-end."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


async def test_content_scoring():
    """Test the LLM-based answer scoring."""
    print("\n" + "="*60)
    print("TEST: Interview Answer Content Scoring")
    print("="*60)
    
    from app.interview.content_scoring import score_interview_answer
    
    # Test 1: Good behavioural answer (STAR method)
    print("\n--- Test 1: Good STAR Answer ---")
    good_answer = """
    Sure, I'd love to share an example. At my previous internship at TCS, we had a project
    deadline that was moved up by two weeks. The team was stressed and morale was low.
    I took the initiative to organize a daily standup meeting and created a shared task board.
    I also volunteered to handle the most complex module myself to reduce load on others.
    As a result, we delivered the project three days before the new deadline, and our manager
    specifically praised the team coordination. I learned that clear communication and
    taking ownership can transform a challenging situation into a success story.
    """
    
    result1 = await score_interview_answer(
        transcript=good_answer,
        question_prompt="Tell me about a time you showed leadership in a team project.",
        question_category="behavioural",
    )
    print(f"Available: {result1.available}")
    if result1.available:
        print(f"Relevance:     {result1.relevance}/25")
        print(f"Structure:     {result1.structure}/25")
        print(f"Depth:         {result1.depth}/25")
        print(f"Communication: {result1.communication}/25")
        print(f"TOTAL:         {result1.total}/100")
        print(f"Feedback:      {result1.feedback}")
        print(f"Strengths:     {result1.strengths}")
        print(f"Improvements:  {result1.improvements}")
    else:
        print(f"Error: {result1.error}")

    # Test 2: Weak/vague answer
    print("\n--- Test 2: Weak Answer ---")
    weak_answer = """
    Um, yeah, I think leadership is important. I like to help people.
    Sometimes in college we do group projects and I try to do my part.
    I think being a good leader means listening to others.
    """
    
    result2 = await score_interview_answer(
        transcript=weak_answer,
        question_prompt="Tell me about a time you showed leadership in a team project.",
        question_category="behavioural",
    )
    print(f"Available: {result2.available}")
    if result2.available:
        print(f"Relevance:     {result2.relevance}/25")
        print(f"Structure:     {result2.structure}/25")
        print(f"Depth:         {result2.depth}/25")
        print(f"Communication: {result2.communication}/25")
        print(f"TOTAL:         {result2.total}/100")
        print(f"Feedback:      {result2.feedback}")
    else:
        print(f"Error: {result2.error}")

    # Test 3: Off-topic answer
    print("\n--- Test 3: Off-Topic Answer ---")
    offtopic = """
    I really enjoy playing cricket on weekends. My favorite player is Virat Kohli.
    Last Sunday we had a match and I scored 45 runs which was my personal best.
    The weather was nice and we had a great time with friends.
    """
    
    result3 = await score_interview_answer(
        transcript=offtopic,
        question_prompt="What are your greatest strengths as a software developer?",
        question_category="technical",
    )
    print(f"Available: {result3.available}")
    if result3.available:
        print(f"Relevance:     {result3.relevance}/25")
        print(f"TOTAL:         {result3.total}/100")
        print(f"Feedback:      {result3.feedback}")
    else:
        print(f"Error: {result3.error}")

    # Test 4: Too short
    print("\n--- Test 4: Too Short ---")
    result4 = await score_interview_answer(
        transcript="I like coding.",
        question_prompt="Why do you want this job?",
        question_category="general",
    )
    print(f"Available: {result4.available}")
    print(f"Error: {result4.error}")
    print(f"Feedback: {result4.feedback}")

    # Verify scoring order: good > weak > offtopic
    print("\n" + "="*60)
    print("SCORING COMPARISON")
    print("="*60)
    scores = [
        ("Good STAR", result1.total if result1.available else 0),
        ("Weak/Vague", result2.total if result2.available else 0),
        ("Off-Topic", result3.total if result3.available else 0),
    ]
    for name, score in scores:
        bar = "█" * (score // 5) + "░" * (20 - score // 5)
        print(f"  {name:12s} [{bar}] {score}/100")
    
    if result1.available and result2.available and result3.available:
        if result1.total > result2.total > result3.total:
            print("\n✓ Scoring order correct: Good > Weak > Off-topic")
            return True
        else:
            print(f"\n✗ Unexpected order: {result1.total} vs {result2.total} vs {result3.total}")
            return False
    return result1.available


async def test_whisper_integration():
    """Test that Whisper transcription works (needed for score-answer endpoint)."""
    print("\n" + "="*60)
    print("TEST: Whisper ASR Integration")
    print("="*60)
    
    test_audio = Path("tests/fixtures/short_sample.wav")
    if not test_audio.exists():
        print(f"⚠ Test audio not found: {test_audio}")
        print("  Skipping (generate with: python scripts/generate_sample_audio.py)")
        return True  # Not a failure
    
    from app.asr.whisper_service import transcribe_audio
    
    print(f"Transcribing {test_audio}...")
    result = transcribe_audio(str(test_audio))
    print(f"Provider: {result.provider}")
    print(f"Text: '{result.text}'")
    print(f"Words: {len(result.words)}")
    print("✓ Whisper working")
    return True


async def test_endpoint_smoke():
    """Quick check that the endpoint is registered."""
    print("\n" + "="*60)
    print("TEST: Endpoint Registration")
    print("="*60)
    
    from app.main import app
    
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append(route.path)
        elif hasattr(route, 'routes'):
            for r in route.routes:
                if hasattr(r, 'path'):
                    routes.append(r.path)
    
    required = ["/interview/analyze", "/interview/score-answer", "/interview/submissions"]
    for path in required:
        found = any(path in r for r in routes)
        status = "✓" if found else "✗"
        print(f"  {status} {path}")
    
    return all(any(p in r for r in routes) for p in required)


async def main():
    print("\n" + "#"*60)
    print("#  INTERVIEW STUDIO TEST SUITE")
    print("#"*60)
    
    results = []
    
    results.append(("Endpoint Registration", await test_endpoint_smoke()))
    results.append(("Whisper ASR", await test_whisper_integration()))
    results.append(("Content Scoring", await test_content_scoring()))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, passed in results:
        print(f"  {'✓' if passed else '✗'} {name}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("✓ ALL TESTS PASSED!" if all_passed else "✗ SOME TESTS FAILED"))
    print("="*60 + "\n")
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
