"""
Evaluation Engine for Kivi Word-Level Phonetic Memory System.
Executes benchmarks, measures Precision, Recall, False Intervention Rate, Latency, and generates reports.

This module runs the SEEDED REGRESSION SUITE (eval/regression_seeded.json): cases whose
entities are pre-loaded into memory by db/seed_data.py before the suite runs, with
hand-authored aliases and context triggers. It is useful as a regression guard (did a
change break a known-good case?) but, on its own, it is exactly the kind of evaluation
the assignment brief warns against: "A collection of successful examples chosen after
the system was built is not an evaluation." The aliases and negative-context words this
suite exercises are visible in db/seed_data.py, so a 100% pass rate here mostly proves
the seed data was written to match the test cases, not that the memory system
generalizes.

The suite that actually tests generalization is eval/holdout_engine.py
(eval/holdout_generalization.json): its entities are NOT in the seed data at all, and
are taught to the system live, through the same MemoryEngine.learn_from_correction /
create_or_update_memory / learn_negative_correction paths a real user's corrections
would go through, before being tested on differently-worded sentences that were never
part of the teaching step. Read this suite's results together with the holdout suite's
and eval/ablation.py's, not in isolation - see README "Decisions & Validation".
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from core.models import TranscriptProcessRequest, DBEvalRun, DBMemory
from core.transcript_processor import TranscriptProcessor
from db.database import SessionLocal, init_db, reset_db
from db.seed_data import seed_database


BENCHMARK_PATH = os.path.join(os.path.dirname(__file__), "regression_seeded.json")


class EvalEngine:
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or SessionLocal()


def capture_relevant_memory_state(db: Session, traces: List[Any]) -> Dict[str, Any]:
    """Snapshot the memory state that existed when an evaluation decision ran.

    Traces identify candidate memories; this preserves their complete durable
    records plus a compact description of the full active memory bank.
    """
    active_memories = (
        db.query(DBMemory)
        .filter(DBMemory.is_active == True)
        .order_by(DBMemory.id)
        .all()
    )
    relevant_ids = {
        trace.memory_id if hasattr(trace, "memory_id") else trace.get("memory_id")
        for trace in traces
    }
    relevant_ids.discard(None)

    return {
        "active_memory_count": len(active_memories),
        "active_memory_terms": [memory.canonical_term for memory in active_memories],
        "relevant_memories": [
            memory.to_dict() for memory in active_memories if memory.id in relevant_ids
        ],
    }


def run_evaluation(db: Session, benchmark_path: str = BENCHMARK_PATH, save_to_db: bool = True) -> Dict[str, Any]:
    with open(benchmark_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    processor = TranscriptProcessor(db)
    
    case_results = []
    total_cases = len(cases)
    passed_cases = 0
    
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0
    
    latencies = []

    for case in cases:
        req = TranscriptProcessRequest(
            asr_output=case["asr_input"],
            formatted_output=case.get("formatted_input"),
            confidence_threshold=0.65
        )
        
        t0 = time.perf_counter()
        resp = processor.process(req)
        latency_ms = round((time.perf_counter() - t0) * 1000, 3)
        latencies.append(latency_ms)

        actual_output = resp.memory_aware_output
        expected_output = case["expected_output"]
        
        # Check exact text match
        text_matched = actual_output.strip() == expected_output.strip()
        
        # Check decision
        actual_decision = "INTERVENE" if resp.interventions_count > 0 else "DO_NOTHING"
        expected_decision = case["expected_decision"]
        decision_matched = actual_decision == expected_decision
        
        passed = text_matched and decision_matched
        if passed:
            passed_cases += 1

        # Classify for Precision & Recall & False Interventions
        if expected_decision == "INTERVENE":
            if actual_decision == "INTERVENE" and text_matched:
                true_positives += 1
            else:
                false_negatives += 1
        elif expected_decision == "DO_NOTHING":
            if actual_decision == "DO_NOTHING":
                true_negatives += 1
            else:
                false_positives += 1

        case_results.append({
            "id": case["id"],
            "category": case["category"],
            "description": case["description"],
            "asr_input": case["asr_input"],
            "formatted_input": case.get("formatted_input"),
            "expected_output": expected_output,
            "actual_output": actual_output,
            "expected_decision": expected_decision,
            "actual_decision": actual_decision,
            "passed": passed,
            "latency_ms": latency_ms,
            "interventions_count": resp.interventions_count,
            "suppressed_count": resp.suppressed_count,
            "traces": [t.model_dump() for t in resp.traces],
            "relevant_memory_state": capture_relevant_memory_state(db, resp.traces),
            "notes": case.get("notes", "")
        })

    # Metric calculations
    accuracy = round((passed_cases / total_cases) * 100, 2) if total_cases > 0 else 0.0
    precision = round((true_positives / (true_positives + false_positives)) * 100, 2) if (true_positives + false_positives) > 0 else 100.0
    recall = round((true_positives / (true_positives + false_negatives)) * 100, 2) if (true_positives + false_negatives) > 0 else 100.0
    
    total_negative_cases = true_negatives + false_positives
    false_intervention_rate = round((false_positives / total_negative_cases) * 100, 2) if total_negative_cases > 0 else 0.0
    
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    p95_latency = round(sorted(latencies)[int(len(latencies) * 0.95)], 2) if latencies else 0.0

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": total_cases - passed_cases,
        "accuracy_pct": accuracy,
        "precision_pct": precision,
        "recall_pct": recall,
        "false_intervention_rate_pct": false_intervention_rate,
        "confusion_matrix": {
            "true_positives": true_positives,
            "false_positives": false_positives,
            "true_negatives": true_negatives,
            "false_negatives": false_negatives
        },
        "latency": {
            "avg_ms": avg_latency,
            "p95_ms": p95_latency,
            "min_ms": min(latencies) if latencies else 0.0,
            "max_ms": max(latencies) if latencies else 0.0
        },
        "cases": case_results
    }

    if save_to_db:
        eval_run = DBEvalRun(
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=total_cases - passed_cases,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            false_intervention_rate=false_intervention_rate,
            avg_latency_ms=avg_latency,
            results_json=json.dumps(summary)
        )
        db.add(eval_run)
        db.commit()

    return summary
