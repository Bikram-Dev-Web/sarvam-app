# Suite 2/4 - Holdout Generalization Report

> None of this suite's entities are in `db/seed_data.py`. Each journey teaches an entity live, through the same `MemoryEngine` calls a real correction, dictionary import, or reverted substitution would trigger, then tests recognition on sentences never used to teach it. This is the suite that actually answers 'does the memory system generalize.'

**Generated:** 2026-09-09T16:24:52Z

## Summary (graded cases only - see Known Limitations below)

| Metric | Value |
|---|---|
| Accuracy | **100.0%** (7/7) |
| Precision | **100.0%** |
| Recall | **100.0%** |
| False Intervention Rate | **0.0%** |
| Average Inference Latency | **3.05 ms** |
| Average Teaching Latency | **5.69 ms** |

## Confusion Matrix (graded cases only)

- True Positives: 4
- True Negatives: 3
- False Positives: 0
- False Negatives: 0

## Journeys

### HOLD-01: ishaan_one_shot_generalization
Teach a brand-new person entity ('Ishaan') from a single realistic correction, with NO hand-authored seed entry anywhere in db/seed_data.py. Then test whether the system generalizes to a differently-misheard spelling ('Eshan', never seen in teaching) in an unseen sentence.

- Taught via `correction`: `[{"original_span": "ishan", "canonical_term": "Ishaan", "memory_id": 9, "confidence": 0.88, "context_triggers": ["review", "deployment", "notes", "before", "merging"]}]`

### HOLD-02: ishaan_reinforcement_through_ordinary_use
A second, ordinary correction for the same person, in a different context ('standup'). Tests whether reinforcement through repeated ordinary use - not a bigger single upload - is what makes coverage broader, per the brief's 'how Kivi could learn through ordinary use'.

- Taught via `correction`: `[{"original_span": "eshan", "canonical_term": "Ishaan", "memory_id": 9, "confidence": 0.91, "context_triggers": ["join", "standup"]}]`

### HOLD-03: pinecone_new_category_recognition
A holdout entity outside the 'person' category (a product/jargon term), taught via an explicit dictionary entry rather than a correction, to prove the mechanism isn't special-cased to names. Deliberately configured the way a developer might realistically configure a v1 entry: no negative_contexts yet (see HOLD-04).

- Taught via `dictionary`: `{"id": 10, "canonical_term": "Pinecone", "category": "product", "phonetic_code": "PNKN", "normalized_phonetic": "pinecone", "soundex_code": "P525", "aliases": ["pine cone", "pinecone"], "confidence_score": 1.0, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.321159", "created_at`

### HOLD-04: pinecone_discovered_false_positive **[known_limitation_before_fix]**
No new teaching - reuses the memory state left by HOLD-03. 'Pine cone' is also a real, unrelated English noun phrase (a literal pine cone), and the v1 entry above has no negative_contexts to protect against that. This case is a DELIBERATE, LABELED demonstration of a real failure mode we discovered while building this suite, not a cherry-picked success - see README 'Known limitations & discovered failure modes' and eval/run_eval.py's report, which lists it separately from the pass/fail tally rather than folding it into the headline accuracy number.


### HOLD-05: pinecone_negative_evidence_fix_verified
The product's answer to HOLD-04: the user reverts Kivi's wrong substitution, which teaches negative evidence (learn_negative_correction) instead of requiring a developer to hand-edit negative_contexts. Verifies the fix (a) actually suppresses the failing case, (b) generalizes to a DIFFERENT unseen forest sentence rather than memorizing the one correction, and (c) does not regress the legitimate product-context case - the fix must be scoped, not a blanket kill switch.

- Taught via `negative_correction`: `[{"wrong_span": "Pinecone", "reverted_to": "pine cone", "memory_id": 10, "canonical_term": "Pinecone", "new_confidence": 0.85, "added_negative_contexts": ["collected", "fresh", "from", "forest", "floor", "while", "hiking"], "deactivated": false}]`

## Graded Cases (count toward the summary above)

| Case | Expected | Actual | Status | Latency |
|---|---|---|---|---|
| `HOLD-01a` | `INTERVENE` | `INTERVENE` | PASS | 3.695 ms |
| `HOLD-01b` | `DO_NOTHING` | `DO_NOTHING` | PASS | 1.62 ms |
| `HOLD-02a` | `INTERVENE` | `INTERVENE` | PASS | 2.023 ms |
| `HOLD-03a` | `INTERVENE` | `INTERVENE` | PASS | 2.949 ms |
| `HOLD-05a` | `DO_NOTHING` | `DO_NOTHING` | PASS | 4.251 ms |
| `HOLD-05b` | `DO_NOTHING` | `DO_NOTHING` | PASS | 4.176 ms |
| `HOLD-05c` | `INTERVENE` | `INTERVENE` | PASS | 2.42 ms |

### Graded case traces

#### HOLD-01a (ishaan_one_shot_generalization)
- Different misspelling than was taught ('Eshan' vs taught 'ishan'), in a sentence sharing two of the taught context words ('review', 'notes'). Phonetic similarity alone is moderate, not near-exact - this only crosses the intervention threshold because context corroborates it. Demonstrates the composite gate actually gating, not just phonetic lookup.
- ASR Input: `eshan should review the api docs and notes before merging`
- Expected: `Ishaan should review the api docs and notes before merging.` | Actual: `Ishaan should review the api docs and notes before merging.`
  - Span `Eshan` -> `Ishaan` | `INTERVENED` | phon=0.6447 ctx=0.84 conf=0.88 composite=0.7621
    Reason: Replaced 'Eshan' with personal term 'Ishaan'. Score 0.7621 >= 0.65.
  - Span `docs` -> `Deeksha` | `SUPPRESSED` | phon=0.6248 ctx=0.0 conf=0.92 composite=0.5112
    Reason: Candidate Deeksha was deliberately suppressed: High phonetic & contextual agreement (score 0.5112 vs threshold 0.65).
  - Memory state at decision time: 9 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil, Ishaan)
  - Relevant memory snapshots:
    - `{"id": 4, "canonical_term": "Deeksha", "category": "person", "phonetic_code": "TKX", "normalized_phonetic": "diksa", "soundex_code": "D200", "aliases": ["Diksha", "Deekshya"], "confidence_score": 0.92, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.220700", "created_at": "2026-09-09T16:24:52.220702", "source_type": "explicit_correction", "context_triggers": ["product", "roadmap", "sync", "jira", "call", "designer"], "negative_contexts": ["ceremony", "initiation", "spiritual"], "is_active": true, "notes": "Product Manager name"}`
    - `{"id": 9, "canonical_term": "Ishaan", "category": "learned_entity", "phonetic_code": "IXN", "normalized_phonetic": "isan", "soundex_code": "I250", "aliases": ["ishan"], "confidence_score": 0.88, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.298734", "created_at": "2026-09-09T16:24:52.298736", "source_type": "explicit_correction", "context_triggers": ["review", "deployment", "notes", "before", "merging"], "negative_contexts": [], "is_active": true, "notes": "Learned from user correction: 'ishan' -> 'Ishaan'"}`

#### HOLD-01b (ishaan_one_shot_generalization)
- Same unseen misspelling as HOLD-01a, but zero overlap with the one context vocabulary the system has ever observed for this person. A single correction is deliberately not enough evidence to intervene in a completely unrelated context - this is the product choosing silence under weak evidence, not a bug. Compare to HOLD-02a, where a second ordinary correction changes this outcome for a *different* unrelated context.
- ASR Input: `is eshan free for lunch`
- Expected: `Is eshan free for lunch.` | Actual: `Is eshan free for lunch.`
  - Span `eshan` -> `Ishaan` | `SUPPRESSED` | phon=0.6447 ctx=0.0 conf=0.88 composite=0.5101
    Reason: Candidate Ishaan was deliberately suppressed: High phonetic & contextual agreement (score 0.5101 vs threshold 0.65).
  - Memory state at decision time: 9 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil, Ishaan)
  - Relevant memory snapshots:
    - `{"id": 9, "canonical_term": "Ishaan", "category": "learned_entity", "phonetic_code": "IXN", "normalized_phonetic": "isan", "soundex_code": "I250", "aliases": ["ishan"], "confidence_score": 0.88, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.298734", "created_at": "2026-09-09T16:24:52.298736", "source_type": "explicit_correction", "context_triggers": ["review", "deployment", "notes", "before", "merging"], "negative_contexts": [], "is_active": true, "notes": "Learned from user correction: 'ishan' -> 'Ishaan'"}`

#### HOLD-02a (ishaan_reinforcement_through_ordinary_use)
- This is the exact sentence from HOLD-01b's context family ('free for ...'), which was suppressed before. It now intervenes because 'standup' overlaps a trigger learned in the second correction, AND 'eshan' is now itself a confirmed alias (not just a phonetic guess) - both learned from ordinary use, not from a bigger initial dictionary entry.
- ASR Input: `is eshan free for the standup`
- Expected: `Is Ishaan free for the standup.` | Actual: `Is Ishaan free for the standup.`
  - Span `eshan` -> `Ishaan` | `INTERVENED` | phon=0.95 ctx=0.314 conf=0.91 composite=0.7492
    Reason: Replaced 'eshan' with personal term 'Ishaan'. Score 0.7492 >= 0.65.
  - Memory state at decision time: 9 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil, Ishaan)
  - Relevant memory snapshots:
    - `{"id": 9, "canonical_term": "Ishaan", "category": "learned_entity", "phonetic_code": "IXN", "normalized_phonetic": "isan", "soundex_code": "I250", "aliases": ["ishan", "eshan"], "confidence_score": 0.91, "reinforcement_count": 2, "last_reinforced_at": "2026-09-09T16:24:52.312022", "created_at": "2026-09-09T16:24:52.298736", "source_type": "explicit_correction", "context_triggers": ["review", "deployment", "notes", "before", "merging", "join", "standup"], "negative_contexts": [], "is_active": true, "notes": "Learned from user correction: 'eshan' -> 'Ishaan'"}`

#### HOLD-03a (pinecone_new_category_recognition)
- Multi-word ASR mishearing ('pine cone') in a legitimate product context.
- ASR Input: `we store the embeddings in pine cone for fast retrieval`
- Expected: `We store the embeddings in Pinecone for fast retrieval.` | Actual: `We store the embeddings in Pinecone for fast retrieval.`
  - Span `pine cone` -> `Pinecone` | `INTERVENED` | phon=0.95 ctx=0.467 conf=1.0 composite=0.8176
    Reason: Replaced 'pine cone' with personal term 'Pinecone'. Score 0.8176 >= 0.65.
  - Memory state at decision time: 10 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil, Ishaan, Pinecone)
  - Relevant memory snapshots:
    - `{"id": 10, "canonical_term": "Pinecone", "category": "product", "phonetic_code": "PNKN", "normalized_phonetic": "pinecone", "soundex_code": "P525", "aliases": ["pine cone", "pinecone"], "confidence_score": 1.0, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.321159", "created_at": "2026-09-09T16:24:52.321161", "source_type": "manual_dictionary", "context_triggers": ["vector", "embeddings", "database", "index", "query", "retrieval"], "negative_contexts": [], "is_active": true, "notes": "Vector DB product name. v1 config - see HOLD-04/HOLD-05 for what happens next."}`

#### HOLD-05a (pinecone_negative_evidence_fix_verified)
- Same sentence as HOLD-04a - now correctly suppressed.
- ASR Input: `i collected a fresh pine cone from the forest floor while hiking`
- Expected: `I collected a fresh pine cone from the forest floor while hiking.` | Actual: `I collected a fresh pine cone from the forest floor while hiking.`
  - Span `pine cone` -> `Pinecone` | `SUPPRESSED` | phon=0.95 ctx=-1.0 conf=0.85 composite=0.0
    Reason: Candidate Pinecone was deliberately suppressed: Suppressed: Negative context detected (collected, fresh, from, forest, floor, while, hiking) (score 0.0 vs threshold 0.65).
  - Memory state at decision time: 10 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil, Ishaan, Pinecone)
  - Relevant memory snapshots:
    - `{"id": 10, "canonical_term": "Pinecone", "category": "product", "phonetic_code": "PNKN", "normalized_phonetic": "pinecone", "soundex_code": "P525", "aliases": ["pine cone", "pinecone"], "confidence_score": 0.85, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.321159", "created_at": "2026-09-09T16:24:52.321161", "source_type": "manual_dictionary", "context_triggers": ["vector", "embeddings", "database", "index", "query", "retrieval"], "negative_contexts": ["collected", "fresh", "from", "forest", "floor", "while", "hiking"], "is_active": true, "notes": "Vector DB product name. v1 config - see HOLD-04/HOLD-05 for what happens next. | Reverted in context (collected, fresh, from, forest, floor, while, hiking); confidence -0.15"}`

#### HOLD-05b (pinecone_negative_evidence_fix_verified)
- A DIFFERENT, previously-unseen sentence that shares the learned negative context 'forest'. This checks that the veto generalizes from contextual evidence rather than memorizing the exact corrected sentence.
- ASR Input: `she picked up a pine cone near the forest trail and put it in her bag`
- Expected: `She picked up a pine cone near the forest trail and put it in her bag.` | Actual: `She picked up a pine cone near the forest trail and put it in her bag.`
  - Span `pine cone` -> `Pinecone` | `SUPPRESSED` | phon=0.95 ctx=-1.0 conf=0.85 composite=0.0
    Reason: Candidate Pinecone was deliberately suppressed: Suppressed: Negative context detected (forest) (score 0.0 vs threshold 0.65).
  - Memory state at decision time: 10 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil, Ishaan, Pinecone)
  - Relevant memory snapshots:
    - `{"id": 10, "canonical_term": "Pinecone", "category": "product", "phonetic_code": "PNKN", "normalized_phonetic": "pinecone", "soundex_code": "P525", "aliases": ["pine cone", "pinecone"], "confidence_score": 0.85, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.321159", "created_at": "2026-09-09T16:24:52.321161", "source_type": "manual_dictionary", "context_triggers": ["vector", "embeddings", "database", "index", "query", "retrieval"], "negative_contexts": ["collected", "fresh", "from", "forest", "floor", "while", "hiking"], "is_active": true, "notes": "Vector DB product name. v1 config - see HOLD-04/HOLD-05 for what happens next. | Reverted in context (collected, fresh, from, forest, floor, while, hiking); confidence -0.15"}`

#### HOLD-05c (pinecone_negative_evidence_fix_verified)
- The original legitimate product-context case from HOLD-03 must still work. If this regressed, the negative-evidence mechanism would be an indiscriminate kill switch rather than a scoped correction - it is not.
- ASR Input: `we store the embeddings in pine cone for fast retrieval`
- Expected: `We store the embeddings in Pinecone for fast retrieval.` | Actual: `We store the embeddings in Pinecone for fast retrieval.`
  - Span `pine cone` -> `Pinecone` | `INTERVENED` | phon=0.95 ctx=0.467 conf=0.85 composite=0.7801
    Reason: Replaced 'pine cone' with personal term 'Pinecone'. Score 0.7801 >= 0.65.
  - Memory state at decision time: 10 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil, Ishaan, Pinecone)
  - Relevant memory snapshots:
    - `{"id": 10, "canonical_term": "Pinecone", "category": "product", "phonetic_code": "PNKN", "normalized_phonetic": "pinecone", "soundex_code": "P525", "aliases": ["pine cone", "pinecone"], "confidence_score": 0.85, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.321159", "created_at": "2026-09-09T16:24:52.321161", "source_type": "manual_dictionary", "context_triggers": ["vector", "embeddings", "database", "index", "query", "retrieval"], "negative_contexts": ["collected", "fresh", "from", "forest", "floor", "while", "hiking"], "is_active": true, "notes": "Vector DB product name. v1 config - see HOLD-04/HOLD-05 for what happens next. | Reverted in context (collected, fresh, from, forest, floor, while, hiking); confidence -0.15"}`

## Known Limitations (discovered failure modes, reported separately)

These cases are NOT counted in the summary metrics above. Each is a real behavior this system exhibits today, kept in the suite on purpose and labeled rather than removed, per the brief's instruction to report unnecessary or incorrect interventions separately from useful ones.

### HOLD-04a (pinecone_discovered_false_positive)
- This is the BUG, recorded as the system's actual (undesirable) behavior today given only the HOLD-03 teaching: it wrongly substitutes the literal pine cone. High phonetic similarity ('pine cone' is a registered alias) plus a merely-moderate base confidence is enough to clear the threshold even with zero relevant context, because no negative_contexts were ever taught for this entity. HOLD-05 shows the fix for exactly this.
- ASR Input: `i collected a fresh pine cone from the forest floor while hiking`
- Actual (today): `I collected a fresh Pinecone from the forest floor while hiking.` (`INTERVENE`)
- Desired: decision should be `DO_NOTHING`
  - Span `pine cone` -> `Pinecone` | `INTERVENED` | phon=0.95 ctx=0.0 conf=1.0 composite=0.6775
- Memory state at decision time: 10 active; relevant snapshots: `[{"id": 10, "canonical_term": "Pinecone", "category": "product", "phonetic_code": "PNKN", "normalized_phonetic": "pinecone", "soundex_code": "P525", "aliases": ["pine cone", "pinecone"], "confidence_score": 1.0, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.321159", "created_at": "2026-09-09T16:24:52.321161", "source_type": "manual_dictionary", "context_triggers": ["vector", "embeddings", "database", "index", "query", "retrieval"], "negative_contexts": [], "is_active": true, "notes": "Vector DB product name. v1 config - see HOLD-04/HOLD-05 for what happens next."}]`
