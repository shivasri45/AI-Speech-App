import pytest
from app.fluency.service import FluencyService
from app.rubrics.service import RubricService
from app.battles.scoring import evaluate_battle_winner, calculate_battle_score
from app.sessions.debate_flow import DebateFlow, DebateRoundType

def test_fluency_service():
    service = FluencyService()
    
    # Mock Whisper transcript output
    mock_transcript = {
        "text": "The design is like very subtle um you know",
        "words": [
            {"word": "The", "start": 0.0, "end": 0.2},
            {"word": "design", "start": 0.2, "end": 0.7},
            {"word": "is", "start": 0.7, "end": 0.9},
            {"word": "like", "start": 0.9, "end": 1.2},  # Filler
            {"word": "very", "start": 3.0, "end": 3.5},  # Long pause before this
            {"word": "subtle", "start": 3.5, "end": 4.0},
            {"word": "um", "start": 4.0, "end": 4.5},    # Filler
            {"word": "subtle", "start": 4.5, "end": 5.0} # Repetition (different context, but simulating matching previous word)
        ]
    }
    
    # Analyze with a total audio duration of 6.0 seconds
    result = service.analyze_fluency(mock_transcript, total_duration_seconds=6.0)
    
    # 8 words in 6 seconds (0.1 minutes) -> 8 / 0.1 = 80 WPM
    assert result["words_per_minute"] == 80
    assert result["filler_word_count"] == 2 # "like", "um"
    assert result["long_pause_count"] == 1  # between "like" and "very"
    assert result["speech_duration_seconds"] == 5.0 # 5.0 - 0.0
    assert result["repetition_count"] == 0
    assert result["silence_ratio"] == 0.17
    assert result["score"] == 71

def test_fluency_service_handles_missing_duration_and_malformed_words():
    service = FluencyService()

    transcript_with_bad_words = {
        "words": [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.5, "end": 1.0},
            "bad-word-row",
            {"word": "again", "start": 1.2, "end": 1.7},
            {"word": "again", "start": 1.7, "end": 2.0},
            {"word": "", "start": 2.0, "end": 2.2},
        ]
    }

    result = service.analyze_fluency(transcript_with_bad_words, total_duration_seconds=0.0)

    assert result["total_duration_seconds"] == 2.0
    assert result["speech_duration_seconds"] == 2.0
    assert result["words_per_minute"] == 120
    assert result["repetition_count"] == 1
    assert result["silence_ratio"] == 0.0

    empty_result = service.analyze_fluency({"words": []}, total_duration_seconds=4.0)
    assert empty_result["silence_ratio"] == 1.0
    assert empty_result["score"] == 0

def test_rubric_service():
    service = RubricService()

    transcript = (
        "First, I believe AI in education helps students because it gives quick feedback. "
        "For example, a study showed 20 percent faster improvement. "
        "However, some may argue it can distract students, but clear rules solve that. "
        "In conclusion, AI supports better learning outcomes."
    )
    result = service.evaluate_communication(transcript, "AI in education")
    result_repeat = service.evaluate_communication(transcript, "AI in education")

    assert result["available"] is True
    assert result["rubric_version"] == "v2"
    assert result == result_repeat
    assert 0 <= result["overall_score"] <= 100
    for key in ["clarity", "structure", "relevance", "evidence", "confidence", "rebuttal"]:
        assert key in result["criteria"]
        assert isinstance(result["criteria"][key]["score"], int)
        assert isinstance(result["criteria"][key]["feedback"], str)
        assert len(result["criteria"][key]["feedback"]) > 0

    missing_topic = service.evaluate_communication("This is a speech", None)
    assert missing_topic["available"] is False
    assert missing_topic["overall_score"] is None
    assert "Expected topic is required" in missing_topic["criteria"]["clarity"]["feedback"]

    empty_result = service.evaluate_communication("", "AI in education")
    assert empty_result["available"] is False
    assert empty_result["overall_score"] is None

def test_battle_scoring():
    player_1 = {
        "pronunciation_score": 80,
        "fluency_score": 90,
        "relevance_score": 70,
        "argument_quality": 85,
        "time_discipline": 100,
        "rebuttal_strength": 60
    }
    
    player_2 = {
        "pronunciation_score": 70,
        "fluency_score": 75,
        "relevance_score": 90,
        "argument_quality": 90,
        "time_discipline": 80,
        "rebuttal_strength": 90
    }
    
    result = evaluate_battle_winner(player_1, player_2)
    assert result["winner"] == "player2"
    assert result["player1_score"] == 80
    assert result["player2_score"] == 82
    assert result["margin"] == 2

    clamped_score = calculate_battle_score({
        "pronunciation_score": 250,
        "fluency_score": "75",
        "relevance_score": -10,
        "argument_quality": None,
        "time_discipline": "not-a-number",
        "rebuttal_strength": 120
    })
    assert clamped_score == 46

    malformed_result = evaluate_battle_winner({"pronunciation_score": 200}, None)
    assert malformed_result["winner"] == "player1"
    assert malformed_result["player1_score"] == 20
    assert malformed_result["player2_score"] == 0

def test_debate_flow():
    flow = DebateFlow("Is AI good for students?")
    
    assert not flow.is_complete()
    assert flow.get_current_round() == DebateRoundType.OPENING
    
    # Simulate completely running through rounds
    for _ in range(4):
        assert flow.advance_round({"mock_audio": "audio.wav", "speaker": "student"})
        
    assert flow.is_complete()
    assert flow.advance_round({"mock_audio": "extra.wav"}) is False

    summary = flow.get_summary()
    assert summary["is_complete"] is True
    assert summary["current_round"] == "finished"
    assert summary["completed_rounds"] == 4
    assert summary["total_rounds"] == 4
    assert len(summary["history"]) == 4

    untitled_flow = DebateFlow("   ")
    assert untitled_flow.get_summary()["topic"] == "Untitled debate topic"
