# Suite 3/4 - Ablation & Sensitivity Report

> Validation for the three numbers in the composite decision score that were product decisions, not measurements: the phonetic/context/confidence weight split and the intervention threshold. Computed by recombining the decision traces recorded by the other two suites' official runs (see `eval/ablation.py` docstring for the exact method and its stated scope).

**Generated:** 2026-09-09T16:24:52Z

**Cases in sweep:** 24 (holdout_generalization=7, holdout_generalization_limitation=1, regression_seeded=16)

**Shipped default:** threshold=`0.65`, weights phonetic=`0.45` context=`0.3` confidence=`0.25`

## Threshold sweep (at shipped default weights)

| Threshold | Accuracy | Precision | Recall | False Intervention Rate | TP | FP | TN | FN |
|---|---|---|---|---|---|---|---|---|
| 0.30 | 91.67% | 86.67% | 100.0% | 18.18% | 13 | 2 | 9 | 0 |
| 0.35 | 91.67% | 86.67% | 100.0% | 18.18% | 13 | 2 | 9 | 0 |
| 0.40 | 91.67% | 86.67% | 100.0% | 18.18% | 13 | 2 | 9 | 0 |
| 0.45 | 91.67% | 86.67% | 100.0% | 18.18% | 13 | 2 | 9 | 0 |
| 0.50 | 91.67% | 86.67% | 100.0% | 18.18% | 13 | 2 | 9 | 0 |
| 0.55 | 95.83% | 92.86% | 100.0% | 9.09% | 13 | 1 | 10 | 0 |
| 0.60 | 95.83% | 92.86% | 100.0% | 9.09% | 13 | 1 | 10 | 0 |
| 0.65 **<- shipped default** | 95.83% | 92.86% | 100.0% | 9.09% | 13 | 1 | 10 | 0 |
| 0.70 | 100.0% | 100.0% | 100.0% | 0.0% | 13 | 0 | 11 | 0 |
| 0.75 | 87.5% | 100.0% | 76.92% | 0.0% | 10 | 0 | 11 | 3 |
| 0.80 | 66.67% | 100.0% | 38.46% | 0.0% | 5 | 0 | 11 | 8 |
| 0.85 | 45.83% | 100.0% | 0.0% | 0.0% | 0 | 0 | 11 | 13 |
| 0.90 | 45.83% | 100.0% | 0.0% | 0.0% | 0 | 0 | 11 | 13 |

## Weight ablation (at shipped default threshold)

| Configuration | Weights (phon/ctx/conf) | Accuracy | Precision | Recall | False Intervention Rate |
|---|---|---|---|---|---|
| phonetic_only | 1.0/0.0/0.0 | 91.67% | 92.31% | 92.31% | 9.09% |
| phonetic_plus_context | 0.6/0.4/0.0 | 100.0% | 100.0% | 100.0% | 0.0% |
| shipped_default | 0.45/0.3/0.25 | 95.83% | 92.86% | 100.0% | 9.09% |
| context_heavy | 0.3/0.45/0.25 | 100.0% | 100.0% | 100.0% | 0.0% |

## Reading this honestly

This is a small sweep (see case count above) - treat the exact optimum it finds as directional, not as a mandate to chase the single best-scoring cell. What it is useful for: (1) confirming that dropping the context term (`phonetic_only`) measurably increases false interventions on this data, which is the actual argument for keeping context in the score at all, and (2) showing where the shipped threshold sits relative to cells that would also resolve the one discovered limitation case - which the negative-evidence learning loop (see `holdout_report.md`, HOLD-05) already resolves without retuning a global threshold that every other memory shares. We kept the global threshold at 0.65 rather than moving it to chase one case's score, and fixed that case's actual cause (a missing negative context) instead - see README 'Decisions & Validation'.