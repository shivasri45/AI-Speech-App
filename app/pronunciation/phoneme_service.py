from functools import lru_cache
from pathlib import Path

from app.pronunciation.transcript_cleaner import normalize_transcript


DICTIONARY_PATH = Path("mfa_models/dictionary/cmudict.dict")

FALLBACK_PHONEMES = {
    "subtle": ["S", "AH", "T", "AH", "L"],
    "debt": ["D", "EH", "T"],
    "doubt": ["D", "AW", "T"],
    "receipt": ["R", "IH", "S", "IY", "T"],
    "island": ["AY", "L", "AH", "N", "D"],
    "honest": ["AA", "N", "AH", "S", "T"],
    "hour": ["AW", "ER"],
    "could": ["K", "UH", "D"],
    "would": ["W", "UH", "D"],
    "should": ["SH", "UH", "D"],
    "colonel": ["K", "ER", "N", "AH", "L"],
    "choir": ["K", "W", "AY", "ER"],
    "chaos": ["K", "EY", "AA", "S"],
    "schedule": ["S", "K", "EH", "JH", "UW", "L"],
    "specific": ["S", "P", "AH", "S", "IH", "F", "IH", "K"],
    "probably": ["P", "R", "AA", "B", "AH", "B", "L", "IY"],
    "comfortable": ["K", "AH", "M", "F", "T", "ER", "B", "AH", "L"],
    "vegetable": ["V", "EH", "JH", "T", "AH", "B", "AH", "L"],
    "develop": ["D", "IH", "V", "EH", "L", "AH", "P"],
    "analysis": ["AH", "N", "AE", "L", "AH", "S", "AH", "S"],
    "entrepreneur": ["AA", "N", "T", "R", "AH", "P", "R", "AH", "N", "ER"],
    "rural": ["R", "UH", "R", "AH", "L"],
    "thorough": ["TH", "ER", "OW"],
    "although": ["AO", "L", "DH", "OW"],
    "thought": ["TH", "AO", "T"],
    "through": ["TH", "R", "UW"],
    "throughout": ["TH", "R", "UW", "AW", "T"],
    "world": ["W", "ER", "L", "D"],
    "asked": ["AE", "S", "K", "T"],
    "strength": ["S", "T", "R", "EH", "NG", "K", "TH"],
}


def strip_stress(phoneme: str):
    return "".join(character for character in phoneme if not character.isdigit())


@lru_cache(maxsize=1)
def load_cmudict():
    entries = {}

    if not DICTIONARY_PATH.exists():
        return entries

    with open(DICTIONARY_PATH, "r", encoding="utf-8", errors="ignore") as dictionary:
        for line in dictionary:
            line = line.strip()

            if not line or line.startswith((";", "#")):
                continue

            parts = line.split()

            if len(parts) < 2:
                continue

            word = parts[0].lower()
            word = word.split("(")[0]
            phonemes = [strip_stress(phoneme) for phoneme in parts[1:]]

            entries.setdefault(word, phonemes)

    return entries


def get_word_phonemes(word: str):
    normalized_word = normalize_transcript(word)

    if not normalized_word:
        return []

    dictionary = load_cmudict()

    if normalized_word in dictionary:
        return dictionary[normalized_word]

    return FALLBACK_PHONEMES.get(normalized_word, [])


def get_expected_word_phonemes(expected_text: str):
    phoneme_words = []

    for word in normalize_transcript(expected_text).split():
        phonemes = get_word_phonemes(word)

        phoneme_words.append({
            "word": word,
            "phonemes": phonemes
        })

    return phoneme_words
