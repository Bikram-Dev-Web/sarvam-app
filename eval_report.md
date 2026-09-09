# Suite 1/4 - Seeded Regression Report

> This suite's entities are hand-seeded in `db/seed_data.py` specifically so these cases pass. Read it as a regression guard, not as evidence of generalization - see `holdout_report.md` and `EVALUATION_SUMMARY.md` for that.

**Generated:** 2026-09-09T16:24:52Z

## Summary

| Metric | Value |
|---|---|
| Exact Match Accuracy | **100.0%** |
| Precision (Useful Interventions) | **100.0%** |
| Recall (Intervention Coverage) | **100.0%** |
| False Intervention Rate | **0.0%** |
| Average Latency | **2.57 ms** |
| P95 Latency | **3.98 ms** |

## Confusion Matrix

- True Positives (Useful Interventions): 9
- True Negatives (Correct Suppressions): 7
- False Positives (Unnecessary Interventions): 0
- False Negatives (Missed Interventions): 0

## Case-by-Case

| ID | Category | Expected | Actual | Status | Latency |
|---|---|---|---|---|---|
| `CASE-01` | core_brief_example | `INTERVENE` | `INTERVENE` | PASS | 3.983 ms |
| `CASE-02` | negative_context_suppression | `DO_NOTHING` | `DO_NOTHING` | PASS | 2.604 ms |
| `CASE-03` | negative_context_suppression | `DO_NOTHING` | `DO_NOTHING` | PASS | 2.413 ms |
| `CASE-04` | person_name_disambiguation | `INTERVENE` | `INTERVENE` | PASS | 2.855 ms |
| `CASE-05` | indian_name_phonetic_variant | `INTERVENE` | `INTERVENE` | PASS | 2.506 ms |
| `CASE-06` | technical_jargon_replacement | `INTERVENE` | `INTERVENE` | PASS | 3.009 ms |
| `CASE-07` | negative_context_suppression | `DO_NOTHING` | `DO_NOTHING` | PASS | 2.684 ms |
| `CASE-08` | cloud_infrastructure_product | `INTERVENE` | `INTERVENE` | PASS | 1.926 ms |
| `CASE-09` | database_service_replacement | `INTERVENE` | `INTERVENE` | PASS | 1.768 ms |
| `CASE-10` | organization_and_product_cooccurrence | `INTERVENE` | `INTERVENE` | PASS | 2.644 ms |
| `CASE-11` | neutral_generic_speech | `DO_NOTHING` | `DO_NOTHING` | PASS | 2.371 ms |
| `CASE-12` | casing_and_punctuation_preservation | `INTERVENE` | `INTERVENE` | PASS | 3.077 ms |
| `CASE-13` | negative_context_suppression | `DO_NOTHING` | `DO_NOTHING` | PASS | 2.492 ms |
| `CASE-14` | organization_recognition | `INTERVENE` | `INTERVENE` | PASS | 1.865 ms |
| `CASE-15` | neutral_generic_speech | `DO_NOTHING` | `DO_NOTHING` | PASS | 2.154 ms |
| `CASE-16` | database_negative_space | `DO_NOTHING` | `DO_NOTHING` | PASS | 2.832 ms |

## Inspectable Decision Traces

### CASE-01: Original assignment brief case with multiple entity replacements (Person + Product)
- ASR Input: `ask aditya to review the sarvam kiwi service`
- Formatted Input: `Ask Aditya to review the Sarvam Kiwi service.`
- Expected Memory-Aware: `Ask Aaditya to review the Sarvam Kivi service.`
- Actual Memory-Aware: `Ask Aaditya to review the Sarvam Kivi service.`
- Result: MATCH
  - Decision Traces:
    - Span `Aditya` -> `Aaditya` | Decision: `INTERVENED`
      Phonetic: `0.9564` | Context: `0.5` | Confidence: `0.95` | Composite: `0.8179`
      Reason: Replaced 'Aditya' with personal term 'Aaditya'. Score 0.8179 >= 0.65.
    - Span `Kiwi` -> `Kivi` | Decision: `INTERVENED`
      Phonetic: `0.95` | Context: `0.378` | Confidence: `0.98` | Composite: `0.7859`
      Reason: Replaced 'Kiwi' with personal term 'Kivi'. Score 0.7859 >= 0.65.
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 1, "canonical_term": "Aaditya", "category": "person", "phonetic_code": "TTY", "normalized_phonetic": "aditya", "soundex_code": "A330", "aliases": ["Aditya", "Adithya", "Aadithya"], "confidence_score": 0.95, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.208427", "created_at": "2026-09-09T16:24:52.208429", "source_type": "explicit_correction", "context_triggers": ["review", "sarvam", "service", "pr", "meeting", "team", "code", "assigned"], "negative_contexts": [], "is_active": true, "notes": "Co-founder / Tech Lead name spelling preference"}`
    - `{"id": 2, "canonical_term": "Kivi", "category": "product", "phonetic_code": "KF", "normalized_phonetic": "kivi", "soundex_code": "K100", "aliases": ["Kiwi", "Keevi", "Kivee"], "confidence_score": 0.98, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.214152", "created_at": "2026-09-09T16:24:52.214154", "source_type": "explicit_correction", "context_triggers": ["sarvam", "service", "speech", "transcribe", "voice", "model", "app", "dictionary", "dictation"], "negative_contexts": ["fruit", "eat", "slice", "salad", "smoothie", "supermarket", "grocery", "bird", "new zealand"], "is_active": true, "notes": "Sarvam's speech product name. Never substitute when discussing the fruit or bird."}`

### CASE-02: Homophone trap where 'kiwi' refers to the fruit, not the speech product
- ASR Input: `i want to eat a fresh kiwi fruit for breakfast`
- Formatted Input: `I want to eat a fresh kiwi fruit for breakfast.`
- Expected Memory-Aware: `I want to eat a fresh kiwi fruit for breakfast.`
- Actual Memory-Aware: `I want to eat a fresh kiwi fruit for breakfast.`
- Result: MATCH
  - Decision Traces:
    - Span `kiwi` -> `Kivi` | Decision: `SUPPRESSED`
      Phonetic: `0.95` | Context: `-1.0` | Confidence: `0.98` | Composite: `0.0`
      Reason: Candidate Kivi was deliberately suppressed: Suppressed: Negative context detected (fruit, eat) (score 0.0 vs threshold 0.65).
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 2, "canonical_term": "Kivi", "category": "product", "phonetic_code": "KF", "normalized_phonetic": "kivi", "soundex_code": "K100", "aliases": ["Kiwi", "Keevi", "Kivee"], "confidence_score": 0.98, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.214152", "created_at": "2026-09-09T16:24:52.214154", "source_type": "explicit_correction", "context_triggers": ["sarvam", "service", "speech", "transcribe", "voice", "model", "app", "dictionary", "dictation"], "negative_contexts": ["fruit", "eat", "slice", "salad", "smoothie", "supermarket", "grocery", "bird", "new zealand"], "is_active": true, "notes": "Sarvam's speech product name. Never substitute when discussing the fruit or bird."}`

### CASE-03: Homophone trap where 'kneel' is a verb of physical posture, not person 'Neil'
- ASR Input: `please kneel down on the floor to check the cable`
- Formatted Input: `Please kneel down on the floor to check the cable.`
- Expected Memory-Aware: `Please kneel down on the floor to check the cable.`
- Actual Memory-Aware: `Please kneel down on the floor to check the cable.`
- Result: MATCH
  - Decision Traces:
    - Span `kneel` -> `Neil` | Decision: `SUPPRESSED`
      Phonetic: `0.95` | Context: `-1.0` | Confidence: `0.9` | Composite: `0.0`
      Reason: Candidate Neil was deliberately suppressed: Suppressed: Negative context detected (down, floor) (score 0.0 vs threshold 0.65).
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 8, "canonical_term": "Neil", "category": "person", "phonetic_code": "NL", "normalized_phonetic": "neil", "soundex_code": "N400", "aliases": ["kneel"], "confidence_score": 0.9, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.235007", "created_at": "2026-09-09T16:24:52.235009", "source_type": "explicit_correction", "context_triggers": ["meeting", "call", "slack", "manager", "engineer", "sent", "talked"], "negative_contexts": ["down", "floor", "prayer", "leg", "knee", "ground", "stand"], "is_active": true, "notes": "Team member name. Suppress when user means the physical action of kneeling."}`

### CASE-04: Person name replacement in professional communication context
- ASR Input: `i had a sync call with kneel to discuss the backend roadmap`
- Formatted Input: `I had a sync call with kneel to discuss the backend roadmap.`
- Expected Memory-Aware: `I had a sync call with Neil to discuss the backend roadmap.`
- Actual Memory-Aware: `I had a sync call with Neil to discuss the backend roadmap.`
- Result: MATCH
  - Decision Traces:
    - Span `kneel` -> `Neil` | Decision: `INTERVENED`
      Phonetic: `0.95` | Context: `0.314` | Confidence: `0.9` | Composite: `0.7467`
      Reason: Replaced 'kneel' with personal term 'Neil'. Score 0.7467 >= 0.65.
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 8, "canonical_term": "Neil", "category": "person", "phonetic_code": "NL", "normalized_phonetic": "neil", "soundex_code": "N400", "aliases": ["kneel"], "confidence_score": 0.9, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.235007", "created_at": "2026-09-09T16:24:52.235009", "source_type": "explicit_correction", "context_triggers": ["meeting", "call", "slack", "manager", "engineer", "sent", "talked"], "negative_contexts": ["down", "floor", "prayer", "leg", "knee", "ground", "stand"], "is_active": true, "notes": "Team member name. Suppress when user means the physical action of kneeling."}`

### CASE-05: Indian transliteration variant of product manager name
- ASR Input: `please assign the jira ticket to diksha for product review`
- Formatted Input: `Please assign the jira ticket to Diksha for product review.`
- Expected Memory-Aware: `Please assign the jira ticket to Deeksha for product review.`
- Actual Memory-Aware: `Please assign the jira ticket to Deeksha for product review.`
- Result: MATCH
  - Decision Traces:
    - Span `Diksha` -> `Deeksha` | Decision: `INTERVENED`
      Phonetic: `0.9579` | Context: `0.467` | Confidence: `0.92` | Composite: `0.8012`
      Reason: Replaced 'Diksha' with personal term 'Deeksha'. Score 0.8012 >= 0.65.
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 4, "canonical_term": "Deeksha", "category": "person", "phonetic_code": "TKX", "normalized_phonetic": "diksa", "soundex_code": "D200", "aliases": ["Diksha", "Deekshya"], "confidence_score": 0.92, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.220700", "created_at": "2026-09-09T16:24:52.220702", "source_type": "explicit_correction", "context_triggers": ["product", "roadmap", "sync", "jira", "call", "designer"], "negative_contexts": ["ceremony", "initiation", "spiritual"], "is_active": true, "notes": "Product Manager name"}`

### CASE-06: Machine learning framework misrecognized as common words
- ASR Input: `we trained our model using pie torch on multi gpu cluster`
- Formatted Input: `We trained our model using pie torch on multi GPU cluster.`
- Expected Memory-Aware: `We trained our model using PyTorch on multi GPU cluster.`
- Actual Memory-Aware: `We trained our model using PyTorch on multi GPU cluster.`
- Result: MATCH
  - Decision Traces:
    - Span `pie torch` -> `PyTorch` | Decision: `INTERVENED`
      Phonetic: `0.95` | Context: `0.4` | Confidence: `0.94` | Composite: `0.7825`
      Reason: Replaced 'pie torch' with personal term 'PyTorch'. Score 0.7825 >= 0.65.
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 5, "canonical_term": "PyTorch", "category": "jargon", "phonetic_code": "PTRX", "normalized_phonetic": "pytorch", "soundex_code": "P362", "aliases": ["pie torch", "py torch", "pie torch"], "confidence_score": 0.94, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.225112", "created_at": "2026-09-09T16:24:52.225114", "source_type": "manual_dictionary", "context_triggers": ["training", "cuda", "gpu", "model", "tensor", "backprop", "deep learning", "framework"], "negative_contexts": ["baking", "oven", "apple pie", "recipe", "flashlight", "fire torch"], "is_active": true, "notes": "ML Framework. Suppress in culinary or campfire contexts."}`

### CASE-07: Culinary context mentioning pie and a torch should not turn into PyTorch
- ASR Input: `baking an apple pie with a culinary torch in the oven`
- Formatted Input: `Baking an apple pie with a culinary torch in the oven.`
- Expected Memory-Aware: `Baking an apple pie with a culinary torch in the oven.`
- Actual Memory-Aware: `Baking an apple pie with a culinary torch in the oven.`
- Result: MATCH
  - Decision Traces:
    - Span `torch` -> `PyTorch` | Decision: `SUPPRESSED`
      Phonetic: `0.6869` | Context: `-1.0` | Confidence: `0.94` | Composite: `0.0`
      Reason: Candidate PyTorch was deliberately suppressed: Suppressed: Negative context detected (baking, oven, apple pie) (score 0.0 vs threshold 0.65).
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 5, "canonical_term": "PyTorch", "category": "jargon", "phonetic_code": "PTRX", "normalized_phonetic": "pytorch", "soundex_code": "P362", "aliases": ["pie torch", "py torch", "pie torch"], "confidence_score": 0.94, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.225112", "created_at": "2026-09-09T16:24:52.225114", "source_type": "manual_dictionary", "context_triggers": ["training", "cuda", "gpu", "model", "tensor", "backprop", "deep learning", "framework"], "negative_contexts": ["baking", "oven", "apple pie", "recipe", "flashlight", "fire torch"], "is_active": true, "notes": "ML Framework. Suppress in culinary or campfire contexts."}`

### CASE-08: Spoken acronym/phonetic for Kubernetes cluster deployment
- ASR Input: `deploy the docker container to the coober nettees cluster`
- Formatted Input: `Deploy the Docker container to the coober nettees cluster.`
- Expected Memory-Aware: `Deploy the Docker container to the Kubernetes cluster.`
- Actual Memory-Aware: `Deploy the Docker container to the Kubernetes cluster.`
- Result: MATCH
  - Decision Traces:
    - Span `coober nettees` -> `Kubernetes` | Decision: `INTERVENED`
      Phonetic: `0.95` | Context: `0.5` | Confidence: `0.93` | Composite: `0.81`
      Reason: Replaced 'coober nettees' with personal term 'Kubernetes'. Score 0.81 >= 0.65.
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 7, "canonical_term": "Kubernetes", "category": "jargon", "phonetic_code": "KBRNTS", "normalized_phonetic": "kubernetes", "soundex_code": "K165", "aliases": ["coober nettees", "k eights", "k8s"], "confidence_score": 0.93, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.231812", "created_at": "2026-09-09T16:24:52.231814", "source_type": "manual_dictionary", "context_triggers": ["cluster", "pod", "nodes", "deploy", "docker", "helm", "devops", "cloud"], "negative_contexts": [], "is_active": true, "notes": "Container orchestration system"}`

### CASE-09: Misrecognized developer tool name in backend database context
- ASR Input: `we migrated our postgres tables to super base`
- Formatted Input: `We migrated our postgres tables to super base.`
- Expected Memory-Aware: `We migrated our postgres tables to Supabase.`
- Actual Memory-Aware: `We migrated our postgres tables to Supabase.`
- Result: MATCH
  - Decision Traces:
    - Span `super base.` -> `Supabase` | Decision: `INTERVENED`
      Phonetic: `0.95` | Context: `0.314` | Confidence: `0.9` | Composite: `0.7467`
      Reason: Replaced 'super base' with personal term 'Supabase'. Score 0.7467 >= 0.65.
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 6, "canonical_term": "Supabase", "category": "product", "phonetic_code": "SPBS", "normalized_phonetic": "supabase", "soundex_code": "S112", "aliases": ["super base", "superbase"], "confidence_score": 0.9, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.228568", "created_at": "2026-09-09T16:24:52.228570", "source_type": "manual_dictionary", "context_triggers": ["database", "postgres", "auth", "backend", "table", "sql", "migration"], "negative_contexts": ["baseball", "superhero", "fortress", "military base"], "is_active": true, "notes": "Backend DB service"}`

### CASE-10: Company name and proprietary voice product combined sentence
- ASR Input: `sarwam released a new version of kiwi for indic speech`
- Formatted Input: `Sarwam released a new version of kiwi for Indic speech.`
- Expected Memory-Aware: `Sarvam released a new version of Kivi for Indic speech.`
- Actual Memory-Aware: `Sarvam released a new version of Kivi for Indic speech.`
- Result: MATCH
  - Decision Traces:
    - Span `Sarwam` -> `Sarvam` | Decision: `INTERVENED`
      Phonetic: `0.95` | Context: `0.314` | Confidence: `0.99` | Composite: `0.7692`
      Reason: Replaced 'Sarwam' with personal term 'Sarvam'. Score 0.7692 >= 0.65.
    - Span `kiwi` -> `Kivi` | Decision: `INTERVENED`
      Phonetic: `0.95` | Context: `0.289` | Confidence: `0.98` | Composite: `0.7592`
      Reason: Replaced 'kiwi' with personal term 'Kivi'. Score 0.7592 >= 0.65.
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 2, "canonical_term": "Kivi", "category": "product", "phonetic_code": "KF", "normalized_phonetic": "kivi", "soundex_code": "K100", "aliases": ["Kiwi", "Keevi", "Kivee"], "confidence_score": 0.98, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.214152", "created_at": "2026-09-09T16:24:52.214154", "source_type": "explicit_correction", "context_triggers": ["sarvam", "service", "speech", "transcribe", "voice", "model", "app", "dictionary", "dictation"], "negative_contexts": ["fruit", "eat", "slice", "salad", "smoothie", "supermarket", "grocery", "bird", "new zealand"], "is_active": true, "notes": "Sarvam's speech product name. Never substitute when discussing the fruit or bird."}`
    - `{"id": 3, "canonical_term": "Sarvam", "category": "organization", "phonetic_code": "SRFM", "normalized_phonetic": "sarvam", "soundex_code": "S615", "aliases": ["Serve hum", "Sarwam", "Sarvamm"], "confidence_score": 0.99, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.217638", "created_at": "2026-09-09T16:24:52.217640", "source_type": "manual_dictionary", "context_triggers": ["ai", "kivi", "indic", "models", "company", "bangalore", "service"], "negative_contexts": [], "is_active": true, "notes": "Company name"}`

### CASE-11: Ordinary everyday sentence with no personal entities or relevant triggers
- ASR Input: `the weather today in bangalore is quite pleasant and windy`
- Formatted Input: `The weather today in Bangalore is quite pleasant and windy.`
- Expected Memory-Aware: `The weather today in Bangalore is quite pleasant and windy.`
- Actual Memory-Aware: `The weather today in Bangalore is quite pleasant and windy.`
- Result: MATCH
  - *No candidate identified (clean pass-through).*
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)

### CASE-12: Entity at the beginning of an interrogative sentence
- ASR Input: `aditya, did you already push the pr to the repository?`
- Formatted Input: `Aditya, did you already push the PR to the repository?`
- Expected Memory-Aware: `Aaditya, did you already push the PR to the repository?`
- Actual Memory-Aware: `Aaditya, did you already push the PR to the repository?`
- Result: MATCH
  - Decision Traces:
    - Span `Aditya,` -> `Aaditya` | Decision: `INTERVENED`
      Phonetic: `0.9564` | Context: `0.3` | Confidence: `0.95` | Composite: `0.7579`
      Reason: Replaced 'Aditya' with personal term 'Aaditya'. Score 0.7579 >= 0.65.
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 1, "canonical_term": "Aaditya", "category": "person", "phonetic_code": "TTY", "normalized_phonetic": "aditya", "soundex_code": "A330", "aliases": ["Aditya", "Adithya", "Aadithya"], "confidence_score": 0.95, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.208427", "created_at": "2026-09-09T16:24:52.208429", "source_type": "explicit_correction", "context_triggers": ["review", "sarvam", "service", "pr", "meeting", "team", "code", "assigned"], "negative_contexts": [], "is_active": true, "notes": "Co-founder / Tech Lead name spelling preference"}`

### CASE-13: Supermarket grocery context mentioning kiwi and apples
- ASR Input: `can you buy some kiwi and bananas from the supermarket`
- Formatted Input: `Can you buy some kiwi and bananas from the supermarket?`
- Expected Memory-Aware: `Can you buy some kiwi and bananas from the supermarket?`
- Actual Memory-Aware: `Can you buy some kiwi and bananas from the supermarket?`
- Result: MATCH
  - Decision Traces:
    - Span `kiwi` -> `Kivi` | Decision: `SUPPRESSED`
      Phonetic: `0.95` | Context: `-1.0` | Confidence: `0.98` | Composite: `0.0`
      Reason: Candidate Kivi was deliberately suppressed: Suppressed: Negative context detected (supermarket) (score 0.0 vs threshold 0.65).
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 2, "canonical_term": "Kivi", "category": "product", "phonetic_code": "KF", "normalized_phonetic": "kivi", "soundex_code": "K100", "aliases": ["Kiwi", "Keevi", "Kivee"], "confidence_score": 0.98, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.214152", "created_at": "2026-09-09T16:24:52.214154", "source_type": "explicit_correction", "context_triggers": ["sarvam", "service", "speech", "transcribe", "voice", "model", "app", "dictionary", "dictation"], "negative_contexts": ["fruit", "eat", "slice", "salad", "smoothie", "supermarket", "grocery", "bird", "new zealand"], "is_active": true, "notes": "Sarvam's speech product name. Never substitute when discussing the fruit or bird."}`

### CASE-14: Spoken company name in startup and indic language context
- ASR Input: `serve hum is building speech AI models for India`
- Formatted Input: `Serve hum is building speech AI models for India.`
- Expected Memory-Aware: `Sarvam is building speech AI models for India.`
- Actual Memory-Aware: `Sarvam is building speech AI models for India.`
- Result: MATCH
  - Decision Traces:
    - Span `Serve hum` -> `Sarvam` | Decision: `INTERVENED`
      Phonetic: `0.95` | Context: `0.429` | Confidence: `0.99` | Composite: `0.8037`
      Reason: Replaced 'Serve hum' with personal term 'Sarvam'. Score 0.8037 >= 0.65.
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 3, "canonical_term": "Sarvam", "category": "organization", "phonetic_code": "SRFM", "normalized_phonetic": "sarvam", "soundex_code": "S615", "aliases": ["Serve hum", "Sarwam", "Sarvamm"], "confidence_score": 0.99, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.217638", "created_at": "2026-09-09T16:24:52.217640", "source_type": "manual_dictionary", "context_triggers": ["ai", "kivi", "indic", "models", "company", "bangalore", "service"], "negative_contexts": [], "is_active": true, "notes": "Company name"}`

### CASE-15: Conversation about general cooking with no entity matches
- ASR Input: `we prepared some pasta with tomato sauce and basil`
- Formatted Input: `We prepared some pasta with tomato sauce and basil.`
- Expected Memory-Aware: `We prepared some pasta with tomato sauce and basil.`
- Actual Memory-Aware: `We prepared some pasta with tomato sauce and basil.`
- Result: MATCH
  - *No candidate identified (clean pass-through).*
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)

### CASE-16: Baseball discussion mentioning a super base runner
- ASR Input: `the player is a super base runner in the baseball tournament`
- Formatted Input: `The player is a super base runner in the baseball tournament.`
- Expected Memory-Aware: `The player is a super base runner in the baseball tournament.`
- Actual Memory-Aware: `The player is a super base runner in the baseball tournament.`
- Result: MATCH
  - Decision Traces:
    - Span `super base` -> `Supabase` | Decision: `SUPPRESSED`
      Phonetic: `0.95` | Context: `-1.0` | Confidence: `0.9` | Composite: `0.0`
      Reason: Candidate Supabase was deliberately suppressed: Suppressed: Negative context detected (baseball) (score 0.0 vs threshold 0.65).
  - Memory state at decision time: 8 active (Aaditya, Kivi, Sarvam, Deeksha, PyTorch, Supabase, Kubernetes, Neil)
  - Relevant memory snapshots:
    - `{"id": 6, "canonical_term": "Supabase", "category": "product", "phonetic_code": "SPBS", "normalized_phonetic": "supabase", "soundex_code": "S112", "aliases": ["super base", "superbase"], "confidence_score": 0.9, "reinforcement_count": 1, "last_reinforced_at": "2026-09-09T16:24:52.228568", "created_at": "2026-09-09T16:24:52.228570", "source_type": "manual_dictionary", "context_triggers": ["database", "postgres", "auth", "backend", "table", "sql", "migration"], "negative_contexts": ["baseball", "superhero", "fortress", "military base"], "is_active": true, "notes": "Backend DB service"}`
