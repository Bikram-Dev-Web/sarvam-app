"""
Unit tests for TranscriptProcessor: 3-tier transformations, case preservation, and decision tracing.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models import Base, TranscriptProcessRequest
from core.transcript_processor import TranscriptProcessor, format_raw_asr, preserve_case_and_punctuation
from db.seed_data import seed_database


@pytest.fixture
def seeded_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    seed_database(session)
    yield session
    session.close()


def test_format_raw_asr():
    raw = "ask aditya to review the sarvam kiwi service"
    formatted = format_raw_asr(raw)
    assert formatted == "Ask aditya to review the sarvam kiwi service."


def test_preserve_case_and_punctuation():
    assert preserve_case_and_punctuation("aditya,", "Aaditya") == "Aaditya,"
    assert preserve_case_and_punctuation("KIWI!", "Kivi") == "KIVI!"
    assert preserve_case_and_punctuation("(kiwi)", "Kivi") == "(Kivi)"


def test_transcript_processing_intervenes(seeded_db):
    processor = TranscriptProcessor(seeded_db)
    req = TranscriptProcessRequest(
        asr_output="ask aditya to review the sarvam kiwi service",
        formatted_output="Ask Aditya to review the Sarvam Kiwi service."
    )
    res = processor.process(req)
    assert res.memory_aware_output == "Ask Aaditya to review the Sarvam Kivi service."
    assert res.interventions_count >= 2
    assert len(res.traces) > 0


def test_transcript_processing_suppresses_negative_context(seeded_db):
    processor = TranscriptProcessor(seeded_db)
    req = TranscriptProcessRequest(
        asr_output="i want to eat a fresh kiwi fruit for breakfast",
        formatted_output="I want to eat a fresh kiwi fruit for breakfast."
    )
    res = processor.process(req)
    assert res.memory_aware_output == "I want to eat a fresh kiwi fruit for breakfast."
    assert res.interventions_count == 0
    assert res.suppressed_count >= 1
    assert any(
        trace.decision == "SUPPRESSED"
        and trace.matched_memory_term == "Kivi"
        and "fruit" in trace.details["neg_matched_triggers"]
        for trace in res.traces
    )


def test_case_only_personalization_is_applied(seeded_db):
    processor = TranscriptProcessor(seeded_db)
    req = TranscriptProcessRequest(
        asr_output="we trained the model with pytorch",
        formatted_output="We trained the model with pytorch.",
    )
    res = processor.process(req)

    assert res.memory_aware_output == "We trained the model with PyTorch."
    assert any(trace.original_span == "pytorch." for trace in res.traces)


def test_span_length_is_driven_by_memory_data(seeded_db):
    from core.memory_engine import MemoryEngine

    MemoryEngine(seeded_db).create_or_update_memory(
        canonical_term="Visual Studio Code",
        category="product",
        aliases=["visual studio code"],
        context_triggers=["editor"],
        confidence_score=0.95,
    )
    processor = TranscriptProcessor(seeded_db)
    res = processor.process(TranscriptProcessRequest(
        asr_output="open visual studio code editor",
        formatted_output="Open visual studio code editor.",
    ))

    assert res.memory_aware_output == "Open Visual Studio Code editor."
    assert any(trace.start_pos == 1 and trace.end_pos == 3 for trace in res.traces)
