import re
from typing import Dict, Any, Optional, List

class RubricService:
    CRITERIA_KEYS = ["clarity", "structure", "relevance", "evidence", "confidence", "rebuttal"]

    def __init__(self):
        self.rubric_version = "v2"

    def evaluate_communication(self, transcript_text: str, expected_topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluates communication quality deterministically based on transcript and expected topic.
        """
        cleaned_transcript = (transcript_text or "").strip()
        cleaned_topic = (expected_topic or "").strip()

        if not cleaned_transcript:
            return self._unavailable_result("No transcript text was provided.")

        transcript_tokens = self._tokenize(cleaned_transcript)
        if not transcript_tokens:
            return self._unavailable_result("Transcript did not contain enough words to score.")

        if not cleaned_topic:
            return self._unavailable_result("Expected topic is required for communication rubric scoring.")

        topic_tokens = self._topic_tokens(cleaned_topic)
        if not topic_tokens:
            return self._unavailable_result("Expected topic did not contain scorable words.")

        clarity = self._score_clarity(cleaned_transcript, transcript_tokens)
        structure = self._score_structure(cleaned_transcript)
        relevance = self._score_relevance(transcript_tokens, topic_tokens)
        evidence = self._score_evidence(cleaned_transcript)
        confidence = self._score_confidence(transcript_tokens)
        rebuttal = self._score_rebuttal(cleaned_transcript)

        criteria = {
            "clarity": clarity,
            "structure": structure,
            "relevance": relevance,
            "evidence": evidence,
            "confidence": confidence,
            "rebuttal": rebuttal
        }
        criterion_scores = [criterion["score"] for criterion in criteria.values()]
        overall_score = int(round((sum(criterion_scores) / (len(criterion_scores) * 10)) * 100))

        return {
            "available": True,
            "rubric_version": self.rubric_version,
            "overall_score": overall_score,
            "criteria": criteria
        }

    def _unavailable_result(self, reason: str) -> Dict[str, Any]:
        criteria = {
            key: {"score": None, "feedback": reason}
            for key in self.CRITERIA_KEYS
        }
        return {
            "available": False,
            "rubric_version": self.rubric_version,
            "overall_score": None,
            "criteria": criteria
        }

    def _tokenize(self, text: str) -> List[str]:
        return [token for token in re.findall(r"[a-zA-Z']+", text.lower()) if token]

    def _topic_tokens(self, topic: str) -> List[str]:
        stop_words = {"a", "an", "the", "is", "are", "to", "for", "and", "of", "in", "on"}
        return [token for token in self._tokenize(topic) if token not in stop_words]

    def _score_clarity(self, transcript_text: str, tokens: List[str]) -> Dict[str, Any]:
        sentence_fragments = [s.strip() for s in re.split(r"[.!?]+", transcript_text) if s.strip()]
        sentence_count = max(1, len(sentence_fragments))
        average_sentence_length = len(tokens) / sentence_count
        filler_words = {"um", "uh", "like", "basically", "actually", "you", "know"}
        filler_count = sum(1 for token in tokens if token in filler_words)

        score = 10
        if average_sentence_length > 24:
            score -= 2
        if average_sentence_length < 4:
            score -= 2
        if filler_count >= 3:
            score -= 3
        elif filler_count == 2:
            score -= 2
        elif filler_count == 1:
            score -= 1

        score = max(0, min(10, score))
        feedback = f"Average sentence length is {average_sentence_length:.1f} words with {filler_count} filler tokens."
        return {"score": score, "feedback": feedback}

    def _score_structure(self, transcript_text: str) -> Dict[str, Any]:
        text = transcript_text.lower()
        intro_markers = ["first", "to begin", "my point", "i believe", "in my view"]
        connector_markers = ["because", "therefore", "however", "also", "for example", "in addition"]
        conclusion_markers = ["in conclusion", "overall", "to conclude", "finally", "to sum up"]

        intro_present = any(marker in text for marker in intro_markers)
        connector_count = sum(1 for marker in connector_markers if marker in text)
        conclusion_present = any(marker in text for marker in conclusion_markers)

        score = 3
        if intro_present:
            score += 2
        score += min(3, connector_count)
        if conclusion_present:
            score += 2
        score = max(0, min(10, score))

        feedback = (
            f"Structure markers found - intro: {'yes' if intro_present else 'no'}, "
            f"connectors: {connector_count}, conclusion: {'yes' if conclusion_present else 'no'}."
        )
        return {"score": score, "feedback": feedback}

    def _score_relevance(self, transcript_tokens: List[str], topic_tokens: List[str]) -> Dict[str, Any]:
        token_set = set(transcript_tokens)
        overlap = [token for token in topic_tokens if token in token_set]
        overlap_ratio = len(overlap) / len(topic_tokens)

        if overlap_ratio >= 0.8:
            score = 10
        elif overlap_ratio >= 0.6:
            score = 8
        elif overlap_ratio >= 0.4:
            score = 6
        elif overlap_ratio >= 0.2:
            score = 4
        elif overlap_ratio > 0:
            score = 2
        else:
            score = 0

        feedback = f"Matched {len(overlap)} of {len(topic_tokens)} topic keywords: {', '.join(overlap) if overlap else 'none'}."
        return {"score": score, "feedback": feedback}

    def _score_evidence(self, transcript_text: str) -> Dict[str, Any]:
        text = transcript_text.lower()
        evidence_markers = [
            "for example",
            "for instance",
            "according to",
            "data",
            "study",
            "research",
            "statistics",
            "evidence",
            "because"
        ]
        marker_hits = sum(1 for marker in evidence_markers if marker in text)
        number_mentions = len(re.findall(r"\b\d+(\.\d+)?%?\b", text))
        total_signals = marker_hits + min(2, number_mentions)

        if total_signals >= 4:
            score = 10
        elif total_signals == 3:
            score = 8
        elif total_signals == 2:
            score = 6
        elif total_signals == 1:
            score = 4
        else:
            score = 1

        feedback = f"Evidence signals found: markers={marker_hits}, numeric references={number_mentions}."
        return {"score": score, "feedback": feedback}

    def _score_confidence(self, transcript_tokens: List[str]) -> Dict[str, Any]:
        confident_markers = {"clearly", "definitely", "certainly", "must", "will", "strongly"}
        hedge_markers = {"maybe", "perhaps", "might", "kind", "sort", "probably", "guess"}

        confidence_hits = sum(1 for token in transcript_tokens if token in confident_markers)
        hedge_hits = sum(1 for token in transcript_tokens if token in hedge_markers)

        score = 6 + min(3, confidence_hits) - min(5, hedge_hits)
        score = max(0, min(10, score))
        feedback = f"Confidence markers={confidence_hits}; hedging markers={hedge_hits}."
        return {"score": score, "feedback": feedback}

    def _score_rebuttal(self, transcript_text: str) -> Dict[str, Any]:
        text = transcript_text.lower()
        rebuttal_markers = [
            "however",
            "but",
            "although",
            "on the other hand",
            "some may argue",
            "critics say",
            "while others"
        ]
        rebuttal_hits = sum(1 for marker in rebuttal_markers if marker in text)

        if rebuttal_hits >= 3:
            score = 10
        elif rebuttal_hits == 2:
            score = 8
        elif rebuttal_hits == 1:
            score = 6
        else:
            score = 1

        feedback = (
            "Counterargument handling present."
            if rebuttal_hits
            else "No explicit rebuttal or counterargument markers detected."
        )
        return {"score": score, "feedback": feedback}
