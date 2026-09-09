"""
Phonetic similarity and encoding engine for Kivi's Word-Level Memory System.
Handles Latin-script Indian-English and domain-specific phonetic variations.
"""

import re
import jellyfish
from typing import Tuple, List, Dict, Any, Optional


def normalize_indian_phonetics(word: str) -> str:
    """
    Normalizes common Indian-English transliteration variants:
    - 'aa' -> 'a', 'ee' -> 'i', 'oo' -> 'u'
    - 'w' -> 'v', 'ph' -> 'f'
    - Aspirated consonant reduction for similarity checks: 'dh'->'d', 'th'->'t', 'bh'->'b', 'kh'->'k', 'gh'->'g'
    - Repeated consonants reduction: 'tt' -> 't', 'dd' -> 'd', etc.
    """
    w = word.lower().strip()
    w = re.sub(r'[^a-z0-9]', '', w)
    
    # Common vowel variants
    w = re.sub(r'aa+', 'a', w)
    w = re.sub(r'ee+', 'i', w)
    w = re.sub(r'oo+', 'u', w)
    w = re.sub(r'ou', 'au', w)
    
    # Consonant variants common in Indian phonetics & speech ASR confusion
    w = re.sub(r'w', 'v', w)
    w = re.sub(r'ph', 'f', w)
    w = re.sub(r'dh', 'd', w)
    w = re.sub(r'th', 't', w)
    w = re.sub(r'bh', 'b', w)
    w = re.sub(r'kh', 'k', w)
    w = re.sub(r'gh', 'g', w)
    w = re.sub(r'sh', 's', w)
    w = re.sub(r'zh', 'z', w)
    
    # Collapse consecutive duplicate letters
    w = re.sub(r'(.)\1+', r'\1', w)
    return w


def get_phonetic_keys(term: str) -> Dict[str, Any]:
    """
    Computes multiple phonetic and normalized representations for a term or phrase.
    """
    clean_term = term.strip()
    words = clean_term.split()
    
    metaphone_primary = []
    metaphone_secondary = []
    soundex_keys = []
    normalized_keys = []
    
    for w in words:
        clean_w = re.sub(r'[^a-zA-Z0-9]', '', w)
        if not clean_w:
            continue
        try:
            metaphone = jellyfish.metaphone(clean_w)
            metaphone_primary.append(metaphone or clean_w)
        except Exception:
            metaphone_primary.append(clean_w)
            
        try:
            sndx = jellyfish.soundex(clean_w)
            soundex_keys.append(sndx)
        except Exception:
            soundex_keys.append("")
            
        normalized_keys.append(normalize_indian_phonetics(clean_w))
        
    return {
        "raw": clean_term.lower(),
        "metaphone": " ".join(metaphone_primary),
        "soundex": " ".join(soundex_keys),
        "normalized": " ".join(normalized_keys),
    }


def compute_phonetic_similarity(target: str, candidate: str) -> Tuple[float, Dict[str, Any]]:
    """
    Computes a composite phonetic and string similarity score between target (from memory)
    and candidate (from ASR/formatted text).
    
    Score ranges from 0.0 (completely dissimilar) to 1.0 (exact phonetic/orthographic match).
    """
    target_clean = target.strip().lower()
    candidate_clean = candidate.strip().lower()
    
    if target_clean == candidate_clean:
        return 1.0, {"exact_match": True, "score": 1.0}
        
    t_keys = get_phonetic_keys(target_clean)
    c_keys = get_phonetic_keys(candidate_clean)
    
    # 1. Metaphone similarity (Jaro-Winkler on metaphone strings)
    meta_sim = jellyfish.jaro_winkler_similarity(t_keys["metaphone"], c_keys["metaphone"])
    
    # 2. Soundex match
    soundex_match = 1.0 if t_keys["soundex"] and t_keys["soundex"] == c_keys["soundex"] else 0.0
    
    # 3. Normalized Indian-English phonetic string distance (normalized Levenshtein)
    norm_t = t_keys["normalized"]
    norm_c = c_keys["normalized"]
    max_len = max(len(norm_t), len(norm_c), 1)
    norm_lev_dist = jellyfish.levenshtein_distance(norm_t, norm_c)
    norm_sim = 1.0 - (norm_lev_dist / max_len)
    
    # 4. Raw Jaro-Winkler distance
    jw_sim = jellyfish.jaro_winkler_similarity(target_clean, candidate_clean)
    
    # 5. Raw Normalized Levenshtein
    raw_max_len = max(len(target_clean), len(candidate_clean), 1)
    raw_lev = jellyfish.levenshtein_distance(target_clean, candidate_clean)
    raw_lev_sim = 1.0 - (raw_lev / raw_max_len)
    
    # Weighted composite score
    # We favor normalized phonetic + metaphone heavily, with soundex and raw string as reinforcement
    score = (
        0.35 * norm_sim +
        0.30 * meta_sim +
        0.15 * soundex_match +
        0.10 * jw_sim +
        0.10 * raw_lev_sim
    )
    
    score = max(0.0, min(1.0, score))
    
    details = {
        "metaphone_sim": round(meta_sim, 3),
        "soundex_match": soundex_match == 1.0,
        "norm_phonetic_sim": round(norm_sim, 3),
        "jaro_winkler": round(jw_sim, 3),
        "raw_lev_sim": round(raw_lev_sim, 3),
        "target_phonetics": t_keys,
        "candidate_phonetics": c_keys,
        "composite_score": round(score, 4)
    }
    
    return round(score, 4), details
