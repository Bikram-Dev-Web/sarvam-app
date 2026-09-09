# RUN.md — Verification & Review Guide

## 1. Primary Review Method
**Primary Review Method:** **Completely Local Application** (FastAPI Backend + SQLite + Embedded Vanilla Web UI & CLI Evaluation Suite).

---

## 2. Required Runtimes & Versions
- **Python:** `3.10` or higher (tested on `Python 3.13.x` / `3.12.x` / `3.11.x`)
- **Web Browser:** Modern browser (Chrome, Safari, Edge, Firefox)
- **Operating System:** Cross-platform (macOS, Linux, Windows)

---

## 3. Environment Variables
No environment variables are required. The application defaults to the repository-local `kivi_memory.db` file.

`KIVI_DB_PATH` is optional if you want the SQLite file elsewhere. Set it in the shell that runs Alembic and the application:
```bash
# Windows PowerShell
$env:KIVI_DB_PATH = "C:\path\to\kivi_memory.db"

# macOS / Linux
export KIVI_DB_PATH=/path/to/kivi_memory.db
```
The repository includes `.env.example` as a reference, but does not auto-load `.env` files. No private credentials or paid API keys are required; all phonetic matching, context scoring, and evaluations run locally and deterministically. No LLM call is made anywhere in this system.

---

## 4. Exact Commands to Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 5. Exact Commands to Create, Migrate, and Seed Database
Apply the versioned Alembic schema migration, then populate the standard seed entities (`Aaditya`, `Kivi`, `Sarvam`, `Deeksha`, `Supabase`, `PyTorch`, `Kubernetes`, `Neil`):
```bash
python -m alembic upgrade head
python -m db.seed_data
```
Note: these are the ONLY entities pre-loaded into memory. `Ishaan` and `Pinecone`, used by the holdout generalization suite (see step 9), are deliberately not in this list - they are taught live, during that suite's own run, to prove the system generalizes rather than just replaying seeded answers. See `README.md` §4.8.

---

## 6. Exact Commands to Start the Application Process
Start the local FastAPI web server:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## 7. URL to Open
Open your browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 8. Primary Interactions to Try

### Journey 1: The Core Assignment Example (Multi-Entity Substitution)
1. In the **Transcript Studio** tab, select **Assignment Brief** from the scenario dropdown.
   - **ASR Input:** `ask aditya to review the sarvam kiwi service`
   - **Formatted Output:** `Ask Aditya to review the Sarvam Kiwi service.`
2. Click **⚡ Resolve Memory-Aware Transcript**.
3. **Verify:**
   - **Memory-Aware Output:** `Ask Aaditya to review the Sarvam Kivi service.`
   - Both `Aditya -> Aaditya` and `Kiwi -> Kivi` are highlighted.
   - Inspect the **Decision Traces**: phonetic similarity, context trigger matches (`sarvam`, `service`), and composite confidence score.

### Journey 2: Negative Space & Homophone Traps (Deliberate Non-Intervention)
1. Select **Negative Space: Kiwi Fruit** preset:
   - **Input:** `i want to eat a fresh kiwi fruit for breakfast`
2. Click **⚡ Resolve Memory-Aware Transcript**.
3. **Verify:**
   - Output remains `I want to eat a fresh kiwi fruit for breakfast.` (no false replacement).
   - The Decision Trace shows a suppression due to a matched negative-context trigger.
4. Try **Negative Space: Kneel down on floor**:
   - `please kneel down on the floor to check the cable` remains unchanged because `down`/`floor` trigger negative-context suppression for `Neil`.

### Journey 3: Dynamic Learning via User Correction
1. Switch to the **Observation Hub** tab.
2. In **Method A: Learn from User Correction**:
   - **Original Transcript:** `Meeting with siobhan tomorrow at ten`
   - **Corrected Transcript:** `Meeting with Siobhan tomorrow at ten`
3. Click **🧠 Ingest Observation & Update Memory**.
4. Observe Kivi extracting the mapping (`siobhan -> Siobhan`), computing phonetic representations, capturing context triggers (`meeting`, `tomorrow`), and adding it to durable memory.
5. Return to **Transcript Studio**, input `i have a meeting with shivon`, and watch Kivi apply the learned name `Siobhan`.

### Journey 4: Teaching Negative Evidence From a Wrong Substitution
This exercises the mechanism documented in `README.md` §4.7, built in response to a real failure mode discovered while evaluating this system (see step 9 / `holdout_report.md`). It is fully available in the browser UI.
1. In **Observation Hub > Method B**, add `Pinecone` as a product with alias `pine cone`, positive contexts `vector, embeddings, database`, and no negative contexts.
2. In **Transcript Studio**, process `i collected a fresh pine cone from the forest floor while hiking`.
3. Verify the fresh memory initially over-intervenes and produces `I collected a fresh Pinecone from the forest floor while hiking.` Copy that output.
4. In **Observation Hub > Method C**, paste that output into **Kivi Output**, then enter `I collected a fresh pine cone from the forest floor while hiking.` as **User-Restored Text**. Submit the negative correction.
5. Process the forest sentence again and verify it is now left unchanged with an inspectable suppression trace.
6. Process `we store the embeddings in pine cone for fast retrieval` and verify it still becomes `We store the embeddings in Pinecone for fast retrieval.` The learned veto is contextual, not a blanket deletion.

This exact sequence (minus the manual copy/paste) is what `eval/holdout_generalization.json` journeys `HOLD-03/04/05` automate and assert on every run of `python -m eval.run_eval` - step 9 below reproduces it without any manual steps.

### Journey 5: Memory State Inspector
1. Switch to the **Memory Inspector** tab.
2. Search, inspect, or delete memory entries.
3. Observe Metaphone keys, Indian phonetic normalizations, confidence scores, reinforcement counts, positive context triggers, and negative context constraints - including any that were added automatically via Journey 4 rather than typed in by hand.

### Journey 6: Full Evaluation (all 3 suites)
1. Switch to the **Evaluation Benchmark** tab, or run from a terminal (recommended - see step 9).
2. The in-app **🚀 Run Benchmark Evaluation** button calls `GET /api/eval`, which runs only Suite 1 (seeded regression) - it is a quick in-app sanity check, not the full evaluation story.
3. For the complete picture (all 3 suites, plus the honest read of what they mean together), use the terminal command in step 9 and read `EVALUATION_SUMMARY.md`.

---

## 9. Exact Command to Run the Evaluation
Run the full, reproducible evaluation - all four suites - from your terminal:
```bash
python -m eval.run_eval
```
This resets and reseeds the database, then runs, in order: the seeded regression suite, the holdout generalization suite (teaching new entities live), and the ablation/sensitivity study - and writes 7 files (see below). **Read `EVALUATION_SUMMARY.md` first.**

Each generated evaluation case preserves its inputs, expected and actual outputs, traces, and a snapshot of the relevant memory state. Holdout teaching latency and transcript-inference latency are measured separately.

To run the automated `pytest` test suite (unit tests for the memory engine, phonetics, transcript processor, API, and the evaluation suites themselves):
```bash
python -m pytest
```

---

## 10. Where Evaluation Results Are Written
- `EVALUATION_SUMMARY.md` — **start here.** Ties all four suites together with latency/cost/DB-growth numbers.
- `eval_results.json` / `eval_report.md` — Suite 1 (seeded regression), machine-readable and human-readable.
- `holdout_results.json` / `holdout_report.md` — Suite 2 (holdout generalization), including the one labeled discovered limitation and its live fix.
- `ablation_results.json` / `ablation_report.md` — Suite 3 (threshold/weight sensitivity study).
- `scale_results.json` / `scale_report.md` — Suite 4 (large-scale generalization): 49 entities seen nowhere else in this repository, ~694 transcripts, five case families graded separately. This is the suite that reports non-perfect numbers, and the reasons are broken down case by case. Takes ~25s of the run's total time.
- Database Evaluation History: the seeded regression suite's runs are additionally stored in the `eval_runs` SQLite table (`GET /api/stats` reports the row count).

---

## 11. Exact Procedure for Resetting the System
- **Via Web UI:** Click the **🔄 Reset System** button in the top navigation bar (calls `POST /api/reset?with_seed=true`).
- **Via CLI / Python:**
  ```bash
  python -c "from db.database import reset_db; from db.seed_data import seed_database, SessionLocal; reset_db(); seed_database(SessionLocal())"
  ```
- Running `python -m eval.run_eval` also resets and reseeds the database as its first step (unless called with `--no-reset`).
