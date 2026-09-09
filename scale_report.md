# Suite 4/4 - Large-Scale Generalization Report

> 49 entities that appear in NO other data file in this repository and nowhere in the assignment brief, taught live during this run through the same `MemoryEngine` calls a real correction or dictionary import would trigger, then graded across ~694 transcripts. Suites 1 and 2 are small enough that a single case moves the headline by several points and small enough that some behaviours never occur in them at all; two of the three failure modes this project documents were only reachable at this volume. Every case is generated deterministically from `eval/scale_generalization.json`, so nothing here was picked after seeing a result - see `eval/scale_engine.py` for what each family means.

**Generated:** 2026-09-09T16:24:52Z

**Corpus:** 49 entities, 694 transcripts (P=343, HN=7, ADV=26, W=98, CTRL=220)

## Headline (P + HN + ADV + CTRL)

> Every family below whose ground truth is a fact rather than a product decision. The W family is excluded on purpose and reported at the end. **Read the per-family table before this number** - the ADV family is adversarial by construction, so it pulls the blended false-intervention rate well above what ordinary traffic produces.

| Metric | Value |
|---|---|
| Exact Match Accuracy | **89.43%** (533/596) |
| Precision (Useful Interventions) | **94.3%** |
| Recall (Intervention Coverage) | **86.88%** |
| False Intervention Rate | **7.11%** |
| Average Latency | **15.341 ms** |
| P95 Latency | **18.276 ms** |
| Confusion Matrix | TP 298 · FP 18 · TN 235 · FN 45 |

## Per-family results (the table that actually matters)

| Family | What it tests | n | Accuracy | Precision | Recall | False Intervention Rate |
|---|---|---:|---:|---:|---:|---:|
| `P` | Entity meant, context corroborates -> INTERVENE | 343 | 86.88% | 100.0% | 86.88% | n/a |
| `HN` | Similar word in its own real meaning -> DO_NOTHING | 7 | 100.0% | n/a | n/a | 0.0% |
| `ADV` | Ordinary word + the entity's own triggers -> DO_NOTHING | 26 | 30.77% | 0.0% | n/a | 69.23% |
| `CTRL` | Ordinary sentences, no entity at all -> DO_NOTHING | 220 | 100.0% | n/a | n/a | 0.0% |
| `W` | Entity meant, zero corroboration (policy call) | 98 | 71.43% | 0.0% | n/a | 28.57% |

The `W` family is reported both ways and never folded into the headline, because its ground truth is a product decision rather than a fact. Under the shipped policy (stay silent when evidence is weak) it scores **71.43%**. Under the alternative reading (the user said the name, so spell it correctly regardless of context) recall would be **28.57%** (28/98). Averaging the two would hide the choice.

## Generalization vs. recall

| Positive cases | n | Accuracy | What it proves |
|---|---:|---:|---|
| Taught mishearing | 49 | 100.0% | Recall check only - should be near-perfect, and is not evidence of generalization |
| Held-out mishearing (never shown) | 294 | 84.69% | The actual generalization result |

## Breakdown by entity category

| Category | n | Accuracy | Precision | Recall | FIR |
|---|---:|---:|---:|---:|---:|
| control | 220 | 100.0% | n/a | n/a | 0.0% |
| jargon | 49 | 85.71% | 90.7% | 92.86% | 57.14% |
| organization | 22 | 95.45% | 95.45% | 100.0% | 100.0% |
| person | 211 | 81.52% | 94.86% | 84.69% | 60.0% |
| place | 21 | 100.0% | 100.0% | 100.0% | n/a |
| product | 73 | 78.08% | 92.73% | 80.95% | 40.0% |

## Breakdown by how the entity was taught

| Teaching path | n | Accuracy | Precision | Recall | FIR |
|---|---:|---:|---:|---:|---:|
| correction | 232 | 83.19% | 95.41% | 86.18% | 60.0% |
| dictionary | 144 | 83.33% | 92.5% | 88.1% | 50.0% |
| n/a | 220 | 100.0% | n/a | n/a | 0.0% |

## Cross-entity interference

> Suite 1 replayed unchanged before and after loading 49 new entities. This is the question a growing memory bank raises that a fixed 16-case suite cannot answer on its own: does remembering more terms start breaking the terms already remembered?

| | Memory bank | Accuracy | Precision | Recall | FIR | Avg latency | P95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Before | 10 | 100.0% | 100.0% | 100.0% | 0.0% | 2.9 ms | 4.22 ms |
| After | 59 | 100.0% | 100.0% | 100.0% | 0.0% | 15.03 ms | 21.8 ms |

**Newly failing cases: 0** - no regressions.

## Negative-evidence adaptation loop

> Every false intervention above is reverted through `learn_negative_correction`, exactly as a user undoing a wrong substitution would. Both halves are then re-measured. Reporting only the first half is how the trigger-poisoning defect described in README 4.7 stayed invisible: it fixed 100% of the false positives while silently taking every true positive for those same entities to zero.

**Reverts applied:** 18 across 18 entities

| Measurement | Before reverts | After reverts |
|---|---:|---:|
| Negatives (HN+ADV) accuracy | 45.45% | **100.0%** |
| Negatives (HN+ADV) false intervention rate | 54.55% | **0.0%** |
| Positives for those same entities | 85.71% | **82.54%** |

Suppression cost **3.17 pp** of true-positive accuracy on the affected entities. That number is the point of this section: it is the price of the adaptation loop, and it is only visible because both halves are measured.

## Sensitivity at scale

> `eval/ablation.py`'s method applied to **596 graded cases** instead of ~20. Re-derives gating decisions only (not replacement text), and only over spans already treated as candidates at the shipped configuration - same stated scope as that module. This does not replace suite 3; it is the same question asked with more data.

| Threshold | Decision accuracy | Precision | Recall | FIR | TP | FP | TN | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.55 | 86.24% | 88.27% | 87.76% | 15.81% | 301 | 40 | 213 | 42 |
| 0.60 | 89.43% | 94.3% | 86.88% | 7.11% | 298 | 18 | 235 | 45 |
| 0.65 **<- shipped** | 89.43% | 94.3% | 86.88% | 7.11% | 298 | 18 | 235 | 45 |
| 0.70 | 88.59% | 94.5% | 85.13% | 6.72% | 292 | 17 | 236 | 51 |
| 0.75 | 88.26% | 97.56% | 81.63% | 2.77% | 280 | 7 | 246 | 63 |
| 0.80 | 83.39% | 99.19% | 71.72% | 0.79% | 246 | 2 | 251 | 97 |
| 0.85 | 66.28% | 100.0% | 41.4% | 0.0% | 142 | 0 | 253 | 201 |
| 0.90 | 44.8% | 100.0% | 4.08% | 0.0% | 14 | 0 | 253 | 329 |

| Weighting (phonetic/context/confidence) | Decision accuracy | Precision | Recall | FIR |
|---|---:|---:|---:|---:|
| shipped_default (0.45/0.3/0.25) | 89.43% | 94.3% | 86.88% | 7.11% |
| phonetic_only (1.0/0.0/0.0) | 86.24% | 88.96% | 86.88% | 14.62% |
| phonetic_heavy (0.7/0.2/0.1) | 88.93% | 94.25% | 86.01% | 7.11% |
| context_heavy (0.3/0.5/0.2) | 88.42% | 94.19% | 85.13% | 7.11% |
| confidence_heavy (0.3/0.2/0.5) | 86.58% | 88.12% | 88.63% | 16.21% |
| equal_thirds (0.34/0.33/0.33) | 89.43% | 94.3% | 86.88% | 7.11% |
| no_confidence_term (0.6/0.4/0.0) | 88.76% | 94.81% | 85.13% | 6.32% |

## Scaling

> `find_best_candidate` scans every active memory for every candidate span, with no phonetic index or blocking key, so cost is O(spans x memories) and the two curves multiply. Both axes grow in real deployment.

| Active memories | Avg latency | P95 |
|---:|---:|---:|
| 8 | 2.522 ms | 3.721 ms |
| 16 | 4.636 ms | 5.775 ms |
| 24 | 6.576 ms | 7.68 ms |
| 32 | 8.72 ms | 10.527 ms |
| 40 | 10.765 ms | 12.514 ms |
| 48 | 12.769 ms | 14.852 ms |
| 59 | 15.883 ms | 18.341 ms |

| Transcript tokens (at 59 memories) | Avg latency | Max |
|---:|---:|---:|
| 10 | 16.011 ms | 16.701 ms |
| 25 | 38.033 ms | 39.714 ms |
| 50 | 76.222 ms | 78.001 ms |
| 100 | 151.691 ms | 154.933 ms |
| 200 | 300.299 ms | 310.597 ms |
| 400 | 603.893 ms | 645.211 ms |

## Teaching cost

49 entities taught live; memory bank 10 -> 59. Avg 5.3 ms, p95 7.347 ms, max 8.324 ms per entity. Measured separately from inference so database writes are never confused with decision latency.

## Every failing case (63)

> Listed in full rather than summarized. A failure that intervened with the WRONG text is a materially different product outcome from one that stayed silent, so the decision column is the first thing to read.

| Case | Family | Expected | Actual decision | Output |
|---|---|---|---|---|
| `P-Siobhan-00` | P | `INTERVENE` | `DO_NOTHING` | `Can you ask shavon about the hiring panel today.` |
| `P-Siobhan-01` | P | `INTERVENE` | `DO_NOTHING` | `I will loop in shavon on the hiring and the panel.` |
| `P-Siobhan-02` | P | `INTERVENE` | `DO_NOTHING` | `Shavon said the hiring panel is ready for review.` |
| `P-Niamh-00` | P | `INTERVENE` | `DO_NOTHING` | `Can you ask neev about the localization strings today.` |
| `P-Niamh-01` | P | `INTERVENE` | `DO_NOTHING` | `I will loop in neev on the localization and the strings.` |
| `P-Niamh-02` | P | `INTERVENE` | `DO_NOTHING` | `Neev said the localization strings is ready for review.` |
| `P-Niamh-10` | P | `INTERVENE` | `DO_NOTHING` | `Can you ask niav about the localization strings today.` |
| `P-Niamh-11` | P | `INTERVENE` | `DO_NOTHING` | `I will loop in niav on the localization and the strings.` |
| `P-Niamh-12` | P | `INTERVENE` | `DO_NOTHING` | `Niav said the localization strings is ready for review.` |
| `P-Caoimhe-00` | P | `INTERVENE` | `DO_NOTHING` | `Can you ask kweeva about the accessibility checks today.` |
| `P-Caoimhe-01` | P | `INTERVENE` | `DO_NOTHING` | `I will loop in kweeva on the accessibility and the checks.` |
| `P-Caoimhe-02` | P | `INTERVENE` | `DO_NOTHING` | `Kweeva said the accessibility checks is ready for review.` |
| `P-Caoimhe-10` | P | `INTERVENE` | `DO_NOTHING` | `Can you ask keevah about the accessibility checks today.` |
| `P-Caoimhe-11` | P | `INTERVENE` | `DO_NOTHING` | `I will loop in keevah on the accessibility and the checks.` |
| `P-Caoimhe-12` | P | `INTERVENE` | `DO_NOTHING` | `Keevah said the accessibility checks is ready for review.` |
| `P-Xavier-00` | P | `INTERVENE` | `DO_NOTHING` | `Can you ask exavier about the platform runtime today.` |
| `P-Xavier-01` | P | `INTERVENE` | `DO_NOTHING` | `I will loop in exavier on the platform and the runtime.` |
| `P-Xavier-02` | P | `INTERVENE` | `DO_NOTHING` | `Exavier said the platform runtime is ready for review.` |
| `P-Aoife-00` | P | `INTERVENE` | `DO_NOTHING` | `Can you ask eefah about the compliance report today.` |
| `P-Aoife-01` | P | `INTERVENE` | `DO_NOTHING` | `I will loop in eefah on the compliance and the report.` |
| `P-Aoife-02` | P | `INTERVENE` | `DO_NOTHING` | `Eefah said the compliance report is ready for review.` |
| `P-Aoife-10` | P | `INTERVENE` | `DO_NOTHING` | `Can you ask eepha about the compliance report today.` |
| `P-Aoife-11` | P | `INTERVENE` | `DO_NOTHING` | `I will loop in eepha on the compliance and the report.` |
| `P-Aoife-12` | P | `INTERVENE` | `DO_NOTHING` | `Eepha said the compliance report is ready for review.` |
| `P-Thibault-00` | P | `INTERVENE` | `DO_NOTHING` | `Can you ask tibo about the billing ledger today.` |
| `P-Thibault-01` | P | `INTERVENE` | `DO_NOTHING` | `I will loop in tibo on the billing and the ledger.` |
| `P-Thibault-02` | P | `INTERVENE` | `DO_NOTHING` | `Tibo said the billing ledger is ready for review.` |
| `P-Thibault-10` | P | `INTERVENE` | `DO_NOTHING` | `Can you ask thibo about the billing ledger today.` |
| `P-Thibault-11` | P | `INTERVENE` | `DO_NOTHING` | `I will loop in thibo on the billing and the ledger.` |
| `P-Thibault-12` | P | `INTERVENE` | `DO_NOTHING` | `Thibo said the billing ledger is ready for review.` |
| `P-Redpanda-10` | P | `INTERVENE` | `DO_NOTHING` | `Can you check the streaming topic on red pander today.` |
| `P-Redpanda-11` | P | `INTERVENE` | `DO_NOTHING` | `We moved the streaming and the topic over to red pander.` |
| `P-Redpanda-12` | P | `INTERVENE` | `DO_NOTHING` | `Red pander is blocking the streaming topic work.` |
| `P-Clickhouse-00` | P | `INTERVENE` | `DO_NOTHING` | `Can you check the olap query on clik house today.` |
| `P-Clickhouse-01` | P | `INTERVENE` | `DO_NOTHING` | `We moved the olap and the query over to clik house.` |
| `P-Clickhouse-02` | P | `INTERVENE` | `DO_NOTHING` | `Clik house is blocking the olap query work.` |
| `P-Weaviate-00` | P | `INTERVENE` | `DO_NOTHING` | `Can you check the vector embeddings on way viate today.` |
| `P-Weaviate-01` | P | `INTERVENE` | `DO_NOTHING` | `We moved the vector and the embeddings over to way viate.` |
| `P-Weaviate-02` | P | `INTERVENE` | `DO_NOTHING` | `Way viate is blocking the vector embeddings work.` |
| `P-Airbyte-10` | P | `INTERVENE` | `DO_NOTHING` | `Can you check the connector sync on air byte today.` |
| `P-Airbyte-11` | P | `INTERVENE` | `DO_NOTHING` | `We moved the connector and the sync over to air byte.` |
| `P-Airbyte-12` | P | `INTERVENE` | `DO_NOTHING` | `Air byte is blocking the connector sync work.` |
| `P-Terraform-00` | P | `INTERVENE` | `DO_NOTHING` | `Can you check the provision state on tera form today.` |
| `P-Terraform-01` | P | `INTERVENE` | `DO_NOTHING` | `We moved the provision and the state over to tera form.` |
| `P-Terraform-02` | P | `INTERVENE` | `DO_NOTHING` | `Tera form is blocking the provision state work.` |
| `ADV-Temporal` | ADV | `DO_NOTHING` | `INTERVENE` | `The workflow used a Temporal worker to retry the job.` |
| `ADV-Ansible` | ADV | `DO_NOTHING` | `INTERVENE` | `The playbook has a Ansible default for every inventory task.` |
| `ADV-Terraform` | ADV | `DO_NOTHING` | `INTERVENE` | `We Terraform the state before we apply the provision plan.` |
| `ADV-Weaviate` | ADV | `DO_NOTHING` | `INTERVENE` | `The vector embeddings Weaviate from the schema we agreed on.` |
| `ADV-Deno` | ADV | `DO_NOTHING` | `INTERVENE` | `The runtime permissions Deno a typescript module boundary.` |
| `ADV-Sentry` | ADV | `DO_NOTHING` | `INTERVENE` | `The errors in monitoring go back almost a Sentry of releases.` |
| `ADV-Clickhouse` | ADV | `DO_NOTHING` | `INTERVENE` | `We ran the olap query from the Clickhouse over a shared shard.` |
| `ADV-Jaeger` | ADV | `DO_NOTHING` | `INTERVENE` | `The distributed tracing sampler is Jaeger about every span.` |
| `ADV-Mikhail` | ADV | `DO_NOTHING` | `INTERVENE` | `Mikhail patched the kernel driver last night.` |
| `ADV-Kritika` | ADV | `DO_NOTHING` | `INTERVENE` | `The support tickets flagged a Kritika bug this morning.` |
| `ADV-Gaurav` | ADV | `DO_NOTHING` | `INTERVENE` | `The security audit turned up a Gaurav issue in production.` |
| `ADV-Devika` | ADV | `DO_NOTHING` | `INTERVENE` | `The marketing campaign targets every Devika we support.` |
| `ADV-Shreyas` | ADV | `DO_NOTHING` | `INTERVENE` | `The sprint backlog was torn to Shreyas in planning.` |
| `ADV-Harshita` | ADV | `DO_NOTHING` | `INTERVENE` | `The recruiting interviews got Harshita feedback from the panel.` |
| `ADV-Niamh` | ADV | `DO_NOTHING` | `INTERVENE` | `The localization strings still need a Niamh for the key.` |
| `ADV-Xavier` | ADV | `DO_NOTHING` | `INTERVENE` | `The platform runtime patch was a Xavier for the release.` |
| `ADV-Zomato` | ADV | `DO_NOTHING` | `INTERVENE` | `The delivery partner order had Zomato soup in it.` |
| `ADV-Rakesh` | ADV | `DO_NOTHING` | `INTERVENE` | `The warehouse logistics crew packed tennis Rakesh today.` |

### Failing case traces

#### P-Siobhan-00
- ASR Input: `can you ask shavon about the hiring panel today`
- Expected: `Can you ask Siobhan about the hiring panel today.`
- Actual: `Can you ask shavon about the hiring panel today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Siobhan-01
- ASR Input: `i will loop in shavon on the hiring and the panel`
- Expected: `I will loop in Siobhan on the hiring and the panel.`
- Actual: `I will loop in shavon on the hiring and the panel.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Siobhan-02
- ASR Input: `shavon said the hiring panel is ready for review`
- Expected: `Siobhan said the hiring panel is ready for review.`
- Actual: `Shavon said the hiring panel is ready for review.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Niamh-00
- ASR Input: `can you ask neev about the localization strings today`
- Expected: `Can you ask Niamh about the localization strings today.`
- Actual: `Can you ask neev about the localization strings today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Niamh-01
- ASR Input: `i will loop in neev on the localization and the strings`
- Expected: `I will loop in Niamh on the localization and the strings.`
- Actual: `I will loop in neev on the localization and the strings.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Niamh-02
- ASR Input: `neev said the localization strings is ready for review`
- Expected: `Niamh said the localization strings is ready for review.`
- Actual: `Neev said the localization strings is ready for review.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Niamh-10
- ASR Input: `can you ask niav about the localization strings today`
- Expected: `Can you ask Niamh about the localization strings today.`
- Actual: `Can you ask niav about the localization strings today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Niamh-11
- ASR Input: `i will loop in niav on the localization and the strings`
- Expected: `I will loop in Niamh on the localization and the strings.`
- Actual: `I will loop in niav on the localization and the strings.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Niamh-12
- ASR Input: `niav said the localization strings is ready for review`
- Expected: `Niamh said the localization strings is ready for review.`
- Actual: `Niav said the localization strings is ready for review.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Caoimhe-00
- ASR Input: `can you ask kweeva about the accessibility checks today`
- Expected: `Can you ask Caoimhe about the accessibility checks today.`
- Actual: `Can you ask kweeva about the accessibility checks today.`
  - Span `kweeva` -> `Kivi` | `SUPPRESSED` | phon=0.6378 ctx=0.0 conf=0.98 composite=0.532

#### P-Caoimhe-01
- ASR Input: `i will loop in kweeva on the accessibility and the checks`
- Expected: `I will loop in Caoimhe on the accessibility and the checks.`
- Actual: `I will loop in kweeva on the accessibility and the checks.`
  - Span `kweeva` -> `Kivi` | `SUPPRESSED` | phon=0.6378 ctx=0.0 conf=0.98 composite=0.532

#### P-Caoimhe-02
- ASR Input: `kweeva said the accessibility checks is ready for review`
- Expected: `Caoimhe said the accessibility checks is ready for review.`
- Actual: `Kweeva said the accessibility checks is ready for review.`
  - Span `Kweeva` -> `Kivi` | `SUPPRESSED` | phon=0.6378 ctx=0.0 conf=0.98 composite=0.532

#### P-Caoimhe-10
- ASR Input: `can you ask keevah about the accessibility checks today`
- Expected: `Can you ask Caoimhe about the accessibility checks today.`
- Actual: `Can you ask keevah about the accessibility checks today.`
  - Span `keevah` -> `Kivi` | `SUPPRESSED` | phon=0.7544 ctx=0.0 conf=0.98 composite=0.5845

#### P-Caoimhe-11
- ASR Input: `i will loop in keevah on the accessibility and the checks`
- Expected: `I will loop in Caoimhe on the accessibility and the checks.`
- Actual: `I will loop in keevah on the accessibility and the checks.`
  - Span `keevah` -> `Kivi` | `SUPPRESSED` | phon=0.7544 ctx=0.0 conf=0.98 composite=0.5845

#### P-Caoimhe-12
- ASR Input: `keevah said the accessibility checks is ready for review`
- Expected: `Caoimhe said the accessibility checks is ready for review.`
- Actual: `Keevah said the accessibility checks is ready for review.`
  - Span `Keevah` -> `Kivi` | `SUPPRESSED` | phon=0.7544 ctx=0.0 conf=0.98 composite=0.5845

#### P-Xavier-00
- ASR Input: `can you ask exavier about the platform runtime today`
- Expected: `Can you ask Xavier about the platform runtime today.`
- Actual: `Can you ask exavier about the platform runtime today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Xavier-01
- ASR Input: `i will loop in exavier on the platform and the runtime`
- Expected: `I will loop in Xavier on the platform and the runtime.`
- Actual: `I will loop in exavier on the platform and the runtime.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Xavier-02
- ASR Input: `exavier said the platform runtime is ready for review`
- Expected: `Xavier said the platform runtime is ready for review.`
- Actual: `Exavier said the platform runtime is ready for review.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Aoife-00
- ASR Input: `can you ask eefah about the compliance report today`
- Expected: `Can you ask Aoife about the compliance report today.`
- Actual: `Can you ask eefah about the compliance report today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Aoife-01
- ASR Input: `i will loop in eefah on the compliance and the report`
- Expected: `I will loop in Aoife on the compliance and the report.`
- Actual: `I will loop in eefah on the compliance and the report.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Aoife-02
- ASR Input: `eefah said the compliance report is ready for review`
- Expected: `Aoife said the compliance report is ready for review.`
- Actual: `Eefah said the compliance report is ready for review.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Aoife-10
- ASR Input: `can you ask eepha about the compliance report today`
- Expected: `Can you ask Aoife about the compliance report today.`
- Actual: `Can you ask eepha about the compliance report today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Aoife-11
- ASR Input: `i will loop in eepha on the compliance and the report`
- Expected: `I will loop in Aoife on the compliance and the report.`
- Actual: `I will loop in eepha on the compliance and the report.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Aoife-12
- ASR Input: `eepha said the compliance report is ready for review`
- Expected: `Aoife said the compliance report is ready for review.`
- Actual: `Eepha said the compliance report is ready for review.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Thibault-00
- ASR Input: `can you ask tibo about the billing ledger today`
- Expected: `Can you ask Thibault about the billing ledger today.`
- Actual: `Can you ask tibo about the billing ledger today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Thibault-01
- ASR Input: `i will loop in tibo on the billing and the ledger`
- Expected: `I will loop in Thibault on the billing and the ledger.`
- Actual: `I will loop in tibo on the billing and the ledger.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Thibault-02
- ASR Input: `tibo said the billing ledger is ready for review`
- Expected: `Thibault said the billing ledger is ready for review.`
- Actual: `Tibo said the billing ledger is ready for review.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Thibault-10
- ASR Input: `can you ask thibo about the billing ledger today`
- Expected: `Can you ask Thibault about the billing ledger today.`
- Actual: `Can you ask thibo about the billing ledger today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Thibault-11
- ASR Input: `i will loop in thibo on the billing and the ledger`
- Expected: `I will loop in Thibault on the billing and the ledger.`
- Actual: `I will loop in thibo on the billing and the ledger.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Thibault-12
- ASR Input: `thibo said the billing ledger is ready for review`
- Expected: `Thibault said the billing ledger is ready for review.`
- Actual: `Thibo said the billing ledger is ready for review.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Redpanda-10
- ASR Input: `can you check the streaming topic on red pander today`
- Expected: `Can you check the streaming topic on Redpanda today.`
- Actual: `Can you check the streaming topic on red pander today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Redpanda-11
- ASR Input: `we moved the streaming and the topic over to red pander`
- Expected: `We moved the streaming and the topic over to Redpanda.`
- Actual: `We moved the streaming and the topic over to red pander.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Redpanda-12
- ASR Input: `red pander is blocking the streaming topic work`
- Expected: `Redpanda is blocking the streaming topic work.`
- Actual: `Red pander is blocking the streaming topic work.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Clickhouse-00
- ASR Input: `can you check the olap query on clik house today`
- Expected: `Can you check the olap query on Clickhouse today.`
- Actual: `Can you check the olap query on clik house today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Clickhouse-01
- ASR Input: `we moved the olap and the query over to clik house`
- Expected: `We moved the olap and the query over to Clickhouse.`
- Actual: `We moved the olap and the query over to clik house.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Clickhouse-02
- ASR Input: `clik house is blocking the olap query work`
- Expected: `Clickhouse is blocking the olap query work.`
- Actual: `Clik house is blocking the olap query work.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Weaviate-00
- ASR Input: `can you check the vector embeddings on way viate today`
- Expected: `Can you check the vector embeddings on Weaviate today.`
- Actual: `Can you check the vector embeddings on way viate today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Weaviate-01
- ASR Input: `we moved the vector and the embeddings over to way viate`
- Expected: `We moved the vector and the embeddings over to Weaviate.`
- Actual: `We moved the vector and the embeddings over to way viate.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Weaviate-02
- ASR Input: `way viate is blocking the vector embeddings work`
- Expected: `Weaviate is blocking the vector embeddings work.`
- Actual: `Way viate is blocking the vector embeddings work.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Airbyte-10
- ASR Input: `can you check the connector sync on air byte today`
- Expected: `Can you check the connector sync on Airbyte today.`
- Actual: `Can you check the connector sync on air byte today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Airbyte-11
- ASR Input: `we moved the connector and the sync over to air byte`
- Expected: `We moved the connector and the sync over to Airbyte.`
- Actual: `We moved the connector and the sync over to air byte.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Airbyte-12
- ASR Input: `air byte is blocking the connector sync work`
- Expected: `Airbyte is blocking the connector sync work.`
- Actual: `Air byte is blocking the connector sync work.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Terraform-00
- ASR Input: `can you check the provision state on tera form today`
- Expected: `Can you check the provision state on Terraform today.`
- Actual: `Can you check the provision state on tera form today.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Terraform-01
- ASR Input: `we moved the provision and the state over to tera form`
- Expected: `We moved the provision and the state over to Terraform.`
- Actual: `We moved the provision and the state over to tera form.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### P-Terraform-02
- ASR Input: `tera form is blocking the provision state work`
- Expected: `Terraform is blocking the provision state work.`
- Actual: `Tera form is blocking the provision state work.`
  - *No candidate was considered at all (phonetic similarity below MIN_PHONETIC_SIMILARITY), so the composite score never ran.*

#### ADV-Temporal
- ASR Input: `the workflow used a temporary worker to retry the job`
- Expected: `The workflow used a temporary worker to retry the job.`
- Actual: `The workflow used a Temporal worker to retry the job.`
  - Span `temporary` -> `Temporal` | `INTERVENED` | phon=0.8691 ctx=0.68 conf=0.9 composite=0.8201

#### ADV-Ansible
- ASR Input: `the playbook has a sensible default for every inventory task`
- Expected: `The playbook has a sensible default for every inventory task.`
- Actual: `The playbook has a Ansible default for every inventory task.`
  - Span `sensible` -> `Ansible` | `INTERVENED` | phon=0.6788 ctx=0.68 conf=0.9 composite=0.7345

#### ADV-Terraform
- ASR Input: `we transform the state before we apply the provision plan`
- Expected: `We transform the state before we apply the provision plan.`
- Actual: `We Terraform the state before we apply the provision plan.`
  - Span `transform` -> `Terraform` | `INTERVENED` | phon=0.6527 ctx=0.84 conf=0.9 composite=0.7707

#### ADV-Weaviate
- ASR Input: `the vector embeddings deviate from the schema we agreed on`
- Expected: `The vector embeddings deviate from the schema we agreed on.`
- Actual: `The vector embeddings Weaviate from the schema we agreed on.`
  - Span `deviate` -> `Weaviate` | `INTERVENED` | phon=0.6522 ctx=0.68 conf=0.9 composite=0.7225

#### ADV-Deno
- ASR Input: `the runtime permissions denote a typescript module boundary`
- Expected: `The runtime permissions denote a typescript module boundary.`
- Actual: `The runtime permissions Deno a typescript module boundary.`
  - Span `denote` -> `Deno` | `INTERVENED` | phon=0.6667 ctx=0.84 conf=0.9 composite=0.777

#### ADV-Sentry
- ASR Input: `the errors in monitoring go back almost a century of releases`
- Expected: `The errors in monitoring go back almost a century of releases.`
- Actual: `The errors in monitoring go back almost a Sentry of releases.`
  - Span `century` -> `Sentry` | `INTERVENED` | phon=0.7063 ctx=0.52 conf=0.9 composite=0.6988

#### ADV-Clickhouse
- ASR Input: `we ran the olap query from the clubhouse over a shared shard`
- Expected: `We ran the olap query from the clubhouse over a shared shard.`
- Actual: `We ran the olap query from the Clickhouse over a shared shard.`
  - Span `clubhouse` -> `Clickhouse` | `INTERVENED` | phon=0.6574 ctx=0.68 conf=0.9 composite=0.7248

#### ADV-Jaeger
- ASR Input: `the distributed tracing sampler is eager about every span`
- Expected: `The distributed tracing sampler is eager about every span.`
- Actual: `The distributed tracing sampler is Jaeger about every span.`
  - Span `eager` -> `Jaeger` | `INTERVENED` | phon=0.6211 ctx=0.68 conf=0.9 composite=0.7085

#### ADV-Mikhail
- ASR Input: `michael patched the kernel driver last night`
- Expected: `Michael patched the kernel driver last night.`
- Actual: `Mikhail patched the kernel driver last night.`
  - Span `Michael` -> `Mikhail` | `INTERVENED` | phon=0.7312 ctx=1.0 conf=0.88 composite=0.849

#### ADV-Kritika
- ASR Input: `the support tickets flagged a critical bug this morning`
- Expected: `The support tickets flagged a critical bug this morning.`
- Actual: `The support tickets flagged a Kritika bug this morning.`
  - Span `critical` -> `Kritika` | `INTERVENED` | phon=0.6472 ctx=0.733 conf=0.88 composite=0.7311

#### ADV-Gaurav
- ASR Input: `the security audit turned up a grave issue in production`
- Expected: `The security audit turned up a grave issue in production.`
- Actual: `The security audit turned up a Gaurav issue in production.`
  - Span `audit` -> `Aaditya` | `SUPPRESSED` | phon=0.63 ctx=0.0 conf=0.95 composite=0.521
  - Span `grave` -> `Gaurav` | `INTERVENED` | phon=0.7515 ctx=0.733 conf=0.88 composite=0.7781

#### ADV-Devika
- ASR Input: `the marketing campaign targets every device we support`
- Expected: `The marketing campaign targets every device we support.`
- Actual: `The marketing campaign targets every Devika we support.`
  - Span `device` -> `Devika` | `INTERVENED` | phon=0.7833 ctx=0.733 conf=0.88 composite=0.7924

#### ADV-Shreyas
- ASR Input: `the sprint backlog was torn to shreds in planning`
- Expected: `The sprint backlog was torn to shreds in planning.`
- Actual: `The sprint backlog was torn to Shreyas in planning.`
  - Span `shreds` -> `Shreyas` | `INTERVENED` | phon=0.6557 ctx=0.733 conf=0.88 composite=0.735

#### ADV-Harshita
- ASR Input: `the recruiting interviews got harsh feedback from the panel`
- Expected: `The recruiting interviews got harsh feedback from the panel.`
- Actual: `The recruiting interviews got Harshita feedback from the panel.`
  - Span `harsh` -> `Harshita` | `INTERVENED` | phon=0.6375 ctx=0.733 conf=0.88 composite=0.7268

#### ADV-Niamh
- ASR Input: `the localization strings still need a name for the key`
- Expected: `The localization strings still need a name for the key.`
- Actual: `The localization strings still need a Niamh for the key.`
  - Span `name` -> `Niamh` | `INTERVENED` | phon=0.7738 ctx=0.733 conf=0.88 composite=0.7881

#### ADV-Xavier
- ASR Input: `the platform runtime patch was a savior for the release`
- Expected: `The platform runtime patch was a savior for the release.`
- Actual: `The platform runtime patch was a Xavier for the release.`
  - Span `savior` -> `Xavier` | `INTERVENED` | phon=0.6778 ctx=0.733 conf=0.88 composite=0.7449

#### ADV-Zomato
- ASR Input: `the delivery partner order had tomato soup in it`
- Expected: `The delivery partner order had tomato soup in it.`
- Actual: `The delivery partner order had Zomato soup in it.`
  - Span `tomato` -> `Zomato` | `INTERVENED` | phon=0.6972 ctx=0.68 conf=0.9 composite=0.7427

#### ADV-Rakesh
- ASR Input: `the warehouse logistics crew packed tennis rackets today`
- Expected: `The warehouse logistics crew packed tennis rackets today.`
- Actual: `The warehouse logistics crew packed tennis Rakesh today.`
  - Span `rackets` -> `Rakesh` | `INTERVENED` | phon=0.6284 ctx=0.733 conf=0.88 composite=0.7227
