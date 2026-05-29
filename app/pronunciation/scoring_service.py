from difflib import SequenceMatcher

from app.pronunciation.transcript_cleaner import normalize_transcript


SPECIAL_FEEDBACK = {
    "subtle": "The word 'subtle' is often pronounced like 'suh-tl'; the b is silent.",
    "debt": "The b is silent in 'debt'. Say it like 'det'.",
    "doubt": "The b is silent in 'doubt'. Say it like 'dowt'.",
    "receipt": "The p is silent in 'receipt'. Keep the middle sound clean.",
    "island": "The s is silent in 'island'. Say it like 'eye-land'.",
    "honest": "The h is silent in 'honest'. Start with the vowel sound.",
    "hour": "The h is silent in 'hour'. Start with the vowel sound.",
    "could": "The l is silent in 'could'.",
    "would": "The l is silent in 'would'.",
    "should": "The l is silent in 'should'."
}


def calculate_clarity_score(words):
    if not words:
        return 0

    average_probability = sum(
        word.probability for word in words
    ) / len(words)

    return round(average_probability * 100, 2)


def calculate_pace_wpm(words):
    if not words:
        return 0

    start = min(word.start for word in words)
    end = max(word.end for word in words)
    duration_minutes = (end - start) / 60

    if duration_minutes <= 0:
        return 0

    return round(len(words) / duration_minutes, 2)


def build_feedback(expected_word, heard_word):
    special_feedback = SPECIAL_FEEDBACK.get(expected_word)

    if special_feedback:
        return special_feedback

    if heard_word:
        return (
            f"Expected '{expected_word}', but heard '{heard_word}'. "
            "Practice this word slowly and clearly."
        )

    return f"The word '{expected_word}' was missing or unclear."


def compare_expected_to_transcript(expected_text, transcript):
    expected_words = normalize_transcript(expected_text).split()
    heard_words = normalize_transcript(transcript).split()

    if not expected_words:
        return None, []

    matcher = SequenceMatcher(
        None,
        expected_words,
        heard_words
    )

    mistakes = []
    matched_words = 0

    for tag, expected_start, expected_end, heard_start, heard_end in matcher.get_opcodes():
        expected_chunk = expected_words[expected_start:expected_end]
        heard_chunk = heard_words[heard_start:heard_end]

        if tag == "equal":
            matched_words += len(expected_chunk)
            continue

        chunk_size = max(
            len(expected_chunk),
            len(heard_chunk)
        )

        for index in range(chunk_size):
            expected_word = (
                expected_chunk[index]
                if index < len(expected_chunk)
                else ""
            )
            heard_word = (
                heard_chunk[index]
                if index < len(heard_chunk)
                else ""
            )

            if not expected_word:
                continue

            mistakes.append({
                "expected_word": expected_word,
                "heard_word": heard_word or None,
                "feedback": build_feedback(
                    expected_word,
                    heard_word
                )
            })

    score = round(
        (matched_words / len(expected_words)) * 100,
        2
    )

    return score, mistakes


def get_heard_word_for_expected(expected_word, heard_words):
    normalized_expected = normalize_transcript(expected_word)

    if normalized_expected in heard_words:
        return normalized_expected

    matcher = SequenceMatcher(
        None,
        [normalized_expected],
        heard_words
    )

    for tag, _expected_start, _expected_end, heard_start, heard_end in matcher.get_opcodes():
        if tag == "replace" and heard_start < heard_end:
            return heard_words[heard_start]

    return None


def find_word_probability(expected_word, words):
    normalized_expected = normalize_transcript(expected_word)

    for word in words:
        if normalize_transcript(word.word) == normalized_expected:
            return word.probability

    return 0


def build_word_scores(expected_text, transcript, words, phoneme_words, mfa_available):
    heard_words = normalize_transcript(transcript).split()
    word_scores = []

    for phoneme_word in phoneme_words:
        expected_word = phoneme_word["word"]
        heard_word = get_heard_word_for_expected(expected_word, heard_words)
        word_probability = find_word_probability(expected_word, words)
        word_matches = expected_word == heard_word

        word_match_score = 100 if word_matches else 0
        confidence_score = round(word_probability * 100, 2)
        phoneme_score = 80 if mfa_available and phoneme_word["phonemes"] else None

        if phoneme_score is None:
            score = round((word_match_score * 0.7) + (confidence_score * 0.3), 2)
        else:
            score = round(
                (word_match_score * 0.45) +
                (confidence_score * 0.25) +
                (phoneme_score * 0.30),
                2
            )

        feedback = "Good match."

        if not word_matches:
            feedback = build_feedback(expected_word, heard_word)
        elif expected_word in SPECIAL_FEEDBACK:
            feedback = SPECIAL_FEEDBACK[expected_word]
        elif not mfa_available:
            feedback = "Word matched. Phoneme alignment is not available yet."

        word_scores.append({
            "word": expected_word,
            "heard_word": heard_word,
            "score": score,
            "word_match_score": word_match_score,
            "confidence_score": confidence_score,
            "phoneme_score": phoneme_score,
            "expected_phonemes": phoneme_word["phonemes"],
            "feedback": feedback
        })

    return word_scores


def calculate_pronunciation_score(word_match_score, word_scores):
    if not word_scores:
        return word_match_score

    return round(
        sum(word_score["score"] for word_score in word_scores) / len(word_scores),
        2
    )
