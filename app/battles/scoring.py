from typing import Dict, Any

def calculate_battle_score(player_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates a balanced gamified score based on multidimensional speech analytics.
    Defensively parses nested criteria shapes and adaptively handles unconfigured service metrics.
    """
    # 1. Extract and standardize upstream blocks defensively
    transcription_block = player_payload.get("transcription", {})
    pronunciation_block = player_payload.get("pronunciation", {})
    fluency_block = player_payload.get("fluency", {})
    communication_block = player_payload.get("communication", {})
    criteria = communication_block.get("criteria", {})

    # 2. Extract metrics directly matching engine payload footprints
    # Fluency data maps (0-100)
    fluency_score = float(fluency_block.get("score", 0.0))

    # Communication metrics map from 0-10 fields; normalized out of 100
    clarity_score = float(criteria.get("clarity", {}).get("score", 0.0)) * 10.0
    structure_score = float(criteria.get("structure", {}).get("score", 0.0)) * 10.0
    relevance_score = float(criteria.get("relevance", {}).get("score", 0.0)) * 10.0
    evidence_score = float(criteria.get("evidence", {}).get("score", 0.0)) * 10.0
    rebuttal_score = float(criteria.get("rebuttal", {}).get("score", 0.0)) * 10.0

    # Compound Argument Quality parameter out of structural and evidential value
    argument_quality = (structure_score + evidence_score) / 2.0

    # 3. Base weight configuration parameters
    weights = {
        "pronunciation": 0.15,
        "fluency": 0.20,
        "relevance": 0.15,
        "argument_quality": 0.25,
        "rebuttal": 0.15,
        "time_discipline": 0.10
    }

    # 4. Process Pronunciation engine availability adaptively
    pronunciation_score = 0.0
    if pronunciation_block.get("available") is True:
        pronunciation_score = float(pronunciation_block.get("overall_score", 0.0))
    else:
        # If the engine is unconfigured, redistribute its weight among operational engines
        # Prevents students from receiving zeroed metric penalties
        dropped_weight = weights["pronunciation"]
        weights["pronunciation"] = 0.0
        
        active_keys = ["fluency", "relevance", "argument_quality", "rebuttal"]
        weight_increment = dropped_weight / len(active_keys)
        for key in active_keys:
            weights[key] += weight_increment

    # 5. Extract time behavior constraints from session footprints
    # Deduct up to 10 points if speech footprint doesn't hit ideal boundaries (e.g., under 15 seconds)
    duration = float(player_payload.get("audio", {}).get("duration_seconds", 0.0))
    time_discipline_score = 100.0 if duration >= 15.0 else max(0.0, (duration / 15.0) * 100.0)

    # 6. Execute balanced mathematical aggregation
    weighted_total = (
        (pronunciation_score * weights["pronunciation"]) +
        (fluency_score * weights["fluency"]) +
        (relevance_score * weights["relevance"]) +
        (argument_quality * weights["argument_quality"]) +
        (rebuttal_score * weights["rebuttal"]) +
        (time_discipline_score * weights["time_discipline"])
    )

    final_score = max(0, min(100, int(round(weighted_total))))

    return {
        "final_score": final_score,
        "breakdown": {
            "pronunciation": int(round(pronunciation_score)),
            "fluency": int(round(fluency_score)),
            "relevance": int(round(relevance_score)),
            "argument_quality": int(round(argument_quality)),
            "rebuttal": int(round(rebuttal_score)),
            "time_discipline": int(round(time_discipline_score))
        }
    }

def evaluate_battle_winner(player1_payload: Dict[str, Any], player2_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates complete performance structures and resolves outcomes deterministically.
    Uses argument quality and fluency as strategic tie-breakers if point scores are equivalent.
    """
    p1_meta = calculate_battle_score(player1_payload)
    p2_meta = calculate_battle_score(player2_payload)

    p1_score = p1_meta["final_score"]
    p2_score = p2_meta["final_score"]

    winner = "tie"
    tie_broken_by = None

    if p1_score > p2_score:
        winner = "player1"
    elif p2_score > p1_score:
        winner = "player2"
    else:
        # --- STRATEGIC TIE-BREAKER LOGIC ROUTINE ---
        # Tier 1: Look at Argument Quality
        p1_arg = p1_meta["breakdown"]["argument_quality"]
        p2_arg = p2_meta["breakdown"]["argument_quality"]
        if p1_arg != p2_arg:
            winner = "player1" if p1_arg > p2_arg else "player2"
            tie_broken_by = "argument_quality"
        else:
            # Tier 2: Look at Fluency Metrics
            p1_flu = p1_meta["breakdown"]["fluency"]
            p2_flu = p2_meta["breakdown"]["fluency"]
            if p1_flu != p2_flu:
                winner = "player1" if p1_flu > p2_flu else "player2"
                tie_broken_by = "fluency"

    return {
        "winner": winner,
        "margin": abs(p1_score - p2_score),
        "tie_broken_by": tie_broken_by,
        "player1": {
            "total_score": p1_score,
            "metrics": p1_meta["breakdown"]
        },
        "player2": {
            "total_score": p2_score,
            "metrics": p2_meta["breakdown"]
        }
    }