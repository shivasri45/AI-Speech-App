import re
from typing import Dict, Any, List

class FluencyService:
    # Optimized lookup set for single-word tokens
    SINGLE_FILLER_WORDS = {"um", "uh", "like", "actually", "basically", "so", "well"}
    
    def __init__(self):
        # Pre-compile regex for performance to strip structural punctuation efficiently
        self.punctuation_cleaner = re.compile(r"[.,\/#!$%\^&\*;:{}=\-_`~()?¿¡]")

    def clean_word(self, raw_word: str) -> str:
        """Strips structural punctuation and forces uniform lowercase."""
        if not raw_word:
            return ""
        return self.punctuation_cleaner.sub("", raw_word).lower().strip()

    def analyze_fluency(self, transcript_data: Dict[str, Any], total_duration_seconds: float) -> Dict[str, Any]:
        """
        Analyzes an ASR timeline mapping array to compute production-ready fluency scoring metrics.
        Defensively protected against division-by-zero, negative limits, and duration distortions.
        """
        words: List[Dict[str, Any]] = transcript_data.get("words", [])
        
        # Enforce defensive validation on incoming total tracking times
        if total_duration_seconds <= 0.05:
            return self._empty_fluency_result(total_duration_seconds)
            
        if not words:
            return self._empty_fluency_result(total_duration_seconds)

        word_count = len(words)
        
        # Calculate localized speech window safely bounded by absolute duration parameters
        first_word_start = max(0.0, words[0].get("start", 0.0))
        last_word_end = min(total_duration_seconds, max(first_word_start, words[-1].get("end", 0.0)))
        speech_duration_seconds = last_word_end - first_word_start

        # Calculate Words Per Minute (WPM) based on total audio session footprint
        minutes = total_duration_seconds / 60.0
        wpm = int(word_count / minutes) if minutes > 0 else 0

        # State Variables
        long_pause_count = 0
        filler_word_count = 0
        repetition_count = 0
        
        # Fixed thresholds for structural speech parsing
        LONG_PAUSE_THRESHOLD_SECS = 1.2
        
        cleaned_words_list: List[str] = []

        for i, w in enumerate(words):
            word_text = self.clean_word(w.get("word", ""))
            cleaned_words_list.append(word_text)
            
            start = max(0.0, w.get("start", 0.0))
            end = min(total_duration_seconds, max(start, w.get("end", 0.0)))

            # 1. Structural Inter-Word Pause Verification
            if i > 0:
                prev_end = min(total_duration_seconds, max(0.0, words[i-1].get("end", 0.0)))
                inter_word_gap = start - prev_end
                if inter_word_gap >= LONG_PAUSE_THRESHOLD_SECS:
                    long_pause_count += 1

            # 2. Single Word Filler Matching
            if word_text in self.SINGLE_FILLER_WORDS:
                filler_word_count += 1

            # 3. Double-Word Token Repetition Matching (e.g., "the the", "design design")
            if i > 0 and word_text:
                prev_word_cleaned = cleaned_words_list[i-1]
                if word_text == prev_word_cleaned:
                    repetition_count += 1

        # 4. Sequential Scan for Multi-Word Phrase Fillers ("you know")
        full_cleaned_transcript = " ".join(cleaned_words_list)
        # Scan for structural occurrences of "you know"
        multi_word_fillers = len(re_findall := re.findall(r"\byou know\b", full_cleaned_transcript))
        filler_word_count += multi_word_fillers

        # 5. Safe Silence Calculation Bound
        total_silence_seconds = max(0.0, total_duration_seconds - speech_duration_seconds)
        silence_ratio = min(1.0, total_silence_seconds / total_duration_seconds)

        # 6. Normalized Production Grading Equation (Metrics scaled per minute of talk time)
        # Prevents long audio samples from dropping to zero automatically
        normalized_minutes = max(0.1, total_duration_seconds / 60.0)
        
        pauses_per_minute = long_pause_count / normalized_minutes
        fillers_per_minute = filler_word_count / normalized_minutes
        repetitions_per_minute = repetition_count / normalized_minutes

        score = 100.0
        score -= (pauses_per_minute * 4.0)       # Deductions scaled dynamically per minute
        score -= (fillers_per_minute * 3.0)
        score -= (repetitions_per_minute * 5.0)

        # Apply target pacing window constraints (Ideal: 120 - 160 WPM)
        if wpm < 110:
            score -= min(25.0, (110 - wpm) * 0.5)
        elif wpm > 170:
            score -= min(25.0, (wpm - 170) * 0.5)

        # Safety boundary floor and ceiling clamps
        final_score = max(0, min(100, int(round(score))))

        return {
            "words_per_minute": wpm,
            "speech_duration_seconds": round(speech_duration_seconds, 2),
            "total_duration_seconds": round(total_duration_seconds, 2),
            "silence_ratio": round(silence_ratio, 2),
            "long_pause_count": long_pause_count,
            "filler_word_count": filler_word_count,
            "repetition_count": repetition_count,
            "score": final_score
        }

    def _empty_fluency_result(self, total_duration_seconds: float) -> Dict[str, Any]:
        """Returns safe default fallback structure on empty or corrupted audio pipelines."""
        return {
            "words_per_minute": 0,
            "speech_duration_seconds": 0.0,
            "total_duration_seconds": round(max(0.0, total_duration_seconds), 2),
            "silence_ratio": 1.0,
            "long_pause_count": 0,
            "filler_word_count": 0,
            "repetition_count": 0,
            "score": 0
        }