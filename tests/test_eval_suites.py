"""
Regression tests for the evaluation suites themselves (eval/eval_engine.py,
eval/holdout_engine.py, eval/ablation.py). These are as much a part of the product
as the memory engine - if they silently broke, the numbers in README/EVALUATION_SUMMARY.md
would be wrong without anyone noticing, which is exactly what the brief warns a
"strong-looking result supported by a weak evaluation" looks like from the outside.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models import Base
from db.seed_data import seed_database
from eval.eval_engine import run_evaluation
from eval.holdout_engine import run_holdout_suite
from eval.ablation import run_ablation_study


@pytest.fixture
def seeded_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    seed_database(session)
    yield session
    session.close()


def test_regression_suite_passes_fully_on_its_own_seed_data(seeded_db):
    # This suite's whole point is to be a regression guard against its own seed
    # data - it should always be 100% right after a fresh reset+seed, by construction.
    summary = run_evaluation(seeded_db, save_to_db=False)
    assert summary["total_cases"] >= 16
    assert summary["accuracy_pct"] == 100.0
    assert summary["false_intervention_rate_pct"] == 0.0
    assert all("relevant_memory_state" in case for case in summary["cases"])
    assert all(
        case["relevant_memory_state"]["active_memory_count"] > 0
        for case in summary["cases"]
    )


def test_holdout_suite_entities_are_not_in_seed_data(seeded_db):
    """
    The whole methodological point of the holdout suite is that its entities are
    NOT pre-loaded - this test would catch someone "fixing" a failing holdout case
    by quietly seeding it instead of fixing the generalization.
    """
    from db.seed_data import SEED_ENTRIES
    seeded_terms = {e["canonical_term"].lower() for e in SEED_ENTRIES}

    summary = run_holdout_suite(seeded_db)
    taught_entities = {j["journey"] for j in summary["journeys"]}
    assert taught_entities, "holdout suite taught nothing"

    import json
    from eval.holdout_engine import HOLDOUT_PATH
    with open(HOLDOUT_PATH, encoding="utf-8") as f:
        journeys = json.load(f)
    for j in journeys:
        entity = j.get("entity")
        if entity:
            assert entity.lower() not in seeded_terms, (
                f"holdout entity '{entity}' must not also be in db/seed_data.py - "
                "that would defeat the point of the holdout suite"
            )


def test_holdout_suite_graded_cases_pass_and_limitation_is_labeled(seeded_db):
    summary = run_holdout_suite(seeded_db)
    assert summary["total_graded_cases"] > 0
    assert summary["passed_graded_cases"] == summary["total_graded_cases"], (
        "a graded (non-limitation) holdout case failed - this is a real regression, "
        "not a documented limitation"
    )
    # The known limitation must stay present and labeled, not silently disappear -
    # if this starts failing because the limitation is now fixed for real, update
    # HOLD-04/HOLD-05 in eval/holdout_generalization.json rather than deleting them.
    assert len(summary["limitation_cases"]) == 1
    assert summary["limitation_cases"][0]["case_id"] == "HOLD-04a"
    all_cases = summary["graded_cases"] + summary["limitation_cases"]
    assert all("relevant_memory_state" in case for case in all_cases)
    assert summary["latency"]["inference"]["calls"] == len(all_cases)
    assert summary["latency"]["teaching"]["calls"] == 4


def test_ablation_study_runs_against_recorded_traces(seeded_db):
    regression = run_evaluation(seeded_db, save_to_db=False)
    holdout = run_holdout_suite(seeded_db)
    ablation = run_ablation_study(regression, holdout)

    assert ablation["total_cases_in_sweep"] == (
        regression["total_cases"] + holdout["total_graded_cases"] + len(holdout["limitation_cases"])
    )
    assert len(ablation["threshold_sweep"]) > 1
    # The shipped default must itself be one of the swept configurations, not just
    # described separately - otherwise the "validation" could silently drift from
    # what core/memory_engine.py actually ships.
    from core.memory_engine import DEFAULT_INTERVENTION_THRESHOLD
    assert any(
        abs(row["threshold"] - DEFAULT_INTERVENTION_THRESHOLD) < 1e-9
        for row in ablation["threshold_sweep"]
    )
    assert "shipped_default" in ablation["weight_ablation"]


# ---------------------------------------------------------------------------
# Suite 4: large-scale generalization
# ---------------------------------------------------------------------------

def test_scale_corpus_shares_no_entity_with_the_other_suites():
    """
    The entire value of suite 4 is that its entities are genuinely unseen. If a
    canonical term or alias ever leaks in from db/seed_data.py or the holdout
    corpus, the suite quietly stops measuring generalization and starts measuring
    recall - with no visible symptom. This guards the property directly rather
    than trusting whoever edits the corpus next.
    """
    import json
    from db.seed_data import SEED_ENTRIES
    from eval.holdout_engine import HOLDOUT_PATH
    from eval.scale_engine import SCALE_PATH

    with open(SCALE_PATH, encoding="utf-8") as f:
        corpus = json.load(f)
    with open(HOLDOUT_PATH, encoding="utf-8") as f:
        holdout = json.load(f)

    prior_terms = {e["canonical_term"].lower() for e in SEED_ENTRIES}
    for entry in SEED_ENTRIES:
        prior_terms.update(a.lower() for a in entry["aliases"])
    for journey in holdout:
        if journey.get("entity"):
            prior_terms.add(journey["entity"].lower())
        for step in journey.get("teach", []):
            if step.get("canonical_term"):
                prior_terms.add(step["canonical_term"].lower())
            prior_terms.update(a.lower() for a in step.get("aliases", []))

    for entity in corpus["entities"]:
        scale_terms = {entity["canonical"].lower(), entity["taught_alias"].lower()}
        scale_terms.update(a.lower() for a in entity["holdout_aliases"])
        assert not (scale_terms & prior_terms), (
            f"{entity['canonical']} overlaps an entity the system was already taught "
            f"elsewhere: {scale_terms & prior_terms}"
        )


def test_scale_suite_grades_every_family_separately(seeded_db):
    from eval.scale_engine import run_scale_suite

    summary = run_scale_suite(seeded_db, include_scaling=False)

    # Families must stay separate. Collapsing them into one average is exactly the
    # reporting failure this suite exists to avoid: the adversarial family is a
    # stress test and the control family is ordinary traffic, and they mean
    # opposite things about the product.
    for family in ("P", "HN", "ADV", "CTRL", "W"):
        assert family in summary["by_family"], f"family {family} missing from report"

    # The weak-evidence family must never be folded into the headline.
    assert summary["headline"]["total"] == sum(
        summary["by_family"][f]["total"] for f in ("P", "HN", "ADV", "CTRL")
    )
    assert "ideal_reading" in summary["by_family"]["W"], (
        "the W family must report both the shipped-policy and the alternative reading, "
        "since its ground truth is a product decision rather than a fact"
    )

    # Held-out aliases are the generalization claim; taught aliases are only recall.
    seen = summary["seen_vs_unseen_alias"]
    assert seen["heldout_alias"]["total"] > seen["taught_alias"]["total"]

    assert summary["corpus"]["entities"] == 49
    assert summary["teaching"]["memory_bank_after"] > summary["teaching"]["memory_bank_before"]


def test_scale_suite_measures_both_halves_of_the_adaptation_loop(seeded_db):
    """
    Reverting false positives must be scored on BOTH sides. Measuring only whether
    suppression worked is how the learn_negative_correction trigger-poisoning
    defect (README 4.7) stayed invisible - it fixed every false positive while
    taking the true positives for those same entities to zero.
    """
    from eval.scale_engine import run_scale_suite

    summary = run_scale_suite(seeded_db, include_scaling=False)
    adaptation = summary["adaptation"]

    assert adaptation["reverts_applied"] > 0, (
        "the adversarial family should still provoke false positives at the shipped "
        "threshold - if it does not, this assertion is the early warning that the "
        "corpus stopped being adversarial"
    )
    # Suppression must work...
    assert adaptation["negatives_after"]["false_intervention_rate_pct"] == 0.0
    # ...and it must not have silenced the affected memories entirely.
    positives_after = adaptation["positives_for_affected_entities_after"]
    assert positives_after is not None
    assert positives_after["accuracy_pct"] > 50.0, (
        "reverting a wrong substitution must not disable the memory in the context it "
        "was taught for - see learn_negative_correction's trigger-exclusion filter"
    )


def test_scale_sensitivity_sweep_includes_the_shipped_configuration(seeded_db):
    from core.memory_engine import DEFAULT_INTERVENTION_THRESHOLD
    from eval.scale_engine import run_scale_suite

    summary = run_scale_suite(seeded_db, include_scaling=False)
    sensitivity = summary["sensitivity"]

    assert sensitivity["cases_in_sweep"] == summary["headline"]["total"]
    assert any(
        abs(row["threshold"] - DEFAULT_INTERVENTION_THRESHOLD) < 1e-9
        for row in sensitivity["threshold_sweep"]
    )
    assert "shipped_default" in sensitivity["weight_ablation"]
    # Dropping the context term is the specific claim the score's design rests on,
    # so it must stay in the sweep for that claim to remain checkable.
    assert "phonetic_only" in sensitivity["weight_ablation"]
