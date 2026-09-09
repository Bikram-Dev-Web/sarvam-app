"""
Unit tests for phonetic normalization and composite similarity scoring.
"""

import pytest
from core.phonetics import (
    normalize_indian_phonetics,
    get_phonetic_keys,
    compute_phonetic_similarity
)


def test_normalize_indian_phonetics():
    assert normalize_indian_phonetics("Aaditya") == "aditya"
    assert normalize_indian_phonetics("Deeksha") == "diksa"
    assert normalize_indian_phonetics("Diksha") == "diksa"
    assert normalize_indian_phonetics("Kiwi") == "kivi"
    assert normalize_indian_phonetics("Kivi") == "kivi"


def test_get_phonetic_keys():
    keys = get_phonetic_keys("Aaditya")
    assert "metaphone" in keys
    assert "soundex" in keys
    assert "normalized" in keys
    assert keys["normalized"] == "aditya"


def test_phonetic_similarity_high_for_variants():
    sim_aaditya, _ = compute_phonetic_similarity("Aaditya", "Aditya")
    assert sim_aaditya >= 0.85

    sim_kivi, _ = compute_phonetic_similarity("Kivi", "Kiwi")
    assert sim_kivi >= 0.70

    sim_deeksha, _ = compute_phonetic_similarity("Deeksha", "Diksha")
    assert sim_deeksha >= 0.90


def test_phonetic_similarity_low_for_unrelated():
    sim_unrelated, _ = compute_phonetic_similarity("Aaditya", "Pineapple")
    assert sim_unrelated < 0.40
