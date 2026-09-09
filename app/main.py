"""
FastAPI Application for Kivi Word-Level Phonetic Memory System.
Exposes REST endpoints for processing, learning, memory inspection, resetting, and evaluations.
"""

import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from core.models import (
    MemoryCreate,
    ObservationInput,
    TranscriptProcessRequest,
    TranscriptProcessResponse,
    DBMemory,
    DBEvidenceLog,
    DBEvalRun
)
from core.memory_engine import MemoryEngine
from core.transcript_processor import TranscriptProcessor
from db.database import get_db, init_db, reset_db, SessionLocal
from db.seed_data import seed_database
from eval.eval_engine import run_evaluation
from eval.holdout_engine import run_holdout_suite

# Initialize Database on app startup
init_db()
# Ensure seed data exists if DB is empty
with SessionLocal() as db:
    if db.query(DBMemory).count() == 0:
        seed_database(db)

app = FastAPI(
    title="Kivi Phonetic Memory System",
    description="Word-level personal AI memory engine for personalized speech transcription.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)


# ==========================================
# REST API Endpoints
# ==========================================

@app.post("/api/process", response_model=TranscriptProcessResponse)
def process_transcript(req: TranscriptProcessRequest, db: Session = Depends(get_db)):
    """
    Transforms ASR output + Formatted speech into personalized Memory-Aware output,
    with complete decision traces and metrics.
    """
    processor = TranscriptProcessor(db)
    return processor.process(req)


@app.post("/api/learn")
def learn_observation(obs: ObservationInput, db: Session = Depends(get_db)):
    """
    Ingests an observation:
    - User correction (diff between original and corrected text) -> learns/reinforces a mapping
    - Reversion (is_reversion=true: diff between Kivi's wrong output and what the user wanted) ->
      teaches negative evidence so the same false substitution doesn't repeat in this context
    - Or direct explicit dictionary word addition
    """
    engine = MemoryEngine(db)

    if obs.is_reversion and obs.corrected_text and obs.original_text:
        penalized = engine.learn_negative_correction(
            memory_aware_text=obs.original_text,
            user_reverted_text=obs.corrected_text,
            source=obs.source or "negative_correction"
        )
        return {"status": "success", "type": "negative_correction_learned", "penalized": penalized}
    elif obs.corrected_text and obs.original_text:
        learned = engine.learn_from_correction(
            original_text=obs.original_text,
            corrected_text=obs.corrected_text,
            source=obs.source
        )
        return {"status": "success", "type": "correction_learned", "learned": learned}
    elif obs.explicit_term:
        mem = engine.create_or_update_memory(
            canonical_term=obs.explicit_term,
            category=obs.category or "general",
            context_triggers=obs.context_triggers or [],
            negative_contexts=obs.negative_contexts or [],
            source_type=obs.source
        )
        return {"status": "success", "type": "term_created", "memory": mem.to_dict()}
    else:
        raise HTTPException(status_code=400, detail="Must provide corrected_text or explicit_term")


@app.get("/api/memories")
def get_memories(active_only: bool = Query(True), db: Session = Depends(get_db)):
    """Lists all stored phonetic memories and their current confidence/evidence state."""
    engine = MemoryEngine(db)
    memories = engine.get_all_memories(active_only=active_only)
    return [m.to_dict() for m in memories]


@app.post("/api/memories")
def add_memory(mem_in: MemoryCreate, db: Session = Depends(get_db)):
    """Manually add or update a memory entry."""
    engine = MemoryEngine(db)
    mem = engine.create_or_update_memory(
        canonical_term=mem_in.canonical_term,
        category=mem_in.category,
        aliases=mem_in.aliases,
        context_triggers=mem_in.context_triggers,
        negative_contexts=mem_in.negative_contexts,
        confidence_score=mem_in.confidence_score,
        source_type=mem_in.source_type,
        notes=mem_in.notes
    )
    return mem.to_dict()


@app.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: int, db: Session = Depends(get_db)):
    """Removes a memory entry."""
    engine = MemoryEngine(db)
    success = engine.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "success", "deleted_id": memory_id}


@app.post("/api/reset")
def reset_system(with_seed: bool = Query(True), db: Session = Depends(get_db)):
    """Resets the memory system to clean state, optionally re-seeding bootstrap personas."""
    reset_db()
    if with_seed:
        seed_database(db)
    return {"status": "success", "message": "System memory reset completed.", "seeded": with_seed}


@app.get("/api/eval")
def trigger_evaluation(save_to_db: bool = Query(True), db: Session = Depends(get_db)):
    """
    Runs the SEEDED REGRESSION suite (entities pre-loaded by db/seed_data.py) and
    returns accuracy, precision, latency, and per-case traces. This is a fast
    in-app regression check, not the full evaluation story - see /api/eval/holdout
    and, for the complete picture including the ablation/sensitivity study, run
    `python -m eval.run_eval` from a terminal (see RUN.md).
    """
    summary = run_evaluation(db, save_to_db=save_to_db)
    return summary


@app.post("/api/eval/holdout")
def trigger_holdout_evaluation(db: Session = Depends(get_db)):
    """
    Runs the HOLDOUT GENERALIZATION suite: teaches a handful of entities that are
    NOT in db/seed_data.py live, through the same MemoryEngine calls a real
    correction/dictionary-import/reversion would use, then tests recognition on
    unseen sentences. This is a POST, not a GET, because - unlike /api/eval - it
    mutates the memory store (that live teaching is the point). Call /api/reset
    afterwards if you want the store back to a clean seeded state.
    """
    summary = run_holdout_suite(db)
    return summary


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Returns database size, memory count, and evidence stats."""
    mem_count = db.query(DBMemory).count()
    evidence_count = db.query(DBEvidenceLog).count()
    eval_count = db.query(DBEvalRun).count()
    return {
        "total_memories": mem_count,
        "evidence_logs": evidence_count,
        "eval_runs": eval_count
    }


# Static Web UI Mount
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
