import math
import re
from typing import Dict, Any, List, Optional

class FluencyService:
    # Common filler words
    FILLER_WORDS = {"um", "uh", "like", "you know", "actually", "basically", "so", "well"}
    LONG_PAUSE_THRESHOLD_SECONDS = 1.0

    def __init__(self):
        pass

    def analyze_fluency(self, transcript_data: Dict[str, Any], total_duration_seconds: float) -> Dict[str, Any]:
        """
        Analyzes a Whisper-style transcript with word timestamps and calculates fluency metrics.
        """
        safe_total_duration = self._to_non_negative_float(total_duration_seconds)
        words = self._normalize_words(transcript_data)

        if not words:
            return self._empty_fluency_result(safe_total_duration)

        word_count = len(words)
        speech_duration_seconds = self._compute_speech_duration(words)
        duration_basis = safe_total_duration if safe_total_duration > 0 else speech_duration_seconds

        # Calculate WPM
        minutes = duration_basis / 60.0
        wpm = int(word_count / minutes) if minutes > 0 else 0

        # Pauses & Silence
        long_pause_count = 0
        filler_word_count = 0
        repetition_count = 0
        previous_word_text = ""
        previous_end: Optional[float] = None

        for i, w in enumerate(words):
            word_text = w.get("word", "")
            start = w.get("start")
            end = w.get("end")

            # Check pause
            if i > 0 and previous_end is not None and start is not None:
                pause = start - previous_end
                if pause > self.LONG_PAUSE_THRESHOLD_SECONDS:
                    long_pause_count += 1

            # Check filler
            if word_text in self.FILLER_WORDS:
                filler_word_count += 1

            # Check repetition
            if i > 0 and word_text and word_text == previous_word_text:
                repetition_count += 1

            previous_word_text = word_text
            previous_end = end if end is not None else previous_end

        if duration_basis > 0:
            raw_silence_ratio = (duration_basis - speech_duration_seconds) / duration_basis
            silence_ratio = max(0.0, min(1.0, raw_silence_ratio))
        else:
            silence_ratio = 0.0

        # Basic score heuristic (out of 100)
        score = 100
        score -= (long_pause_count * 5)
        score -= (filler_word_count * 2)
        score -= (repetition_count * 3)
        # Penalize too fast or too slow (ideal 130-160 WPM)
        if wpm < 110:
            score -= min(20, (110 - wpm))
        elif wpm > 180:
            score -= min(20, (wpm - 180))
            
        score = max(0, min(100, int(score)))

        return {
            "words_per_minute": wpm,
            "speech_duration_seconds": round(speech_duration_seconds, 2),
            "total_duration_seconds": round(duration_basis, 2),
            "silence_ratio": round(silence_ratio, 2),
            "long_pause_count": long_pause_count,
            "filler_word_count": filler_word_count,
            "repetition_count": repetition_count,
            "score": score
        }

    def _empty_fluency_result(self, total_duration_seconds: float) -> Dict[str, Any]:
        silence_ratio = 1.0 if total_duration_seconds > 0 else 0.0
        return {
            "words_per_minute": 0,
            "speech_duration_seconds": 0.0,
            "total_duration_seconds": round(total_duration_seconds, 2),
            "silence_ratio": silence_ratio,
            "long_pause_count": 0,
            "filler_word_count": 0,
            "repetition_count": 0,
            "score": 0
        }

    def _normalize_words(self, transcript_data: Dict[str, Any]) -> List[Dict[str, Optional[float]]]:
        if not isinstance(transcript_data, dict):
            return []

        raw_words = transcript_data.get("words", [])
        if not isinstance(raw_words, list):
            return []

        normalized_words: List[Dict[str, Optional[float]]] = []
        for raw_word in raw_words:
            if not isinstance(raw_word, dict):
                continue

            normalized_text = self._normalize_word(raw_word.get("word"))
            if not normalized_text:
                continue

            start = self._to_non_negative_float(raw_word.get("start"), default=None)
            end = self._to_non_negative_float(raw_word.get("end"), default=None)

            if start is not None and end is not None and end < start:
                start, end = end, start

            normalized_words.append({
                "word": normalized_text,
                "start": start,
                "end": end
            })

        return normalized_words

    def _compute_speech_duration(self, words: List[Dict[str, Optional[float]]]) -> float:
        starts = [w["start"] for w in words if w.get("start") is not None]
        ends = [w["end"] for w in words if w.get("end") is not None]

        if not starts or not ends:
            return 0.0

        duration = max(ends) - min(starts)
        return max(0.0, round(duration, 4))

    def _normalize_word(self, value: Any) -> str:
        if value is None:
            return ""

        text = str(value).lower().strip()
        if not text:
            return ""

        return re.sub(r"[^\w\s']", "", text).strip()

    def _to_non_negative_float(self, value: Any, default: Optional[float] = 0.0) -> Optional[float]:
        if value is None:
            return default

        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return default

        if not math.isfinite(numeric):
            return default

        return max(0.0, numeric)
