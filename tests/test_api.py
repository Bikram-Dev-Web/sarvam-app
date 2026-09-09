"""
Integration tests for FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_reset_and_stats():
    res = client.post("/api/reset?with_seed=true")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    res_stats = client.get("/api/stats")
    assert res_stats.status_code == 200
    assert res_stats.json()["total_memories"] > 0


def test_api_process_transcript():
    payload = {
        "asr_output": "ask aditya to review the sarvam kiwi service",
        "formatted_output": "Ask Aditya to review the Sarvam Kiwi service.",
        "confidence_threshold": 0.65
    }
    res = client.post("/api/process", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["memory_aware_output"] == "Ask Aaditya to review the Sarvam Kivi service."
    assert data["interventions_count"] >= 2
    assert len(data["traces"]) > 0


def test_api_learn_observation():
    payload = {
        "source": "user_correction",
        "original_text": "Meeting with siobhan tomorrow",
        "corrected_text": "Meeting with Siobhan tomorrow"
    }
    res = client.post("/api/learn", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert res.json()["type"] == "correction_learned"
    learned = res.json()["learned"]
    assert len(learned) == 1
    assert learned[0]["original_span"] == "siobhan"
    assert learned[0]["canonical_term"] == "Siobhan"

    process_res = client.post("/api/process", json={
        "asr_output": "i have a meeting with siobhan tomorrow"
    })
    assert process_res.status_code == 200
    assert process_res.json()["memory_aware_output"] == "I have a meeting with Siobhan tomorrow."


def test_api_learn_negative_correction_reversion():
    """
    is_reversion=true is the API path for 'Kivi substituted something here and it
    was wrong' - it must go through learn_negative_correction, not
    learn_from_correction, and must not require the caller to hand-author a
    negative_contexts list.
    """
    add_res = client.post("/api/memories", json={
        "canonical_term": "Pinecone",
        "category": "product",
        "aliases": ["pine cone"],
        "context_triggers": ["vector", "database"],
        "confidence_score": 1.0
    })
    assert add_res.status_code == 200
    starting_confidence = add_res.json()["confidence_score"]

    payload = {
        "source": "negative_correction",
        "is_reversion": True,
        "original_text": "I collected a fresh Pinecone from the forest floor.",
        "corrected_text": "I collected a fresh pine cone from the forest floor."
    }
    res = client.post("/api/learn", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert body["type"] == "negative_correction_learned"
    assert len(body["penalized"]) == 1
    assert body["penalized"][0]["canonical_term"] == "Pinecone"
    assert body["penalized"][0]["new_confidence"] < starting_confidence


def test_api_learn_accepts_explicit_term_without_dummy_original_text():
    res = client.post("/api/learn", json={
        "source": "dictionary_import",
        "explicit_term": "GraphQL",
        "category": "jargon",
        "context_triggers": ["schema", "api"],
    })

    assert res.status_code == 200
    body = res.json()
    assert body["type"] == "term_created"
    assert body["memory"]["canonical_term"] == "GraphQL"


def test_api_eval():
    res = client.get("/api/eval")
    assert res.status_code == 200
    data = res.json()
    assert data["accuracy_pct"] >= 95.0
    assert data["precision_pct"] >= 95.0
