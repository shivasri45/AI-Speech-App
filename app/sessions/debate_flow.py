from enum import Enum
from typing import List, Dict, Any, Optional

class DebateRoundType(Enum):
    OPENING = "opening"
    RESPONSE = "response"
    REBUTTAL = "rebuttal"
    CLOSING = "closing"

class DebateFlow:
    """
    Manages the lifecycle and state of a single debate session.
    A debate has defined round flows: Opening, Response, Rebuttal, Closing.
    """
    def __init__(self, topic: str):
        normalized_topic = (topic or "").strip()
        self.topic = normalized_topic if normalized_topic else "Untitled debate topic"
        self.rounds = [
            DebateRoundType.OPENING,
            DebateRoundType.RESPONSE,
            DebateRoundType.REBUTTAL,
            DebateRoundType.CLOSING
        ]
        self.current_round_index = 0
        self.transcripts: List[Dict[str, Any]] = []

    def get_current_round(self) -> Optional[DebateRoundType]:
        if 0 <= self.current_round_index < len(self.rounds):
            return self.rounds[self.current_round_index]
        return None

    def advance_round(self, round_data: Dict[str, Any]):
        """
        Record the round output and advance to the next debate stage.
        `round_data` should include transcripts, scores, and speaker info.
        """
        if self.is_complete():
            return False

        if not isinstance(round_data, dict):
            round_data = {}

        current_round = self.get_current_round()
        self.transcripts.append({
            "round_index": self.current_round_index,
            "round_type": current_round.value if current_round else "finished",
            "data": round_data
        })
        self.current_round_index += 1
        return True
        
    def is_complete(self) -> bool:
        """
        Check if the debate round has completed all stages.
        """
        return self.current_round_index >= len(self.rounds)

    def get_summary(self) -> Dict[str, Any]:
        """
        Generates a summary of all rounds completed in the debate.
        """
        state = self.get_state()
        return {
            "topic": self.topic,
            "is_complete": state["is_complete"],
            "current_round": self.get_current_round().value if self.get_current_round() else "finished",
            "completed_rounds": state["completed_rounds"],
            "total_rounds": state["total_rounds"],
            "history": self.transcripts
        }

    def get_state(self) -> Dict[str, Any]:
        total_rounds = len(self.rounds)
        completed_rounds = max(0, min(self.current_round_index, total_rounds))
        return {
            "topic": self.topic,
            "current_round_index": self.current_round_index,
            "completed_rounds": completed_rounds,
            "total_rounds": total_rounds,
            "is_complete": self.is_complete()
        }
