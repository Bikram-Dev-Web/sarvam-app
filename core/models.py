"""
Data models and Database Schemas for Kivi's Word-Level Memory System.
Supports both SQLAlchemy ORM for durable persistence and Pydantic schemas for API/validation.
"""

from datetime import datetime, timezone
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ==========================================
# SQLAlchemy Database Models
# ==========================================

class DBMemory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    canonical_term = Column(String(255), unique=True, index=True, nullable=False)
    category = Column(String(64), default="general", index=True)  # person, org, product, acronym, jargon, general
    phonetic_code = Column(String(255), index=True, nullable=False)
    normalized_phonetic = Column(String(255), index=True, nullable=False)
    soundex_code = Column(String(64), nullable=True)
    aliases_json = Column(Text, default="[]")  # JSON list of known variations/misrecognitions
    confidence_score = Column(Float, default=0.85)  # 0.0 to 1.0
    reinforcement_count = Column(Integer, default=1)
    last_reinforced_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_type = Column(String(64), default="manual_dictionary")  # explicit_correction, manual_dictionary, repeated_usage, corpus_import
    context_triggers_json = Column(Text, default="[]")  # JSON list of context keywords
    negative_contexts_json = Column(Text, default="[]")  # JSON list of words where memory should NOT trigger
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    evidence_logs = relationship("DBEvidenceLog", back_populates="memory", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "canonical_term": self.canonical_term,
            "category": self.category,
            "phonetic_code": self.phonetic_code,
            "normalized_phonetic": self.normalized_phonetic,
            "soundex_code": self.soundex_code,
            "aliases": json.loads(self.aliases_json) if self.aliases_json else [],
            "confidence_score": round(self.confidence_score, 3),
            "reinforcement_count": self.reinforcement_count,
            "last_reinforced_at": self.last_reinforced_at.isoformat() if self.last_reinforced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "source_type": self.source_type,
            "context_triggers": json.loads(self.context_triggers_json) if self.context_triggers_json else [],
            "negative_contexts": json.loads(self.negative_contexts_json) if self.negative_contexts_json else [],
            "is_active": self.is_active,
            "notes": self.notes
        }


class DBEvidenceLog(Base):
    __tablename__ = "evidence_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    memory_id = Column(Integer, ForeignKey("memories.id", ondelete="CASCADE"), nullable=True)
    source = Column(String(64), default="user_correction")  # user_correction, audio_session, dictionary_import
    original_text = Column(Text, nullable=False)
    corrected_text = Column(Text, nullable=True)
    delta_terms_json = Column(Text, default="{}")  # {"Kiwi": "Kivi", "Aditya": "Aaditya"}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    memory = relationship("DBMemory", back_populates="evidence_logs")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory_id": self.memory_id,
            "source": self.source,
            "original_text": self.original_text,
            "corrected_text": self.corrected_text,
            "delta_terms": json.loads(self.delta_terms_json) if self.delta_terms_json else {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class DBEvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_cases = Column(Integer, default=0)
    passed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    precision = Column(Float, default=0.0)
    recall = Column(Float, default=0.0)
    false_intervention_rate = Column(Float, default=0.0)
    avg_latency_ms = Column(Float, default=0.0)
    results_json = Column(Text, default="{}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "accuracy": round(self.accuracy, 3),
            "precision": round(self.precision, 3),
            "recall": round(self.recall, 3),
            "false_intervention_rate": round(self.false_intervention_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "results": json.loads(self.results_json) if self.results_json else {}
        }


# ==========================================
# Pydantic Schemas for API & Validation
# ==========================================

class MemoryCreate(BaseModel):
    canonical_term: str = Field(..., description="The preferred ground truth term e.g. 'Aaditya', 'Kivi'")
    category: str = Field(default="general", description="person | org | product | acronym | jargon | general")
    aliases: List[str] = Field(default_factory=list, description="Common misspellings or ASR outputs e.g. ['aditya', 'adithya']")
    context_triggers: List[str] = Field(default_factory=list, description="Surrounding contextual words e.g. ['sarvam', 'service']")
    negative_contexts: List[str] = Field(default_factory=list, description="Context words where this term should NOT be substituted e.g. ['fruit', 'eat']")
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0)
    source_type: str = Field(default="manual_dictionary")
    notes: Optional[str] = None


class ObservationInput(BaseModel):
    source: str = Field(default="user_correction", description="user_correction | dictionary_import | audio_session | negative_correction")
    original_text: Optional[str] = Field(None, description="The ASR/formatted transcript before correction, OR (if is_reversion) Kivi's memory-aware output that the user is reverting")
    corrected_text: Optional[str] = Field(None, description="The user's corrected transcript")
    explicit_term: Optional[str] = Field(None, description="Direct word add if manual")
    category: Optional[str] = Field("general")
    context_triggers: Optional[List[str]] = Field(default_factory=list)
    negative_contexts: Optional[List[str]] = Field(default_factory=list)
    is_reversion: bool = Field(
        default=False,
        description=(
            "If true, original_text/corrected_text are read in reverse: original_text is "
            "Kivi's memory-aware output and corrected_text is what the user actually wanted "
            "(i.e. the user undid a substitution Kivi made). This teaches negative evidence "
            "(learn_negative_correction) instead of a new positive mapping - use it when a "
            "memory intervened somewhere it should not have."
        )
    )


class TranscriptProcessRequest(BaseModel):
    asr_output: str = Field(..., description="Raw text from ASR model (e.g. 'ask aditya to review the sarvam kiwi service')")
    formatted_output: Optional[str] = Field(None, description="Pre-formatted text (if omitted, created automatically)")
    confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum combined confidence to intervene")


class DecisionTrace(BaseModel):
    original_span: str
    start_pos: int
    end_pos: int
    matched_memory_term: Optional[str]
    memory_id: Optional[int]
    phonetic_similarity: float
    context_score: float
    evidence_confidence: float
    composite_decision_score: float
    threshold: float
    decision: str  # "INTERVENED" or "SUPPRESSED" or "NO_MATCH"
    reason: str
    details: Dict[str, Any] = Field(default_factory=dict)


class TranscriptProcessResponse(BaseModel):
    asr_output: str
    formatted_output: str
    memory_aware_output: str
    interventions_count: int
    suppressed_count: int
    processing_latency_ms: float
    traces: List[DecisionTrace]
