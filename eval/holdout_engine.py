"""
Holdout Generalization Suite for Kivi's Word-Level Phonetic Memory System.

Unlike eval/eval_engine.py (which replays sentences against entities that were
hand-seeded into db/seed_data.py specifically so those sentences would pass), this
suite:

  1. starts from the same seeded product memory bank a real deployment would have
     (so we can also confirm the new entities don't collide with it), then
  2. TEACHES a handful of entities that appear NOWHERE in db/seed_data.py, using only
     the same MemoryEngine.learn_from_correction / create_or_update_memory /
     learn_negative_correction calls a real correction, dictionary import, or
     reverted substitution would trigger, then
  3. tests recognition on sentences that were never part of the teaching step.

This is the suite that actually answers "does the memory system generalize", as
opposed to "did we remember to seed the right answer". See
eval/holdout_generalization.json for the journeys and eval/README-shaped commentary
inline in that file for why each case exists.

One journey (HOLD-04, flagged "known_limitation_before_fix") is a discovered failure
mode recorded on purpose - it is reported separately from the pass/fail tally, not
folded into headline accuracy, per the brief's instruction to report useful
interventions separately from unnecessary or incorrect ones.
"""

import os
import json
import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from core.models import TranscriptProcessRequest
from core.memory_engine import MemoryEngine
from core.transcript_processor import TranscriptProcessor
from eval.eval_engine import capture_relevant_memory_state

HOLDOUT_PATH = os.path.join(os.path.dirname(__file__), "holdout_generalization.json")


def _apply_teach_step(engine: MemoryEngine, step: Dict[str, Any]) -> Dict[str, Any]:
    started_at = time.perf_counter()
    method = step["method"]
    if method == "correction":
        result = engine.learn_from_correction(
            original_text=step["original_text"],
            corrected_text=step["corrected_text"],
            source="user_correction"
        )
    elif method == "dictionary":
        mem = engine.create_or_update_memory(
            canonical_term=step["canonical_term"],
            category=step.get("category", "general"),
            aliases=step.get("aliases", []),
            context_triggers=step.get("context_triggers", []),
            negative_contexts=step.get("negative_contexts", []),
            confidence_score=step.get("confidence_score", 0.85),
            source_type="manual_dictionary",
            notes=step.get("notes")
        )
        result = mem.to_dict()
    elif method == "negative_correction":
        result = engine.learn_negative_correction(
            memory_aware_text=step["memory_aware_text"],
            user_reverted_text=step["user_reverted_text"],
            source="negative_correction"
        )
    else:
        raise ValueError(f"Unknown teach method: {method}")
    return {
        "method": method,
        "latency_ms": round((time.perf_counter() - started_at) * 1000, 3),
        "result": result,
    }


def run_holdout_suite(db: Session, holdout_path: str = HOLDOUT_PATH) -> Dict[str, Any]:
    with open(holdout_path, "r", encoding="utf-8") as f:
        journeys = json.load(f)

    engine = MemoryEngine(db)
    processor = TranscriptProcessor(db)

    graded_cases: List[Dict[str, Any]] = []
    limitation_cases: List[Dict[str, Any]] = []
    journey_log: List[Dict[str, Any]] = []
    inference_latencies: List[float] = []
    teaching_latencies: List[float] = []

    true_positives = false_positives = true_negatives = false_negatives = 0

    for journey in journeys:
        teach_log = [_apply_teach_step(engine, step) for step in journey.get("teach", [])]
        teaching_latencies.extend(step["latency_ms"] for step in teach_log)
        is_limitation = journey.get("flag") == "known_limitation_before_fix"

        for case in journey.get("assert", []):
            req = TranscriptProcessRequest(
                asr_output=case["asr_input"],
                formatted_output=None,
                confidence_threshold=0.65
            )
            t0 = time.perf_counter()
            resp = processor.process(req)
            latency_ms = round((time.perf_counter() - t0) * 1000, 3)
            inference_latencies.append(latency_ms)

            actual_output = resp.memory_aware_output
            expected_output = case["expected_output"]
            text_matched = actual_output.strip() == expected_output.strip()

            actual_decision = "INTERVENE" if resp.interventions_count > 0 else "DO_NOTHING"
            expected_decision = case["expected_decision"]
            decision_matched = actual_decision == expected_decision
            passed = text_matched and decision_matched

            record = {
                "case_id": case["case_id"],
                "journey": journey["journey"],
                "entity": journey.get("entity"),
                "description": case.get("notes", ""),
                "asr_input": case["asr_input"],
                "expected_output": expected_output,
                "actual_output": actual_output,
                "expected_decision": expected_decision,
                "actual_decision": actual_decision,
                # For a documented pre-fix limitation, expected_decision intentionally
                # records today's (buggy) behavior so the harness can confirm the bug
                # is still reproducible; desired_decision records what SHOULD happen,
                # for eval/ablation.py and for humans reading the report. For a normal
                # graded case the two are always the same.
                "desired_decision": case.get("desired_decision", expected_decision),
                "passed": passed,
                "latency_ms": latency_ms,
                "interventions_count": resp.interventions_count,
                "suppressed_count": resp.suppressed_count,
                "traces": [t.model_dump() for t in resp.traces],
                "relevant_memory_state": capture_relevant_memory_state(db, resp.traces),
            }

            if is_limitation:
                limitation_cases.append(record)
                continue

            graded_cases.append(record)
            if expected_decision == "INTERVENE":
                if actual_decision == "INTERVENE" and text_matched:
                    true_positives += 1
                else:
                    false_negatives += 1
            else:
                if actual_decision == "DO_NOTHING":
                    true_negatives += 1
                else:
                    false_positives += 1

        journey_log.append({
            "id": journey["id"],
            "journey": journey["journey"],
            "description": journey.get("description", ""),
            "flag": journey.get("flag"),
            "teach_steps": teach_log,
        })

    total_graded = len(graded_cases)
    passed_graded = sum(1 for c in graded_cases if c["passed"])
    accuracy = round((passed_graded / total_graded) * 100, 2) if total_graded else 0.0
    precision = round((true_positives / (true_positives + false_positives)) * 100, 2) if (true_positives + false_positives) > 0 else 100.0
    recall = round((true_positives / (true_positives + false_negatives)) * 100, 2) if (true_positives + false_negatives) > 0 else 100.0
    total_negative = true_negatives + false_positives
    false_intervention_rate = round((false_positives / total_negative) * 100, 2) if total_negative > 0 else 0.0

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_graded_cases": total_graded,
        "passed_graded_cases": passed_graded,
        "failed_graded_cases": total_graded - passed_graded,
        "accuracy_pct": accuracy,
        "precision_pct": precision,
        "recall_pct": recall,
        "false_intervention_rate_pct": false_intervention_rate,
        "confusion_matrix": {
            "true_positives": true_positives,
            "false_positives": false_positives,
            "true_negatives": true_negatives,
            "false_negatives": false_negatives,
        },
        "latency": {
            "inference": {
                "calls": len(inference_latencies),
                "avg_ms": round(sum(inference_latencies) / len(inference_latencies), 2) if inference_latencies else 0.0,
                "max_ms": max(inference_latencies) if inference_latencies else 0.0,
            },
            "teaching": {
                "calls": len(teaching_latencies),
                "avg_ms": round(sum(teaching_latencies) / len(teaching_latencies), 2) if teaching_latencies else 0.0,
                "max_ms": max(teaching_latencies) if teaching_latencies else 0.0,
            },
        },
        "journeys": journey_log,
        "graded_cases": graded_cases,
        "limitation_cases": limitation_cases,
    }
