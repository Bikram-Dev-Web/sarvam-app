# The Words Kivi Keeps: Word-Level Phonetic Memory System
*A lightweight, durable personal AI memory engine built for Sarvam's Kivi voice companion.*

---

## 1. Executive Summary & Product Vision

Speech recognition models encounter language they cannot predict in advance: colleague names with non-standard spellings, company products, technical jargon, and domain-specific vocabulary. While a standard language model can clean grammar and punctuation, it cannot know the specific person speaking.

**Kivi's Phonetic Memory System** bridges the gap between raw speech recognition and personalized communication. It moves transcripts through three explicit tiers:
1. **ASR Output:** Raw acoustic tokens produced by speech recognition (*e.g., `ask aditya to review the sarvam kiwi service`*).
2. **Formatted Output:** Grammatically cleaned and punctuated text without personal memory (*e.g., `Ask Aditya to review the Sarvam Kiwi service.`*).
3. **Memory-Aware Output:** Fully personalized transcript injected with personal phonetic memory and contextual awareness (*e.g., `Ask Aaditya to review the Sarvam Kivi service.`*).

The brief's own example establishes the three tiers, not the boundaries of the problem. Everything past Section 4 of this README exists because the boundary was narrow but the problem inside it was not: what should Kivi remember, when should it act on that memory, and - just as importantly - **how do we know any of this is actually true, rather than a system that has just memorized its own test cases?**

---

## 2. Core Architecture & System Design

```
+----------------------------------------------------------------------------------------------------+
|                                    KIVI THREE-TIER PIPELINE                                        |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|   1. ASR Output ────────► 2. Formatted Output ────────► 3. Candidate Matching & Disambiguation    |
|   ("ask aditya...")      ("Ask Aditya...")                       │                                 |
|                                                                  ▼                                 |
|                                                     +──────────────────────────+                   |
|                                                     |   Phonetic Index Lookup  |                   |
|                                                     | (Metaphone/Soundex +     |                   |
|                                                     | Indian Phonetic Norm)    |                   |
|                                                     +────────────┬─────────────+                   |
|                                                                  │                                 |
|                                                                  ▼                                 |
|                                                     +──────────────────────────+                   |
|                                                     | Context Affinity Scoring |                   |
|                                                     | (+ Triggers / - Negative)|                   |
|                                                     +────────────┬─────────────+                   |
|                                                                  │                                 |
|                                                                  ▼                                 |
|                                                     +──────────────────────────+                   |
|                                                     | Decision Gating & Trace  |                   |
|                                                     | (Score >= Threshold?)    |                   |
|                                                     +──────┬────────────┬──────+                   |
|                                                            │            │                          |
|                                            [INTERVENE] ────┘            └──── [SUPPRESS]           |
|                                                 │                                  │               |
|                                                 ▼                                  ▼               |
|                                 3. Memory-Aware Output                Preserve Original Spans      |
|                             ("Ask Aaditya to review the                (e.g. "kiwi fruit",         |
|                                Sarvam Kivi service.")                     "kneel on floor")        |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

A fourth path, not shown above because it runs after the pipeline rather than inside it: when a substitution turns out to be wrong, the user reverting it feeds `MemoryEngine.learn_negative_correction`, which adds the sentence's distinguishing context words (everything except that memory's own positive triggers) as `negative_contexts` on the offending memory and applies a confidence penalty - closing the loop from "the system was wrong" back into "the system knows it was wrong here." See §4.7 and `eval/holdout_generalization.json` (journeys HOLD-04/HOLD-05) for this working end to end on a case we found, not one we planned.

### Key Engineering Principles
1. **Dual-Stage Architecture:** Fast phonetic candidate filtering followed by contextual disambiguation and confidence gating.
2. **Negative Space Preservation:** A personal memory system must know when to **deliberately do nothing**. Negative triggers prevent catastrophic false substitutions (e.g. `kiwi fruit` must never become `Kivi`, `kneel down` must never become `Neil`) - and, as of this revision, those triggers no longer have to be hand-authored: they can be *learned* the first time the system gets it wrong (§4.7).
3. **Multi-Source Evidence Accumulation:** Memory learns through explicit user corrections and explicit dictionary imports. (An earlier draft of this system also claimed "conversational frequency reinforcement" as a source; that code path never existed, so the claim has been removed - see §5.)
4. **Complete Inspectability:** Every single token transformation or suppression generates a structured `DecisionTrace` with phonetic similarity, context affinity score, and clear human-readable rationale.

### Configuration vs. hardcoding

The repository contains fixed **bootstrap data** and fixed **decision policy**, but it does not hardcode transcript answers. Seed entries provide a reproducible demonstration persona; evaluation expected outputs are test labels; and the shipped score weights/threshold are centralized policy constants validated by the ablation suite. The matching and learning paths are entity-agnostic: holdout entities are absent from the seed file, taught live through the same correction/dictionary APIs a user invokes, and then tested on unseen sentences. In production, each user's durable memory rows would replace the demonstration seed data without changing the engine.

---

## 3. Mathematical & Algorithmic Formulation

### 3.1 Composite Phonetic Similarity ($S_{\text{phonetic}}$)
Given a memory canonical term $T$ and a spoken candidate span $C$:
$$S_{\text{phonetic}} = 0.35 \cdot S_{\text{norm}} + 0.30 \cdot S_{\text{metaphone}} + 0.15 \cdot S_{\text{soundex}} + 0.10 \cdot S_{\text{JW}} + 0.10 \cdot S_{\text{Lev}}$$
- $S_{\text{norm}}$: Normalized Levenshtein similarity after Indian-English phonetic normalization (`aa`$\to$`a`, `ee`$\to$`i`, `w`$\to$`v`, `ph`$\to$`f`, reduction of aspirated consonants `dh`$\to$`d`, `th`$\to$`t`).
- $S_{\text{metaphone}}$: Jaro-Winkler similarity on Metaphone acoustic keys.
- $S_{\text{soundex}}$: Binary match on Soundex codes.
- $S_{\text{JW}}$ / $S_{\text{Lev}}$: Orthographic baseline distances.

### 3.2 Contextual Affinity ($S_{\text{context}}$)
For sentence tokens $K$, positive triggers $P$, and negative contexts $N$:
$$S_{\text{context}} = \begin{cases} -1.0 & \text{if } K \cap N \neq \emptyset \quad (\text{Veto Triggered}) \\ 0.2 + 0.8 \cdot \frac{|K \cap P|}{|P|} & \text{if } |K \cap P| > 0 \\ 0.0 & \text{if } P \neq \emptyset \text{ and } K \cap P = \emptyset \\ 0.1 & \text{if } P = \emptyset \end{cases}$$

### 3.3 Composite Decision Score & Gating ($S_{\text{composite}}$)
Implemented once, as a pure function, in `core/memory_engine.compute_composite_score` - both `MemoryEngine.find_best_candidate` and `eval/ablation.py` call it, so the formula can never drift between what the product does and what the validation measures.

If $S_{\text{context}} < 0$, $S_{\text{composite}} = 0.0$ (Suppressed - an absolute veto, not just a large penalty; see §4.3).
Otherwise:
$$S_{\text{composite}} = 0.45 \cdot S_{\text{phonetic}} + 0.30 \cdot S_{\text{context}} + 0.25 \cdot C_{\text{memory}}$$

The system intervenes if and only if:
$$S_{\text{composite}} \ge \theta \quad (\text{default } \theta = 0.65)$$

Both the 0.45/0.30/0.25 split and $\theta = 0.65$ are validated empirically in `eval/ablation.py` / `ablation_report.md`, not asserted by feel - see §4.4 and §4.5.

### 3.4 Evidence Reinforcement & Penalty
When a user confirms a mapping through a correction (positive evidence):
$$C_{t+1} = \min(0.99, \; C_t + (1 - C_t) \times 0.25)$$

When a user reverts a substitution the system made (negative evidence - new in this revision, §4.7):
$$C_{t+1} = \max(0.0, \; C_t - 0.15)$$
and if $C_{t+1} < 0.20$, the memory is deactivated (`is_active = False`) rather than deleted - it stays inspectable but stops being offered as a candidate until reinforced again. The penalty is steeper than the reward, deliberately: an unwanted substitution is a worse product outcome for the user than a missed one, so it should cost more than one correct correction earns back. See §4.7 for the case this was built to fix.

---

## 4. Decisions & Validation

The assignment brief asks, explicitly, that every choice of X over Y come with some validation, not just a description. This section is that record. Each entry names the decision, the alternative it was weighed against, and where the evidence for it lives - most of it in files this repository can regenerate on demand, not in this prose.

### 4.1 Deterministic scoring vs. an LLM judge
**Decision:** Phonetic + context matching is fully deterministic (Metaphone/Soundex/Levenshtein/Jaro-Winkler + rule-based context overlap). No LLM call happens anywhere in the memory pipeline.
**Why:** The brief asks for a system whose decisions are inspectable and whose evaluation is reproducible - "we should be able to run it ourselves, inspect individual cases, and verify the conclusions." A deterministic pipeline gives the same output for the same input and database state, every time, which an LLM-judged pipeline does not. It also means the memory pipeline has a real, load-bearing latency and cost story: $0.00 and single-digit milliseconds (see `EVALUATION_SUMMARY.md`), not "depends on provider pricing that day."
**Trade-off acknowledged:** A deterministic normalizer tuned for Indian-English + common tech jargon will not generalize to phonetic patterns it wasn't designed for (see §6, Limitations). An LLM-based phonetic judge might generalize further, at the cost of latency, cost, and - critically for this brief - inspectability.

### 4.2 SQLite + SQLAlchemy vs. an in-memory dict store
**Decision:** Durable relational storage (`DBMemory`, `DBEvidenceLog`, `DBEvalRun`) via SQLAlchemy over SQLite, with a versioned Alembic migration history under `migrations/`.
**Why:** The brief explicitly asks how memory "should be kept durably" and asks for inspectable memory state and an evidence trail, not just a working demo. A relational evidence log (`DBEvidenceLog`) that records every observation a memory was built or penalized from is what makes `notes` and `source_type` on a `DBMemory` verifiable rather than asserted.
**Validated cost:** This durability isn't free - see §4.6 for the latency cost it was originally imposing and the fix.

### 4.3 Negative context as an absolute veto, not a large penalty
**Decision:** `compute_composite_score` returns exactly `0.0` whenever `context_affinity < 0` (i.e., any negative-context word matched), regardless of how high the phonetic similarity or base confidence is - see §3.3.
**Why:** A false substitution ("kiwi fruit" → "Kivi fruit") is a worse product outcome than a missed one, because it actively corrupts the user's transcript rather than leaving it as ASR produced it. A large-but-finite penalty could still be overridden by a strong enough phonetic match; an absolute veto cannot.
**Validated:** `eval/ablation.py`'s weight sweep keeps this veto fixed across every configuration it tries (see its docstring for why) and still varies the *rest* of the score meaningfully - the seeded suite's negative-context cases (CASE-02, 03, 07, 13, 16) and the holdout suite's Pinecone-in-a-forest case (after the fix, HOLD-05a/b) are all zero false interventions specifically because of this veto, not because of favorable weighting elsewhere.

### 4.4 The phonetic/context/confidence weight split (0.45/0.30/0.25)
**Decision:** Phonetic similarity is weighted highest, context second, prior confidence third.
**Validated:** `eval/ablation.py`'s weight ablation (see `ablation_report.md`, generated fresh by `python -m eval.run_eval`) compares the shipped split against a `phonetic_only` baseline (1.0/0/0) and two other splits, on the same 20+ recorded decision points from both the regression and holdout suites. The concrete, reproducible finding: dropping the context term measurably increases false interventions on this data - that is the actual argument for keeping it in the score, not an assertion that it helps.
**Trade-off acknowledged:** This is a small sweep (see the case count reported in `ablation_report.md`); read its exact ranking as directional, not as a mandate to chase the single best-scoring cell. `ablation_report.md`'s own "Reading this honestly" section says so explicitly.

### 4.5 The intervention threshold (0.65)
**Decision:** A single global threshold, not per-category or per-memory thresholds.
**Validated:** `eval/ablation.py`'s threshold sweep (0.30 → 0.90) is run against the same recorded decision points as §4.4. It is deliberately reported alongside the discovered Pinecone/pine-cone limitation (§4.7): a naive reading of the sweep might suggest raising the threshold to "fix" that one case, but doing so would also suppress genuinely correct interventions elsewhere in the sweep. We fixed the actual cause (a memory with no negative context yet) with the negative-evidence learning loop instead of moving a threshold every other memory in the system shares - see `ablation_report.md`'s closing section for the full argument.

### 4.6 Fetch the active memory set once per transcript, not once per span
**Decision:** `TranscriptProcessor.process` now calls `MemoryEngine.get_all_memories()` exactly once and passes the result into every `find_best_candidate` call for that transcript (`core/memory_engine.py`, `find_best_candidate(..., memories=...)`).
**Why:** The original implementation queried the database inside `find_best_candidate`, which is called for every candidate n-gram at every token position. Those repeated round trips could not change the answer because the memory set cannot change mid-request. This is exactly the kind of latency cost the brief asks to be measured and reported.
**Validated:** `tests/test_memory_engine.py::test_find_best_candidate_accepts_precomputed_memories` asserts both call styles return identical decisions (this is a caching change, not a behavior change). `EVALUATION_SUMMARY.md` reports the resulting per-suite latency from your own machine's run.

### 4.7 Learning negative evidence from a reverted substitution
**Decision:** Added `MemoryEngine.learn_negative_correction` and the API's `is_reversion` flag (`POST /api/learn`). When a user undoes a substitution Kivi made, the system does not just log it - it adds the sentence's *distinguishing* context words as `negative_contexts` on the specific memory that over-fired, and applies the confidence penalty in §3.4. "Distinguishing" is load-bearing: words that are already that memory's own positive triggers are excluded, because a matched negative context is an absolute veto (§3.2) and the sentence proving the substitution was wrong is usually still a sentence about the entity's subject matter. Without that filter, one revert of a `Temporal` substitution in a sentence that legitimately says "workflow" and "retry" would record those as vetoes and silence the memory permanently in exactly the context it was taught for.
**Why this exists:** Building the holdout suite surfaced a real bug, not a hypothetical one (see `eval/holdout_generalization.json`, journey `HOLD-04`, and `holdout_report.md`'s "Known Limitations" section): a freshly taught entity ("Pinecone", alias "pine cone") with no `negative_contexts` yet wrongly substituted a literal pine cone in a hiking sentence. The brief asks explicitly "what the product should do when its evidence is weak or wrong" - our answer is that the user's correction *is* the fix, not a config file only a developer can edit.
**Validated, not just claimed:** `HOLD-05` in the same suite teaches the fix live (from exactly the wrong output `HOLD-04` produced) and then asserts three things, all currently passing: (a) the exact failing sentence is now suppressed, (b) a *different*, previously-unseen forest sentence is also suppressed (proving the fix generalized from context words, not just memorized one sentence), and (c) the original legitimate product-context sentence from `HOLD-03` still intervenes correctly (proving the fix is scoped, not a blanket kill switch on the whole memory). `tests/test_memory_engine.py::test_learn_negative_correction_teaches_scoped_suppression` and `::test_learn_negative_correction_deactivates_after_repeated_false_positives` cover the same mechanism at the unit level.
**Where the trigger-exclusion filter came from:** `HOLD-04`/`HOLD-05` pass without it, because "forest"/"hiking" and "vector"/"embeddings" are disjoint vocabularies - the reverted sentence happens to share no words with the memory's own triggers. Running the same loop over a 49-entity, 596-transcript benchmark (18 independent false positives, each reverted the way a user would) showed that this is a property of that one example, not of the mechanism: with realistic vocabulary overlap, every revert wrote the memory's own triggers into its veto list, and all 126 positive cases for those 18 entities dropped to 0%. With the filter, the same 18 reverts still eliminate 100% of the false interventions (FIR 54.55% → 0.0%) while those positives hold at 82.5% versus an 85.7% pre-revert baseline - a 3.2 pp cost to remove a permanent-silencing failure mode. `::test_learn_negative_correction_never_negates_its_own_positive_triggers` locks the behaviour in.

### 4.8 Four separately-reported evaluation suites instead of one bigger number
**Decision:** `eval/regression_seeded.json` (entities hand-seeded in `db/seed_data.py`) and `eval/holdout_generalization.json` (entities taught live, from nothing, during the suite's own run) are kept as two separate, separately-reported suites - not merged into one number.
**Why:** The brief states this directly: *"A collection of successful examples chosen after the system was built is not an evaluation."* A single suite whose entities are all hand-seeded to match its own test sentences cannot, by construction, distinguish "the system generalizes" from "we remembered to write the right answer into the seed data." We found direct evidence of this while building this suite: **an earlier, cruder placeholder implementation of the phonetic-similarity function still scored 100% on the original seeded suite**, because that suite's aliases are looked up almost verbatim rather than genuinely phonetically matched. See `eval_engine.py`'s module docstring for the full argument. The holdout suite cannot make that mistake, because its entities are taught live, in the suite's own run, using the same code path a real user's correction would use, and the sentences they're tested on were written before the entity existed in memory at all.
**Validated:** All four suites are runnable and reproducible in one command (`python -m eval.run_eval`), and `EVALUATION_SUMMARY.md` reports them side by side rather than blending them - see §5.

**Extended (suite 4):** Suites 1-3 grade 21 cases across 10 entities, which is small enough that some behaviours never occur in them at all. `eval/scale_generalization.json` + `eval/scale_engine.py` add 49 entities that appear in no other data file here and nowhere in the brief, taught live, graded across ~694 transcripts in five case families that are never averaged together:

| Family | What it tests | Ground truth |
|---|---|---|
| `P` | Entity meant, context corroborates. 294 of 343 use a mishearing never shown during teaching. | INTERVENE |
| `HN` | The similar word in its own real meaning (`basil` the herb, a `red panda` at the zoo, the `temporal lobe`). | DO_NOTHING |
| `ADV` | An ordinary word *plus the entity's own trigger words*, so context argues **for** the wrong edit. Adversarial by construction - a stress test, not a traffic estimate. | DO_NOTHING |
| `CTRL` | 220 ordinary sentences mentioning no entity at all. The honest denominator for a real user's false-intervention rate. | DO_NOTHING |
| `W` | Entity meant, zero corroboration. Reported both ways, never folded into the headline, because its ground truth is a product decision rather than a fact. | reported both ways |

It also measures three things the small suites structurally cannot: cross-entity interference (suite 1 replayed on a 7x larger memory bank), the adaptation loop's cost to *true* positives as well as its benefit to false ones, and latency against both memory-bank size and transcript length. Two of the three failure modes documented in §8 were only reachable at this volume. Every case is generated deterministically from the corpus file, and a test fails loudly if any of its entities ever collides with the seed or holdout data.

---

## 5. Evaluation Results

Run `python -m eval.run_eval` from a fresh clone (after `pip install -r requirements.txt`) to generate all of the following, from a freshly reset and reseeded database:

| File | What it is |
|---|---|
| `EVALUATION_SUMMARY.md` | **Start here.** Ties the four suites together, plus latency/cost/DB-growth numbers. |
| `eval_report.md` / `eval_results.json` | Suite 1: seeded regression - full case-by-case detail and decision traces. |
| `holdout_report.md` / `holdout_results.json` | Suite 2: holdout generalization - the journeys, what was taught, what was tested, and the one labeled discovered limitation (fixed live in the same suite). |
| `ablation_report.md` / `ablation_results.json` | Suite 3: threshold sweep + weight ablation validating §4.4/§4.5. |
| `scale_report.md` / `scale_results.json` | Suite 4: large-scale generalization - 49 entities that appear in no other data file here and nowhere in the brief, ~694 transcripts across five separately-graded case families, plus cross-entity interference, the adaptation loop's cost, a ~600-case sensitivity sweep, and latency scaling. |

Every case in every suite is defined in a data file (`eval/regression_seeded.json`, `eval/holdout_generalization.json`, `eval/scale_generalization.json`) or derived from those suites' own recorded decision traces (`eval/ablation.py`) - nothing is asserted by hand after the fact. Each result preserves the active memory-bank summary and complete snapshots of the memories relevant to that decision. Teaching latency is measured separately from transcript inference. `tests/test_eval_suites.py` is a regression guard on the suites themselves (including a test that fails loudly if a holdout entity is ever accidentally also added to the seed data, which would quietly defeat the whole point of §4.8, and the equivalent guard for suite 4's 49 entities).

We deliberately do not paste a specific numbers table into this README: the seeded suite is expected to read 100% by construction (§4.8), the holdout suite's one labeled limitation means its headline number is meaningful only alongside `holdout_report.md`'s "Known Limitations" section, and hardcoding numbers here that can drift from a regenerated report is exactly the kind of stale, self-contradicting claim we found and removed from an earlier draft of this document (the previous revision claimed latency numbers here that directly contradicted the `eval_report.md` it also shipped). Run the command above and read `EVALUATION_SUMMARY.md`.

---

## 6. Repository Structure

```
sarvam/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI server & REST API
│   └── static/                    # Interactive Single Page App (Transcript Studio, Learning Hub, Inspector, Benchmark)
├── core/
│   ├── __init__.py
│   ├── models.py                  # Pydantic & SQLAlchemy ORM models
│   ├── memory_engine.py           # Persistence, evidence learning (positive + negative), context scoring, composite score
│   ├── phonetics.py                # Metaphone, Indian phonetic normalizer
│   └── transcript_processor.py    # 3-stage pipeline & decision explainability
├── db/
│   ├── __init__.py
│   ├── database.py                # SQLite lifecycle & session management
│   └── seed_data.py               # Bootstrap personas & seed memory bank
├── migrations/                    # Versioned Alembic database schema history
│   └── versions/0001_initial_schema.py
├── alembic.ini                    # Migration runner configuration
├── eval/
│   ├── __init__.py
│   ├── regression_seeded.json     # Suite 1 data: hand-seeded regression cases
│   ├── scale_generalization.json  # Suite 4 data: 49 unseen entities + templates
│   ├── scale_engine.py            # Suite 4 engine: families, interference, adaptation, scaling
│   ├── eval_engine.py             # Suite 1 runner
│   ├── holdout_generalization.json # Suite 2 data: live-taught, never-seeded journeys
│   ├── holdout_engine.py          # Suite 2 runner
│   ├── ablation.py                # Suite 3: threshold/weight sensitivity study
│   └── run_eval.py                # CLI orchestrator - runs all 3 suites, writes all reports
├── tests/
│   ├── __init__.py
│   ├── test_phonetics.py
│   ├── test_memory_engine.py       # incl. negative-evidence learning, composite score, caching
│   ├── test_transcript_processor.py
│   ├── test_api.py                 # incl. the is_reversion API path
│   └── test_eval_suites.py         # regression guard on the eval suites themselves
├── eval_results.json / eval_report.md               # generated (suite 1)
├── holdout_results.json / holdout_report.md          # generated (suite 2)
├── ablation_results.json / ablation_report.md        # generated (suite 3)
├── scale_results.json / scale_report.md              # generated (suite 4)
├── EVALUATION_SUMMARY.md                             # generated (start here)
├── requirements.txt
├── pytest.ini
├── .env.example
├── RUN.md                          # Reviewer verification guide
└── README.md                       # This document
```

---

## 7. How to Run & Verify

Please refer to **[RUN.md](RUN.md)** for the exact, complete reviewer procedure. Summary:
1. `pip install -r requirements.txt`
2. `python -m alembic upgrade head`
3. `python -m db.seed_data`
4. `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
5. Open `http://127.0.0.1:8000`
6. Run the full evaluation (all 3 suites): `python -m eval.run_eval`
7. Run the unit/integration test suite: `python -m pytest`

---

## 8. Limitations & Discovered Failure Modes

Discovering these was part of the assignment, not a gap to hide, so they're listed here rather than only in code comments.

- **Negative context is not learned from silence.** The system only learns a negative context either (a) hand-seeded at dictionary-creation time, or (b) taught reactively, after a user reverts a wrong substitution (`learn_negative_correction`, §4.7). It does **not** infer "this context is probably unrelated" just because a sentence never triggers a correction - it has no way to distinguish "correctly silent" from "never tested." This is why `HOLD-04` (§4.7) was a real, discovered gap rather than a hypothetical: the very first sentence in a genuinely new negative context produces one wrong substitution before the system can learn to avoid it. A production system would want a way to pre-populate common ambiguous English words (fruit names, common nouns) as default negative-context hints for any newly created entity that happens to collide with one.
- **One-shot learning is intentionally conservative outside its taught context.** `HOLD-01b` shows a single correction, by design, not being enough evidence to intervene in a context sharing none of that correction's trigger words - see §3.2's `0.0` branch for zero-overlap-with-existing-triggers. This is a product choice (prefer silence under weak evidence) with a real cost: a user who corrects a name exactly once, in one context, will not see it recognized elsewhere until they correct it again in a second context (`HOLD-02`) or the phonetic match alone is strong enough to carry it (as happened, for different reasons, with `ishan`→`Ishaan` directly - see `holdout_report.md`).
- **Correction extraction is token-diff based.** Replacements, including case-only canonical preferences such as `siobhan` -> `Siobhan`, are learned. Pure insertions and deletions are not treated as new phonetic memories because they do not provide a wrong-span-to-canonical-span mapping.
- **Multi-candidate disambiguation is implemented but not stress-tested.** `find_best_candidate` already takes the highest composite score across *all* active memories (not just the first match), so two different entities competing for the same misheard span is structurally handled - but the holdout suite does not currently include a case where two holdout entities are close enough phonetically to actually compete for the same span. This is stated here as an untested edge case, not silently assumed to work.
- **The ablation study (§4.4/§4.5) is a small sweep.** It is honest, reproducible validation for the shipped constants, not a claim of statistically rigorous hyperparameter optimization - `ablation_report.md` says this explicitly rather than letting a clean-looking table imply more than the sample size supports.
- **Cross-script / non-Latin phonetics are out of scope.** The normalizer is tuned for Indian-English transliteration variants and Latin-script tech jargon; Devanagari/Tamil/Telugu script input would need a grapheme-to-phoneme front end this system does not have.

---

## 9. AI Assistance Disclosure

AI coding assistants were used throughout this project (Gemini/Antigravity for an initial pass, then Claude). I directed the work, set the engineering direction, and made every product and architectural decision; the assistants were used to implement against those decisions, to review my own code adversarially, and to generate evaluation data at a volume I would not have hand-written.

Because the brief asks for this explicitly, here is what that actually looked like rather than a blanket statement.

**Decisions I made, which drove the work:**

- **That the first evaluation suite was not a real evaluation.** The original 16 cases were self-referential - their entities were hand-seeded in `db/seed_data.py` specifically so those cases would pass. That is exactly what the brief warns against, so I scoped the holdout suite (§4.8), the ablation study (§4.4/§4.5), and later the large-scale suite (§4.8) as the actual validation.
- **That a wrong substitution is categorically worse than a missed one.** This is the product judgement the whole system rests on: it is why negative context is an absolute veto rather than a weighted term, why the negative-evidence penalty (0.15) exceeds the reinforcement gain, and why the system prefers silence under weak evidence (§3.2, §3.4).
- **That the intervention threshold stays at 0.65.** When a 596-case sweep suggested 0.75 looked better in isolation, I had it tested end-to-end against the shipped suites first: 0.75 breaks `CASE-04`, `CASE-09` and `HOLD-02a`. A threshold every memory shares does not get moved to chase one family's score. 0.70 was rejected too - it trades six real misses for one avoided false edit.
- **That a discovered failure mode gets reported, not removed.** `HOLD-04` stays in the suite, labelled and excluded from headline accuracy, with its live fix in `HOLD-05`.
- **That the large-scale corpus ships inside the repository.** It was initially generated outside the repo. Numbers a reviewer cannot reproduce are not evidence, so it became suite 4, with a test that fails if any of its 49 entities ever collides with the seed or holdout data.
- **That the negative-learning defect below was worth fixing before submission** rather than documenting as a known limitation, once I had measured what it actually cost.

**Defects found and fixed during AI-assisted review:**

- **Negative-evidence learning was silently destroying the memories it corrected.** `learn_negative_correction` recorded every content word of a reverted sentence as a negative context - including the memory's own positive triggers. Since a matched negative context is an absolute veto, one revert permanently silenced an entity in exactly the context it was taught for: across 18 independent reverts it eliminated 100% of false positives while taking all 126 corresponding true positives to zero. Only reachable at 49 entities, because the holdout suite's vocabularies ("forest" vs "vector") happen not to overlap. Fixed with a trigger-exclusion filter; costs 3.17 pp of recall on the affected entities and is locked in by `tests/test_memory_engine.py::test_learn_negative_correction_never_negates_its_own_positive_triggers`.
- **Context-trigger leakage:** a learned multi-word entity's own words ("pie", "torch" from "pie torch" -> "PyTorch") were leaking into its own trigger list, weakening the negative-context vetoes those words exist to trigger (`::test_learn_from_correction_excludes_own_span_words_from_context`).
- **A README that contradicted its own generated reports:** the previous revision claimed latency numbers inconsistent with the `eval_report.md` shipped beside it, and claimed a "conversational frequency reinforcement" learning source with no implementation behind it. Both corrected (§5, §2).
- **A latency defect** (§4.6): memory lookup re-queried the database on every span of every transcript instead of once per transcript.

**What AI was not used for:** there is no LLM call anywhere in the runtime memory pipeline. Every substitution and suppression decision is deterministic - phonetic scoring plus rule-based context affinity - which is why model cost is $0.00 and results are byte-reproducible across runs.

Every number in this README is produced by a runnable case in `eval/` or `tests/`; nothing here is asserted by hand after the fact.
