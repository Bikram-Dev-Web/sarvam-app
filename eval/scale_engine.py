"""
Large-Scale Generalization Suite for Kivi's Word-Level Phonetic Memory System.

Suites 1 and 2 answer "does a known-good case still work" (16 cases, 8 seeded
entities) and "does this generalize at all" (7 graded cases, 2 taught entities).
Both are small enough that a single lucky or unlucky case moves the headline by
several points, and small enough that some behaviours simply never occur in them.
This suite exists because the assignment brief warns that a strong-looking result
on a weak evaluation is not strong work, and because two of the three failure
modes this project documents were only reachable at volume.

It teaches 49 entities that appear in NO other data file in this repository and
nowhere in the brief - Indian and non-Indian person names, products, ML/infra
jargon, organisations and places - through the same
MemoryEngine.learn_from_correction / create_or_update_memory calls a real user's
correction or dictionary import would trigger. It then grades ~694 transcripts.

Case families, graded SEPARATELY and never averaged into a single number:

  P     positive        The entity is genuinely meant and the sentence carries
                        corroborating context. Ground truth: INTERVENE. 294 of
                        these use a mishearing NEVER shown during teaching (the
                        actual generalization test); 49 replay the taught one (a
                        recall check, which should be near-perfect and is not
                        evidence of generalization on its own).

  HN    hard negative   The similar-sounding word is a DIFFERENT real word used in
                        its ordinary meaning - `basil` the herb, a `red panda` at
                        the zoo, the `temporal lobe`, a `sentry` on guard.
                        Ground truth: DO_NOTHING.

  ADV   adversarial     The hardest false-intervention test here. An ordinary
                        English word (or a different real person's name) used
                        naturally, in a sentence that ALSO contains the entity's
                        own positive triggers - so context actively argues FOR the
                        wrong edit and only the phonetic term and the threshold
                        prevent it. Ground truth: DO_NOTHING. These are adversarial
                        by construction: the family's error rate is a stress-test
                        number, not an estimate of production behaviour. Read it
                        next to CTRL, never instead of it.

  CTRL  clean control   220 ordinary sentences containing no target entity at all.
                        Ground truth: DO_NOTHING. This is the honest denominator
                        for a false-intervention rate a real user would experience,
                        because most of what anyone dictates mentions none of their
                        remembered terms.

  W     weak evidence   The entity is meant but NOTHING in the sentence corroborates
                        it. Reported separately and never folded into the headline,
                        because the ground truth here is a product decision rather
                        than a fact: the shipped policy is deliberate silence under
                        weak evidence, while a user who just said a name arguably
                        wants it spelled correctly regardless. Both readings are
                        reported so the choice stays visible instead of being
                        averaged away.

Beyond grading, the suite measures four things the small suites structurally
cannot:

  * interference  - replays suite 1 unchanged before and after loading 49 new
                    entities, to check a larger memory bank introduces no new
                    collisions on known-good cases.
  * adaptation    - reverts every false positive through learn_negative_correction
                    exactly as a user would, then re-measures BOTH the negatives
                    (did suppression work) AND the positives for those same
                    entities (did suppression cost us the memory). Measuring only
                    the first half is how the trigger-poisoning defect fixed in
                    learn_negative_correction went unnoticed - see README 4.7.
  * sensitivity   - repeats eval/ablation.py's method (recombine recorded trace
                    factors through compute_composite_score) over ~600 graded cases
                    instead of ~20. Gating decisions only, not replacement text, and
                    only over spans already treated as candidates at the shipped
                    config - same stated scope as eval/ablation.py.
  * scaling       - latency against memory-bank size and against transcript length,
                    which are the two axes that actually grow in deployment.

Everything is generated deterministically from eval/scale_generalization.json
(fixed RNG seed for the control sentences), so no case was hand-picked after
seeing a result and the whole corpus is inspectable before it is run.
"""

import os
import json
import time
import random
import statistics
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.models import TranscriptProcessRequest, DBMemory
from core.memory_engine import (
    MemoryEngine,
    compute_composite_score,
    DEFAULT_COMPOSITE_WEIGHTS,
    DEFAULT_INTERVENTION_THRESHOLD,
)
from core.transcript_processor import TranscriptProcessor

SCALE_PATH = os.path.join(os.path.dirname(__file__), "scale_generalization.json")

THRESHOLD_GRID = [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
WEIGHT_CONFIGS = {
    "shipped_default": DEFAULT_COMPOSITE_WEIGHTS,
    "phonetic_only": (1.0, 0.0, 0.0),
    "phonetic_heavy": (0.70, 0.20, 0.10),
    "context_heavy": (0.30, 0.50, 0.20),
    "confidence_heavy": (0.30, 0.20, 0.50),
    "equal_thirds": (0.34, 0.33, 0.33),
    "no_confidence_term": (0.60, 0.40, 0.0),
}
GRADED_FAMILIES = ("P", "HN", "ADV", "CTRL")


# ---------------------------------------------------------------------------
# Expected-output construction
# ---------------------------------------------------------------------------

def format_expected(sentence: str) -> str:
    """
    Capitalize the first character and add a terminal period.

    Deliberately reimplemented here in three lines rather than imported from
    core.transcript_processor.format_raw_asr: expected outputs should not be
    derived from the code under test. Formatting is not what this suite grades -
    the substitution is - so replicating only the part that affects the expected
    string keeps the two independent.
    """
    s = sentence.strip()
    if not s:
        return ""
    s = s[0].upper() + s[1:]
    if s[-1] not in ".?!":
        s += "."
    return s


# ---------------------------------------------------------------------------
# Case generation (fully deterministic)
# ---------------------------------------------------------------------------

def build_cases(corpus: Dict[str, Any]) -> List[Dict[str, Any]]:
    templates = corpus["templates"]
    person_categories = set(templates["person_categories"])
    cases: List[Dict[str, Any]] = []

    for entity in corpus["entities"]:
        canonical = entity["canonical"]
        ctx_a, ctx_b = entity["test_ctx"]
        is_person = entity["category"] in person_categories
        positive_templates = templates["person_positive"] if is_person else templates["thing_positive"]
        weak_templates = templates["person_weak"] if is_person else templates["thing_weak"]

        common = dict(
            entity=canonical,
            category=entity["category"],
            teach_method=entity["method"],
        )

        # P - held-out mishearings the system has never been shown, in sentence
        # templates never used for teaching.
        for alias_idx, alias in enumerate(entity["holdout_aliases"]):
            for tpl_idx, template in enumerate(positive_templates):
                cases.append(dict(
                    common,
                    case_id=f"P-{canonical}-{alias_idx}{tpl_idx}",
                    family="P",
                    alias_seen_in_teaching=False,
                    asr_input=template.format(a=alias, c1=ctx_a, c2=ctx_b),
                    expected_output=format_expected(template.format(a=canonical, c1=ctx_a, c2=ctx_b)),
                    expected_decision="INTERVENE",
                ))

        # P - the alias that WAS taught. A recall check, separated in the report
        # from the held-out cases so the two are never conflated.
        template = positive_templates[0]
        cases.append(dict(
            common,
            case_id=f"P-{canonical}-taught",
            family="P",
            alias_seen_in_teaching=True,
            asr_input=template.format(a=entity["taught_alias"], c1=ctx_a, c2=ctx_b),
            expected_output=format_expected(template.format(a=canonical, c1=ctx_a, c2=ctx_b)),
            expected_decision="INTERVENE",
        ))

        # W - entity meant, zero corroborating context. Both readings recorded.
        for weak_idx, template in enumerate(weak_templates):
            alias = entity["holdout_aliases"][0]
            cases.append(dict(
                common,
                case_id=f"W-{canonical}-{weak_idx}",
                family="W",
                alias_seen_in_teaching=False,
                asr_input=template.format(a=alias),
                expected_output=format_expected(template.format(a=alias)),
                expected_decision="DO_NOTHING",
                ideal_output=format_expected(template.format(a=canonical)),
                ideal_decision="INTERVENE",
            ))

        # HN - the similar word in its own genuine meaning.
        homophone = entity.get("homophone")
        if homophone:
            cases.append(dict(
                common,
                case_id=f"HN-{canonical}",
                family="HN",
                alias_seen_in_teaching=False,
                asr_input=homophone["sentence"],
                expected_output=format_expected(homophone["sentence"]),
                expected_decision="DO_NOTHING",
                near_miss=homophone["word"],
            ))

    # ADV - ordinary word plus the entity's own triggers.
    entities_by_name = {e["canonical"]: e for e in corpus["entities"]}
    for adversarial in corpus["adversarial"]:
        entity = entities_by_name[adversarial["entity"]]
        cases.append(dict(
            case_id=f"ADV-{adversarial['entity']}",
            family="ADV",
            entity=adversarial["entity"],
            category=entity["category"],
            teach_method=entity["method"],
            alias_seen_in_teaching=False,
            asr_input=adversarial["sentence"],
            expected_output=format_expected(adversarial["sentence"]),
            expected_decision="DO_NOTHING",
            near_miss=adversarial["near_miss"],
        ))

    return cases


def build_controls(corpus: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Ordinary sentences with no target entity. Seeded RNG, so the same 220
    sentences are produced on every run and can be inspected before being trusted.
    """
    config = corpus["controls"]
    rng = random.Random(config["seed"])

    forbidden_words = set()
    for entity in corpus["entities"]:
        terms = [entity["canonical"], entity["taught_alias"], *entity["holdout_aliases"]]
        if entity.get("homophone"):
            terms.append(entity["homophone"]["word"])
        for term in terms:
            forbidden_words.update(term.lower().split())

    controls: List[Dict[str, Any]] = []
    seen = set()
    while len(controls) < config["count"]:
        template = config["templates"][len(controls) % len(config["templates"])]
        noun_a, noun_b = rng.sample(config["nouns"], 2)
        sentence = template.format(n1=noun_a, n2=noun_b, adj=rng.choice(config["adjectives"]))
        if sentence in seen or any(w in forbidden_words for w in sentence.split()):
            continue
        seen.add(sentence)
        controls.append(dict(
            case_id=f"CTRL-{len(controls):03d}",
            family="CTRL",
            entity=None,
            category="control",
            teach_method=None,
            alias_seen_in_teaching=False,
            asr_input=sentence,
            expected_output=format_expected(sentence),
            expected_decision="DO_NOTHING",
        ))
    return controls


# ---------------------------------------------------------------------------
# Execution and scoring
# ---------------------------------------------------------------------------

def _run_case(processor: TranscriptProcessor, case: Dict[str, Any]) -> Dict[str, Any]:
    request = TranscriptProcessRequest(
        asr_output=case["asr_input"],
        formatted_output=None,
        confidence_threshold=DEFAULT_INTERVENTION_THRESHOLD,
    )
    started_at = time.perf_counter()
    response = processor.process(request)
    latency_ms = round((time.perf_counter() - started_at) * 1000, 3)

    actual_decision = "INTERVENE" if response.interventions_count > 0 else "DO_NOTHING"
    text_matched = response.memory_aware_output.strip() == case["expected_output"].strip()

    record = dict(case)
    record.update(
        actual_output=response.memory_aware_output,
        actual_decision=actual_decision,
        text_matched=text_matched,
        passed=text_matched and actual_decision == case["expected_decision"],
        latency_ms=latency_ms,
        interventions_count=response.interventions_count,
        suppressed_count=response.suppressed_count,
        traces=[t.model_dump() for t in response.traces],
    )
    if "ideal_output" in case:
        record["ideal_matched"] = (
            response.memory_aware_output.strip() == case["ideal_output"].strip()
        )
    return record


def score(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Same grading contract as eval_engine / holdout_engine: an INTERVENE case only
    counts as a true positive if the resulting TEXT is also exactly right, so
    substituting the wrong canonical term is never scored as a success.
    """
    tp = fp = tn = fn = 0
    for record in records:
        if record["expected_decision"] == "INTERVENE":
            if record["actual_decision"] == "INTERVENE" and record["text_matched"]:
                tp += 1
            else:
                fn += 1
        else:
            if record["actual_decision"] == "DO_NOTHING":
                tn += 1
            else:
                fp += 1

    total = len(records)
    passed = sum(1 for r in records if r["passed"])
    latencies = sorted(r["latency_ms"] for r in records)

    def pct(numerator, denominator):
        return round(numerator / denominator * 100, 2) if denominator else None

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy_pct": pct(passed, total) or 0.0,
        "precision_pct": pct(tp, tp + fp),
        "recall_pct": pct(tp, tp + fn),
        "false_intervention_rate_pct": pct(fp, tn + fp),
        "confusion_matrix": {
            "true_positives": tp, "false_positives": fp,
            "true_negatives": tn, "false_negatives": fn,
        },
        "latency": {
            "avg_ms": round(statistics.mean(latencies), 3) if latencies else 0.0,
            "median_ms": round(statistics.median(latencies), 3) if latencies else 0.0,
            "p95_ms": round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))], 3) if latencies else 0.0,
            "max_ms": round(max(latencies), 3) if latencies else 0.0,
        },
    }


def teach_entity(engine: MemoryEngine, entity: Dict[str, Any]) -> Dict[str, Any]:
    """Teaches one entity through the same path a real user's action would use."""
    started_at = time.perf_counter()
    if entity["method"] == "correction":
        original = format_expected(entity["teach_tpl"].format(a=entity["taught_alias"]))
        corrected = format_expected(entity["teach_tpl"].format(a=entity["canonical"]))
        detail = {
            "original_text": original,
            "corrected_text": corrected,
            "learned": engine.learn_from_correction(original, corrected, source="user_correction"),
        }
    elif entity["method"] == "dictionary":
        memory = engine.create_or_update_memory(
            canonical_term=entity["canonical"],
            category=entity["category"],
            aliases=[entity["taught_alias"]],
            context_triggers=entity["triggers"],
            negative_contexts=entity["negatives"],
            confidence_score=0.90,
            source_type="manual_dictionary",
            notes="scale-suite dictionary entry",
        )
        detail = {"memory_id": memory.id, "aliases": [entity["taught_alias"]]}
    else:
        raise ValueError(f"Unknown teach method: {entity['method']}")

    return {
        "entity": entity["canonical"],
        "method": entity["method"],
        "latency_ms": round((time.perf_counter() - started_at) * 1000, 3),
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# Sensitivity sweep (same method and same stated scope as eval/ablation.py)
# ---------------------------------------------------------------------------

def _sweep_decision(record, threshold, weights):
    for trace in record["traces"]:
        composite, _ = compute_composite_score(
            trace["phonetic_similarity"],
            trace["context_score"],
            trace["evidence_confidence"],
            weights,
        )
        if composite >= threshold:
            return "INTERVENE"
    return "DO_NOTHING"


def _sweep_evaluate(records, threshold, weights):
    tp = fp = tn = fn = 0
    for record in records:
        decision = _sweep_decision(record, threshold, weights)
        if record["expected_decision"] == "INTERVENE":
            tp += decision == "INTERVENE"
            fn += decision != "INTERVENE"
        else:
            tn += decision == "DO_NOTHING"
            fp += decision != "DO_NOTHING"

    def pct(numerator, denominator):
        return round(numerator / denominator * 100, 2) if denominator else None

    return {
        "threshold": threshold,
        "weights": {"phonetic": weights[0], "context": weights[1], "confidence": weights[2]},
        "decision_accuracy_pct": pct(tp + tn, len(records)),
        "precision_pct": pct(tp, tp + fp),
        "recall_pct": pct(tp, tp + fn),
        "false_intervention_rate_pct": pct(fp, tn + fp),
        "confusion_matrix": {
            "true_positives": tp, "false_positives": fp,
            "true_negatives": tn, "false_negatives": fn,
        },
    }


# ---------------------------------------------------------------------------
# Suite entry point
# ---------------------------------------------------------------------------

def run_scale_suite(
    db: Session,
    corpus_path: str = SCALE_PATH,
    regression_runner=None,
    include_scaling: bool = True,
) -> Dict[str, Any]:
    """
    Runs the full large-scale suite.

    `regression_runner` is an optional callable (db -> regression summary dict).
    When supplied - eval/run_eval.py passes eval_engine.run_evaluation - suite 1 is
    replayed before and after the 49 new entities are loaded, which is how this
    suite measures cross-entity interference. Omitted, that section is skipped and
    everything else still runs, so this module stays usable standalone.
    """
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    engine = MemoryEngine(db)
    results: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    bank_before = db.query(DBMemory).filter(DBMemory.is_active == True).count()

    # --- interference: suite 1 on the pre-existing bank ---
    if regression_runner is not None:
        baseline = regression_runner(db)
        results["interference_before"] = {
            "memory_bank_size": bank_before,
            "total_cases": baseline["total_cases"],
            "accuracy_pct": baseline["accuracy_pct"],
            "precision_pct": baseline["precision_pct"],
            "recall_pct": baseline["recall_pct"],
            "false_intervention_rate_pct": baseline["false_intervention_rate_pct"],
            "latency": baseline["latency"],
        }

    # --- teaching ---
    teach_log = [teach_entity(engine, entity) for entity in corpus["entities"]]
    teach_latencies = sorted(step["latency_ms"] for step in teach_log)
    bank_after = db.query(DBMemory).filter(DBMemory.is_active == True).count()
    results["teaching"] = {
        "entities_taught": len(corpus["entities"]),
        "memory_bank_before": bank_before,
        "memory_bank_after": bank_after,
        "avg_latency_ms": round(statistics.mean(teach_latencies), 3),
        "p95_latency_ms": round(teach_latencies[int(len(teach_latencies) * 0.95)], 3),
        "max_latency_ms": round(max(teach_latencies), 3),
        "log": teach_log,
    }

    # --- grading ---
    processor = TranscriptProcessor(db)
    cases = build_cases(corpus) + build_controls(corpus)
    records = [_run_case(processor, case) for case in cases]

    by_family = {}
    for family in ("P", "HN", "ADV", "W", "CTRL"):
        subset = [r for r in records if r["family"] == family]
        if subset:
            by_family[family] = score(subset)

    weak = [r for r in records if r["family"] == "W"]
    if weak:
        would_be_correct = sum(1 for r in weak if r.get("ideal_matched"))
        by_family["W"]["ideal_reading"] = {
            "_note": "What the W family would score if the ground truth were 'the user "
                     "said the name, spell it correctly regardless of context' instead of "
                     "the shipped 'stay silent under weak evidence' policy.",
            "would_be_correct": would_be_correct,
            "total": len(weak),
            "recall_pct": round(would_be_correct / len(weak) * 100, 2),
        }

    graded = [r for r in records if r["family"] in GRADED_FAMILIES]
    results["headline"] = score(graded)
    results["headline"]["_note"] = (
        "Covers P + HN + ADV + CTRL - every family whose ground truth is a fact rather "
        "than a product decision. The W family is excluded on purpose and reported "
        "separately. Read the per-family table before this number: the ADV family is "
        "adversarial by construction, so it pulls the blended false-intervention rate "
        "well above what ordinary traffic (CTRL) produces."
    )
    results["by_family"] = by_family

    def breakdown(key):
        buckets: Dict[Any, List[Dict[str, Any]]] = {}
        for record in graded:
            buckets.setdefault(record.get(key) or "n/a", []).append(record)
        return {k: score(v) for k, v in sorted(buckets.items(), key=lambda kv: str(kv[0]))}

    results["by_category"] = breakdown("category")
    results["by_teach_method"] = breakdown("teach_method")

    positives = [r for r in records if r["family"] == "P"]
    results["seen_vs_unseen_alias"] = {
        "_note": "The taught row is a recall check and should be near-perfect; only the "
                 "held-out row is evidence of generalization.",
        "taught_alias": score([r for r in positives if r["alias_seen_in_teaching"]]),
        "heldout_alias": score([r for r in positives if not r["alias_seen_in_teaching"]]),
    }

    results["failures"] = [
        {
            "case_id": r["case_id"], "family": r["family"], "entity": r["entity"],
            "asr_input": r["asr_input"],
            "expected_output": r["expected_output"], "actual_output": r["actual_output"],
            "expected_decision": r["expected_decision"], "actual_decision": r["actual_decision"],
            "traces": [
                {
                    "original_span": t["original_span"],
                    "matched_memory_term": t["matched_memory_term"],
                    "decision": t["decision"],
                    "phonetic_similarity": t["phonetic_similarity"],
                    "context_score": t["context_score"],
                    "evidence_confidence": t["evidence_confidence"],
                    "composite_decision_score": t["composite_decision_score"],
                }
                for t in r["traces"]
            ],
        }
        for r in records if not r["passed"] and r["family"] in GRADED_FAMILIES
    ]

    # --- sensitivity sweep over every graded case ---
    results["sensitivity"] = {
        "_note": "Same method and same stated scope as eval/ablation.py - recombines the "
                 "decision traces recorded above through compute_composite_score. "
                 "Re-derives GATING decisions only, not replacement text, and only over "
                 "spans already treated as candidates at the shipped configuration.",
        "cases_in_sweep": len(graded),
        "shipped_default": {
            "threshold": DEFAULT_INTERVENTION_THRESHOLD,
            "weights": {
                "phonetic": DEFAULT_COMPOSITE_WEIGHTS[0],
                "context": DEFAULT_COMPOSITE_WEIGHTS[1],
                "confidence": DEFAULT_COMPOSITE_WEIGHTS[2],
            },
        },
        "threshold_sweep": [
            _sweep_evaluate(graded, t, DEFAULT_COMPOSITE_WEIGHTS) for t in THRESHOLD_GRID
        ],
        "weight_ablation": {
            name: _sweep_evaluate(graded, DEFAULT_INTERVENTION_THRESHOLD, w)
            for name, w in WEIGHT_CONFIGS.items()
        },
    }

    # --- interference: suite 1 replayed on the grown bank ---
    if regression_runner is not None:
        after = regression_runner(db)
        results["interference_after"] = {
            "memory_bank_size": bank_after,
            "total_cases": after["total_cases"],
            "accuracy_pct": after["accuracy_pct"],
            "precision_pct": after["precision_pct"],
            "recall_pct": after["recall_pct"],
            "false_intervention_rate_pct": after["false_intervention_rate_pct"],
            "latency": after["latency"],
            "newly_failing": [c["id"] for c in after["cases"] if not c["passed"]],
        }

    # --- adaptation: revert every false positive, then re-measure BOTH sides ---
    negative_records = [r for r in records if r["family"] in ("HN", "ADV")]
    adaptation_before = score(negative_records)
    revert_log = []
    affected_memory_ids = set()
    for record in negative_records:
        if record["actual_decision"] != "INTERVENE":
            continue
        penalized = engine.learn_negative_correction(
            memory_aware_text=record["actual_output"],
            user_reverted_text=record["expected_output"],
            source="negative_correction",
        )
        revert_log.append({"case_id": record["case_id"], "penalized": penalized})
        affected_memory_ids.update(entry["memory_id"] for entry in penalized)

    processor = TranscriptProcessor(db)
    negative_case_defs = [c for c in cases if c["family"] in ("HN", "ADV")]
    adaptation_after = score([_run_case(processor, c) for c in negative_case_defs])

    affected_entities = {
        db.query(DBMemory).filter(DBMemory.id == memory_id).first().canonical_term
        for memory_id in affected_memory_ids
    }
    affected_positive_defs = [
        c for c in cases if c["family"] == "P" and c["entity"] in affected_entities
    ]
    positives_before = score([
        r for r in records if r["family"] == "P" and r["entity"] in affected_entities
    ]) if affected_positive_defs else None
    positives_after = score([
        _run_case(processor, c) for c in affected_positive_defs
    ]) if affected_positive_defs else None

    results["adaptation"] = {
        "_note": "Both halves are reported on purpose. Measuring only whether suppression "
                 "worked is how the learn_negative_correction trigger-poisoning defect "
                 "(README 4.7) stayed invisible: it fixed 100% of the false positives "
                 "while silently taking every true positive for those same entities to "
                 "zero, because the reverted sentence's words included the memory's own "
                 "context triggers and a matched negative context is an absolute veto.",
        "reverts_applied": len(revert_log),
        "affected_entities": sorted(affected_entities),
        "negatives_before": adaptation_before,
        "negatives_after": adaptation_after,
        "positives_for_affected_entities_before": positives_before,
        "positives_for_affected_entities_after": positives_after,
        "log": revert_log,
    }

    # --- scaling ---
    if include_scaling:
        results["scaling"] = _measure_scaling(db, cases)

    results["corpus"] = {
        "entities": len(corpus["entities"]),
        "total_transcripts": len(cases),
        "by_family": {
            family: len([c for c in cases if c["family"] == family])
            for family in ("P", "HN", "ADV", "W", "CTRL")
        },
    }
    # Every record is kept so the whole run is inspectable, but the per-trace
    # `details` blob (which repeats the full metaphone/soundex/normalized key sets
    # for both sides of every comparison) is dropped here: it is ~10x the size of
    # everything else combined, and the three factor scores the traces are actually
    # read for - phonetic_similarity, context_score, evidence_confidence - are
    # top-level fields that survive. Failing cases additionally keep their traces
    # in `failures` above.
    for record in records:
        for trace in record["traces"]:
            trace.pop("details", None)
    results["all_records"] = records
    return results


def _measure_scaling(db: Session, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Latency against the two axes that actually grow in deployment: how many terms
    the user has taught, and how long a single dictation is. Temporarily toggles
    is_active to simulate smaller banks, then restores every memory.
    """
    probe_sentences = [c["asr_input"] for c in cases if c["family"] == "CTRL"][:60]

    def probe(processor):
        latencies = []
        for sentence in probe_sentences:
            started_at = time.perf_counter()
            processor.process(TranscriptProcessRequest(
                asr_output=sentence, formatted_output=None,
                confidence_threshold=DEFAULT_INTERVENTION_THRESHOLD))
            latencies.append((time.perf_counter() - started_at) * 1000)
        latencies.sort()
        return {
            "avg_ms": round(statistics.mean(latencies), 3),
            "p95_ms": round(latencies[int(len(latencies) * 0.95)], 3),
        }

    all_memories = db.query(DBMemory).order_by(DBMemory.id).all()
    original_states = [m.is_active for m in all_memories]
    bank_curve = []
    try:
        for size in (8, 16, 24, 32, 40, 48, len(all_memories)):
            if size > len(all_memories):
                continue
            for index, memory in enumerate(all_memories):
                memory.is_active = index < size
            db.commit()
            bank_curve.append(dict(active_memories=size, **probe(TranscriptProcessor(db))))
    finally:
        for memory, state in zip(all_memories, original_states):
            memory.is_active = state
        db.commit()

    processor = TranscriptProcessor(db)
    words = (
        "can you ask sreyas about the sprint backlog today and also check the "
        "ingestion latency on the analytics dashboard before the regression suite "
        "runs for the release"
    ).split()
    length_curve = []
    for token_count in (10, 25, 50, 100, 200, 400):
        repeated = (words * ((token_count // len(words)) + 1))[:token_count]
        text = " ".join(repeated)
        latencies = []
        for _ in range(10):
            started_at = time.perf_counter()
            processor.process(TranscriptProcessRequest(
                asr_output=text, formatted_output=None,
                confidence_threshold=DEFAULT_INTERVENTION_THRESHOLD))
            latencies.append((time.perf_counter() - started_at) * 1000)
        length_curve.append({
            "tokens": token_count,
            "avg_ms": round(statistics.mean(latencies), 3),
            "max_ms": round(max(latencies), 3),
        })

    return {
        "_note": "find_best_candidate scans every active memory for every candidate span, "
                 "so cost is O(spans x memories) - the two curves multiply.",
        "vs_memory_bank_size": bank_curve,
        "vs_transcript_length": length_curve,
    }
