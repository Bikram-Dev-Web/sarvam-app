"""
Unit tests for MemoryEngine: learning from user corrections, reinforcement, context scoring, negative suppressions.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models import Base, DBMemory
from core.memory_engine import (
    MemoryEngine,
    compute_composite_score,
    MIN_ACTIVE_CONFIDENCE,
    NEGATIVE_EVIDENCE_PENALTY,
)


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_and_reinforce_memory(in_memory_db):
    engine = MemoryEngine(in_memory_db)
    mem1 = engine.create_or_update_memory(
        canonical_term="Aaditya",
        category="person",
        aliases=["Aditya"],
        context_triggers=["sarvam", "review"],
        confidence_score=0.85
    )
    assert mem1.id is not None
    assert mem1.reinforcement_count == 1
    assert mem1.confidence_score == 0.85

    # Reinforce
    mem2 = engine.create_or_update_memory(
        canonical_term="Aaditya",
        aliases=["Adithya"],
        context_triggers=["service"]
    )
    assert mem2.id == mem1.id
    assert mem2.reinforcement_count == 2
    assert mem2.confidence_score > 0.85


def test_learn_from_user_correction(in_memory_db):
    engine = MemoryEngine(in_memory_db)
    learned = engine.learn_from_correction(
        original_text="Ask Aditya to review the Sarvam Kiwi service.",
        corrected_text="Ask Aaditya to review the Sarvam Kivi service."
    )
    assert len(learned) == 2
    terms = [l["canonical_term"] for l in learned]
    assert "Aaditya" in terms
    assert "Kivi" in terms


def test_learn_from_case_only_correction(in_memory_db):
    """Preferred capitalization is part of the canonical personal term."""
    engine = MemoryEngine(in_memory_db)
    learned = engine.learn_from_correction(
        original_text="Meeting with siobhan tomorrow at ten",
        corrected_text="Meeting with Siobhan tomorrow at ten",
    )

    assert len(learned) == 1
    assert learned[0]["original_span"] == "siobhan"
    assert learned[0]["canonical_term"] == "Siobhan"
    assert "meeting" in learned[0]["context_triggers"]


def test_context_affinity_and_negative_suppression(in_memory_db):
    engine = MemoryEngine(in_memory_db)
    mem = engine.create_or_update_memory(
        canonical_term="Kivi",
        context_triggers=["sarvam", "service"],
        negative_contexts=["fruit", "eat"]
    )

    # Positive context match
    affinity_pos, pos_m, neg_m = engine.compute_context_affinity(mem, ["sarvam", "service", "review"])
    assert affinity_pos > 0.5
    assert "sarvam" in pos_m
    assert len(neg_m) == 0

    # Negative context match (fruit)
    affinity_neg, pos_m, neg_m = engine.compute_context_affinity(mem, ["fresh", "kiwi", "fruit", "eat"])
    assert affinity_neg == -1.0
    assert "fruit" in neg_m


def test_multi_word_context_triggers_are_matched(in_memory_db):
    engine = MemoryEngine(in_memory_db)
    mem = engine.create_or_update_memory(
        canonical_term="Kivi",
        context_triggers=["speech product"],
        negative_contexts=["new zealand"],
    )

    affinity_pos, pos_m, _ = engine.compute_context_affinity(
        mem, ["our", "speech", "product", "works"]
    )
    assert affinity_pos == 1.0
    assert pos_m == ["speech product"]

    affinity_neg, _, neg_m = engine.compute_context_affinity(
        mem, ["native", "new", "zealand", "bird"]
    )
    assert affinity_neg == -1.0
    assert neg_m == ["new zealand"]


def test_learn_from_correction_excludes_own_span_words_from_context(in_memory_db):
    """
    Regression test for a bug found while building the holdout suite: a multi-word
    entity's own words (e.g. "pie", "torch" from "pie torch" -> "PyTorch") must not
    leak into its own trigger list, or a sentence that is genuinely about that same
    literal wording (baking a pie) would satisfy the positive trigger it's supposed
    to be distinguished from.
    """
    engine = MemoryEngine(in_memory_db)
    learned = engine.learn_from_correction(
        original_text="we trained our model using pie torch on the cluster",
        corrected_text="We trained our model using PyTorch on the cluster."
    )
    assert len(learned) == 1
    triggers = learned[0]["context_triggers"]
    assert "pie" not in [t.lower() for t in triggers]
    assert "torch" not in [t.lower() for t in triggers]
    assert "pytorch" not in [t.lower() for t in triggers]
    assert "cluster" in triggers


def test_compute_composite_score_veto_and_weights():
    # Negative context is an absolute veto regardless of weighting.
    composite, kind = compute_composite_score(0.99, -1.0, 0.99)
    assert composite == 0.0
    assert kind == "vetoed_by_negative_context"

    # Weighted composite matches the documented formula.
    composite, kind = compute_composite_score(0.8, 0.5, 0.9, weights=(0.5, 0.3, 0.2))
    assert kind == "weighted_composite"
    assert composite == round(0.5 * 0.8 + 0.3 * 0.5 + 0.2 * 0.9, 4)

    # Result is always clamped to [0, 1].
    composite, _ = compute_composite_score(1.0, 1.0, 1.0, weights=(0.9, 0.9, 0.9))
    assert composite == 1.0


def test_find_best_candidate_accepts_precomputed_memories(in_memory_db):
    """
    TranscriptProcessor fetches the active memory set once per transcript and passes
    it in, instead of find_best_candidate re-querying the database per span. Both
    call styles must produce identical decisions.
    """
    engine = MemoryEngine(in_memory_db)
    engine.create_or_update_memory(
        canonical_term="Aaditya", aliases=["Aditya"],
        context_triggers=["sarvam", "review"], confidence_score=0.9
    )
    context = ["sarvam", "review"]

    fetched_internally = engine.find_best_candidate("aditya", context)
    memories = engine.get_all_memories(active_only=True)
    passed_in = engine.find_best_candidate("aditya", context, memories=memories)

    assert fetched_internally is not None and passed_in is not None
    mem_a, score_a, details_a = fetched_internally
    mem_b, score_b, details_b = passed_in
    assert mem_a.id == mem_b.id
    assert score_a == score_b


def test_learn_negative_correction_teaches_scoped_suppression(in_memory_db):
    """
    A memory that over-triggers in an unintended context should, after the user
    reverts it, stay silent in similar unrelated contexts WITHOUT losing its ability
    to fire correctly in the context it was actually meant for.
    """
    engine = MemoryEngine(in_memory_db)
    mem = engine.create_or_update_memory(
        canonical_term="Pinecone", category="product",
        aliases=["pine cone"],
        context_triggers=["vector", "embeddings", "database"],
        confidence_score=1.0
    )
    starting_confidence = mem.confidence_score

    penalized = engine.learn_negative_correction(
        memory_aware_text="I collected a fresh Pinecone from the forest floor.",
        user_reverted_text="I collected a fresh pine cone from the forest floor."
    )
    assert len(penalized) == 1
    entry = penalized[0]
    assert entry["canonical_term"] == "Pinecone"
    assert abs(entry["new_confidence"] - (starting_confidence - NEGATIVE_EVIDENCE_PENALTY)) < 1e-6
    # The entity's own words must not have been added as negative context (see the
    # span-exclusion regression test above) - only the surrounding words should be.
    assert "pine" not in entry["added_negative_contexts"]
    assert "cone" not in entry["added_negative_contexts"]
    assert "forest" in entry["added_negative_contexts"]

    refreshed = engine.get_memory_by_id(mem.id)
    affinity, _, neg_matched = engine.compute_context_affinity(refreshed, ["forest", "floor"])
    assert affinity == -1.0
    assert "forest" in neg_matched

    # The legitimate context must be unaffected.
    affinity_legit, pos_matched, neg_matched_legit = engine.compute_context_affinity(
        refreshed, ["vector", "database"]
    )
    assert affinity_legit > 0
    assert len(neg_matched_legit) == 0


def test_learn_negative_correction_never_negates_its_own_positive_triggers(in_memory_db):
    """
    A revert whose sentence legitimately contains the memory's OWN trigger words
    must not turn those triggers into negative contexts.

    Found by a large-scale benchmark run: because a matched negative context is an
    absolute veto, recording a trigger as a negative silences the memory in exactly
    the context it was taught for, so a single revert would permanently disable the
    entity. Only the words that actually distinguish the wrong context may be
    learned.
    """
    engine = MemoryEngine(in_memory_db)
    mem = engine.create_or_update_memory(
        canonical_term="Temporal", category="jargon",
        aliases=["temporel"],
        context_triggers=["workflow", "worker", "retry", "deep learning"],
        confidence_score=0.9
    )

    # The user reverts a wrong substitution in a sentence that is still genuinely
    # about workflows, workers and retries.
    penalized = engine.learn_negative_correction(
        memory_aware_text="The Temporal worker will retry the workflow job tonight.",
        user_reverted_text="The temporary worker will retry the workflow job tonight."
    )
    assert len(penalized) == 1
    added = penalized[0]["added_negative_contexts"]

    # Its own triggers must survive as triggers, not become vetoes.
    for trigger in ("workflow", "worker", "retry"):
        assert trigger not in added
    # Component words of a phrase trigger are protected too.
    assert "deep" not in added and "learning" not in added
    # The genuinely distinguishing word is still learned.
    assert "tonight" in added

    refreshed = engine.get_memory_by_id(mem.id)
    # The context it was taught for must still fire.
    affinity, pos_matched, neg_matched = engine.compute_context_affinity(
        refreshed, ["workflow", "worker", "retry"]
    )
    assert affinity > 0
    assert neg_matched == []
    # The context it was reverted in must still be suppressed.
    veto_affinity, _, veto_matched = engine.compute_context_affinity(refreshed, ["tonight"])
    assert veto_affinity == -1.0
    assert "tonight" in veto_matched


def test_learn_negative_correction_deactivates_after_repeated_false_positives(in_memory_db):
    """A memory that keeps being wrong should eventually be soft-removed (is_active
    set to False), not deleted, and not left active indefinitely."""
    engine = MemoryEngine(in_memory_db)
    mem = engine.create_or_update_memory(
        canonical_term="Testly", confidence_score=0.4, context_triggers=["alpha"]
    )
    # Repeatedly revert a wrong substitution until confidence crosses below
    # MIN_ACTIVE_CONFIDENCE. Each call must find a genuine word-level difference
    # that resolves back to the same memory (the wrong word is the exact
    # canonical term each time).
    wrong = "This is a Testly result."
    right = "This is a test result."
    for _ in range(4):
        engine.learn_negative_correction(memory_aware_text=wrong, user_reverted_text=right)

    refreshed = engine.get_memory_by_id(mem.id)
    assert refreshed.confidence_score < MIN_ACTIVE_CONFIDENCE
    assert refreshed.is_active is False
    # Soft-removed, not deleted: it's still inspectable.
    assert engine.get_memory_by_id(mem.id) is not None
    # And it no longer shows up as a candidate for active lookups.
    assert refreshed not in engine.get_all_memories(active_only=True)
