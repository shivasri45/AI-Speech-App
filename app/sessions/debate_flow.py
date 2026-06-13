from enum import Enum
from typing import List, Dict, Any, Optional

class DebateRoundType(Enum):
    OPENING = "opening"
    RESPONSE = "response"
    REBUTTAL = "rebuttal"
    CLOSING = "closing"

class DebateFlow:
    """
    Manages the lifecycle, state progression, and serialization of a 1v1 debate session.
    Engineered to securely restore states across stateless API worker boundaries.
    """
    def __init__(self, session_id: str, topic: str, initial_round_index: int = 0, history: Optional[List[Dict[str, Any]]] = None):
        self.session_id = session_id
        self.topic = topic
        self.rounds = [
            DebateRoundType.OPENING,
            DebateRoundType.RESPONSE,
            DebateRoundType.REBUTTAL,
            DebateRoundType.CLOSING
        ]
        self.current_round_index = initial_round_index
        self.transcripts: List[Dict[str, Any]] = history or []

    @classmethod
    def restore_from_database(cls, db_session_model: Any) -> "DebateFlow":
        """
        Production Factory Method to rehydrate a debate's state engine 
        from a database record across separate stateless API requests.
        """
        return cls(
            session_id=str(db_session_model.id),
            topic=db_session_model.topic,
            initial_round_index=db_session_model.current_round_index,
            history=db_session_model.history_json or []
        )

    def get_current_round(self) -> Optional[DebateRoundType]:
        """Returns the active round type or None if the session is finalized."""
        if 0 <= self.current_round_index < len(self.rounds):
            return self.rounds[self.current_round_index]
        return None

    def get_assignment_type_context(self) -> str:
        """
        Maps the exact runtime string parameter needed to route 
        evaluation criteria seamlessly to the Gemini Rubric Service.
        """
        return "debate"

    def advance_round(self, speaker_id: str, round_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates performance signatures, records the historical matrix block,
        and advances the session pointer safely to the subsequent stage.
        """
        current_round = self.get_current_round()
        if not current_round:
            raise ValueError(f"Cannot advance debate session '{self.session_id}': Already complete.")

        # Explicitly enforce structural data logging constraints
        round_log_entry = {
            "round_index": self.current_round_index,
            "round_type": current_round.value,
            "speaker_id": speaker_id,
            "analysis": {
                "transcription": round_payload.get("transcription", {}),
                "fluency": round_payload.get("fluency", {}),
                "communication": round_payload.get("communication", {}),
                "battle_scores": round_payload.get("battle_scores", {})
            }
        }
        
        self.transcripts.append(round_log_entry)
        
        # Advance the pointer
        self.current_round_index += 1
        
        return {
            "session_id": self.session_id,
            "just_completed": current_round.value,
            "next_round": self.get_current_round().value if self.get_current_round() else "finished",
            "is_complete": self.is_complete()
        }
        
    def is_complete(self) -> bool:
        """Evaluates whether all structural segments have run to final termination."""
        return self.current_round_index >= len(self.rounds)

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Compiles the overall structural performance history across all 
        stages for direct rendering on student dashboards.
        """
        # Calculate dynamic point metrics aggregate across active transcript histories
        p1_cumulative = 0
        p2_cumulative = 0
        rounds_played = len(self.transcripts)

        for entry in self.transcripts:
            scores = entry.get("analysis", {}).get("battle_scores", {})
            # Read standardized player profiles populated via battles/scoring.py
            p1_cumulative += scores.get("player1", {}).get("total_score", 0)
            p2_cumulative += scores.get("player2", {}).get("total_score", 0)

        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "is_complete": self.is_complete(),
            "rounds_configured": len(self.rounds),
            "rounds_played": rounds_played,
            "current_round_status": self.get_current_round().value if self.get_current_round() else "finished",
            "leaderboard": {
                "player1_cumulative_score": p1_cumulative,
                "player2_cumulative_score": p2_cumulative,
                "average_score": int((p1_cumulative + p2_cumulative) / max(1, rounds_played * 2))
            },
            "history": self.transcripts
        }