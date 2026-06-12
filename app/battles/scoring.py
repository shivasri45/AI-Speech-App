from typing import Dict, Any

WEIGHTS = {
    "pronunciation_score": 0.20,
    "fluency_score": 0.20,
    "relevance_score": 0.15,
    "argument_quality": 0.20,
    "time_discipline": 0.10,
    "rebuttal_strength": 0.15
}


def _normalize_score(value: Any) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, min(100.0, numeric_value))


def calculate_battle_score(player_data: Dict[str, Any]) -> int:
    """
    Calculates a 1v1 battle score based on pronunciation, fluency, relevance, 
    argument quality, time discipline, and rebuttal strength.
    
    According to the TEAM_SPLIT.md Phase 4B rules, we avoid making pronunciation 
    the only battle score.
    """
    
    if not isinstance(player_data, dict):
        player_data = {}

    weighted_score = 0.0
    for score_key, weight in WEIGHTS.items():
        weighted_score += _normalize_score(player_data.get(score_key, 0)) * weight

    return int(round(weighted_score))

def evaluate_battle_winner(player1_data: Dict[str, Any], player2_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the complete state of a 1v1 battle and determines the winner.
    """
    p1_score = calculate_battle_score(player1_data if isinstance(player1_data, dict) else {})
    p2_score = calculate_battle_score(player2_data if isinstance(player2_data, dict) else {})
    
    winner = "tie"
    if p1_score > p2_score:
        winner = "player1"
    elif p2_score > p1_score:
        winner = "player2"
        
    return {
        "player1_score": p1_score,
        "player2_score": p2_score,
        "winner": winner,
        "margin": abs(p1_score - p2_score)
    }
