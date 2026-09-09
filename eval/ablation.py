"""
Ablation & sensitivity study for Kivi's composite decision score.

The gating decision (core.memory_engine.compute_composite_score /
DEFAULT_COMPOSITE_WEIGHTS / DEFAULT_INTERVENTION_THRESHOLD) has three numbers that
were product decisions, not measurements: the phonetic/context/confidence weight
split (0.45 / 0.30 / 0.25) and the intervention threshold (0.65). This module is the
validation for those numbers, run against real recorded decision traces rather than
asserted by feel - see README "Decisions & Validation" for how to read the output.

Method
------
1. The caller (eval/run_eval.py) runs the seeded regression suite and the holdout
   generalization suite exactly once each, as the official, reported runs - and
   passes those two result dicts in here. This module never re-runs either suite
   itself: both suites mutate the database as they teach entities, so re-running
   them a second time inside this module would double-reinforce the holdout
   corrections and silently change the very numbers being validated. Every
   DecisionTrace either suite recorded already contains the three raw factor scores
   (phonetic_similarity, context_score, evidence_confidence) independently of what
   the default threshold/weights decided to do with them, which is all this module
   needs.
2. For each case, recompute the composite score and decision under an ALTERNATIVE
   threshold or weight triple by recombining those same recorded factors (via
   core.memory_engine.compute_composite_score) - not by re-running the pipeline.
   A negative context_score is still an absolute veto under every configuration
   tried here (see compute_composite_score's docstring for why that is a separate
   product decision from the weights).
3. Compare the resulting case-level decision (INTERVENE if any span would intervene)
   to the case's expected/desired decision, and tally accuracy / precision / recall /
   false-intervention-rate for that configuration.

This methodology only re-derives GATING decisions (intervene vs. not), not the exact
replacement text, and only evaluates spans the pipeline actually considered a
candidate for at the default configuration (phonetic_sim >= MIN_PHONETIC_SIMILARITY).
A materially different weighting could in principle surface different candidate spans
entirely; that is out of scope for this sweep and is stated here rather than implied.
"""

import time
from typing import Any, Dict, List, Tuple

from core.memory_engine import (
    compute_composite_score,
    DEFAULT_COMPOSITE_WEIGHTS,
    DEFAULT_INTERVENTION_THRESHOLD,
)


def _collect_graded_cases(regression_summary: Dict[str, Any], holdout_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flattens the two suites' already-computed results into one list of
    {suite, case_id, expected_decision, traces} records. Limitation cases are
    included using their desired_decision (what SHOULD happen), not the documented
    pre-fix expected_decision (what happens today under the shipped default config)
    - an alternative weighting is exactly what might resolve a documented
    limitation, so it belongs in the sweep evaluated against the *desired* outcome.
    """
    regression = regression_summary
    holdout = holdout_summary

    cases = []
    for c in regression["cases"]:
        cases.append({
            "suite": "regression_seeded",
            "case_id": c["id"],
            "expected_decision": c["expected_decision"],
            "traces": c["traces"],
        })
    for c in holdout["graded_cases"]:
        cases.append({
            "suite": "holdout_generalization",
            "case_id": c["case_id"],
            "expected_decision": c["expected_decision"],
            "traces": c["traces"],
        })
    for c in holdout["limitation_cases"]:
        cases.append({
            "suite": "holdout_generalization_limitation",
            "case_id": c["case_id"],
            "expected_decision": c["desired_decision"],
            "traces": c["traces"],
        })
    return cases


def _case_level_decision(
    case: Dict[str, Any],
    threshold: float,
    weights: Tuple[float, float, float]
) -> str:
    for trace in case["traces"]:
        composite, _ = compute_composite_score(
            trace["phonetic_similarity"], trace["context_score"], trace["evidence_confidence"], weights
        )
        if composite >= threshold:
            return "INTERVENE"
    return "DO_NOTHING"


def _score_configuration(
    cases: List[Dict[str, Any]],
    threshold: float,
    weights: Tuple[float, float, float]
) -> Dict[str, Any]:
    tp = fp = tn = fn = 0
    for case in cases:
        actual = _case_level_decision(case, threshold, weights)
        expected = case["expected_decision"]
        if expected == "INTERVENE":
            if actual == "INTERVENE":
                tp += 1
            else:
                fn += 1
        else:
            if actual == "DO_NOTHING":
                tn += 1
            else:
                fp += 1

    total = tp + fp + tn + fn
    accuracy = round(((tp + tn) / total) * 100, 2) if total else 0.0
    precision = round((tp / (tp + fp)) * 100, 2) if (tp + fp) > 0 else 100.0
    recall = round((tp / (tp + fn)) * 100, 2) if (tp + fn) > 0 else 100.0
    total_neg = tn + fp
    fir = round((fp / total_neg) * 100, 2) if total_neg > 0 else 0.0

    return {
        "threshold": threshold,
        "weights": {"phonetic": weights[0], "context": weights[1], "confidence": weights[2]},
        "accuracy_pct": accuracy,
        "precision_pct": precision,
        "recall_pct": recall,
        "false_intervention_rate_pct": fir,
        "confusion_matrix": {"true_positives": tp, "false_positives": fp, "true_negatives": tn, "false_negatives": fn},
    }


def run_ablation_study(regression_summary: Dict[str, Any], holdout_summary: Dict[str, Any]) -> Dict[str, Any]:
    cases = _collect_graded_cases(regression_summary, holdout_summary)

    # --- Threshold sweep at the shipped default weights ---
    threshold_sweep = []
    t = 0.30
    while t <= 0.901:
        threshold_sweep.append(_score_configuration(cases, round(t, 2), DEFAULT_COMPOSITE_WEIGHTS))
        t += 0.05

    # --- Weight ablation at the shipped default threshold ---
    weight_configs = {
        "phonetic_only": (1.0, 0.0, 0.0),
        "phonetic_plus_context": (0.6, 0.4, 0.0),
        "shipped_default": DEFAULT_COMPOSITE_WEIGHTS,
        "context_heavy": (0.30, 0.45, 0.25),
    }
    weight_ablation = {
        name: _score_configuration(cases, DEFAULT_INTERVENTION_THRESHOLD, w)
        for name, w in weight_configs.items()
    }

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_cases_in_sweep": len(cases),
        "cases_by_suite": {
            suite: sum(1 for c in cases if c["suite"] == suite)
            for suite in sorted(set(c["suite"] for c in cases))
        },
        "shipped_default": {
            "threshold": DEFAULT_INTERVENTION_THRESHOLD,
            "weights": {"phonetic": DEFAULT_COMPOSITE_WEIGHTS[0], "context": DEFAULT_COMPOSITE_WEIGHTS[1], "confidence": DEFAULT_COMPOSITE_WEIGHTS[2]},
        },
        "threshold_sweep": threshold_sweep,
        "weight_ablation": weight_ablation,
    }
