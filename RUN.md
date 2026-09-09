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

The interface has four tabs in the top navigation - **Studio**, **Observe**, **Memory**, **Evaluate** - plus a **Reset** button. Every control named below is the exact on-screen label.

### Journey 1: The Core Assignment Example (Multi-Entity Substitution)
1. On the **Studio** tab, pick **Assignment brief: Aditya -> Aaditya, Kiwi -> Kivi** from the **Demonstration scenario** dropdown. It fills both input levels:
   - **Level 1 - ASR output:** `ask aditya to review the sarvam kiwi service`
   - **Level 2 - Formatted output:** `Ask Aditya to review the Sarvam Kiwi service.`
2. Click **Resolve transcript**.
3. **Verify:**
   - **Resolved transcript** reads `Ask Aaditya to review the Sarvam Kivi service.`
   - Both `Aditya -> Aaditya` and `Kiwi -> Kivi` are highlighted.
   - The **Decision ledger** shows, per span, the phonetic similarity, the matched context triggers (`sarvam`, `service`), the evidence confidence, and the composite score against the threshold.

### Journey 2: Negative Space & Homophone Traps (Deliberate Non-Intervention)
1. Select the **Negative space: kiwi fruit** scenario (`i want to eat a fresh kiwi fruit for breakfast`) and click **Resolve transcript**.
2. **Verify** the output is unchanged - `I want to eat a fresh kiwi fruit for breakfast.` - and that the **Decision ledger** records a *suppression* naming the matched negative-context trigger, rather than simply not mentioning the span.
3. Repeat with **Negative space: kneel on the floor**: `please kneel down on the floor to check the cable` stays unchanged, because `down` and `floor` are negative contexts for `Neil`.
4. **Negative space: pie and culinary torch** does the same for `PyTorch` in a cooking sentence.

### Journey 3: Dynamic Learning via User Correction
1. Go to the **Observe** tab, section **Learn from a correction**.
2. **Original transcript:** `Meeting with siobhan tomorrow at ten`
   **Corrected transcript:** `Meeting with Siobhan tomorrow at ten`
3. Click **Ingest correction**. Kivi extracts the mapping (`siobhan -> Siobhan`), computes its phonetic keys, and captures `meeting`/`tomorrow` as context triggers.
4. Return to **Studio**, put `i have a meeting with shivon` in **Level 1 - ASR output**, leave Level 2 blank, and click **Resolve transcript**. The learned term is applied - note that `shivon` is a spelling the system was never taught.

### Journey 4: Teaching Negative Evidence From a Wrong Substitution
Exercises the mechanism in `README.md` 4.7, built in response to a failure mode discovered while evaluating this system (see step 9 / `holdout_report.md`).
1. On **Observe**, in **Add an explicit term**: **Canonical term** `Pinecone`, **Category** `Product`, **Known ASR aliases** `pine cone`, **Context triggers** `vector, embeddings, database`, **Negative contexts** left empty. Click **Save memory**.
2. On **Studio**, resolve `i collected a fresh pine cone from the forest floor while hiking`.
3. **Verify** the fresh memory over-intervenes and returns `I collected a fresh Pinecone from the forest floor while hiking.` Copy that line.
4. On **Observe**, in **Correct a wrong intervention**: paste that line into **Kivi output**, and put `I collected a fresh pine cone from the forest floor while hiking.` into **User-restored text**. Click **Record negative evidence**.
5. Resolve the forest sentence again - it is now left unchanged, with an inspectable suppression trace.
6. Resolve `we store the embeddings in pine cone for fast retrieval` - it still becomes `We store the embeddings in Pinecone for fast retrieval.` The learned veto is contextual, not a blanket deletion.

This sequence (minus the manual copy/paste) is what `eval/holdout_generalization.json` journeys `HOLD-03/04/05` automate and assert on every run of `python -m eval.run_eval`.

### Journey 5: Memory State Inspection
1. Open the **Memory** tab (the badge next to its label is the active memory count).
2. Under **Stored terms**, search, inspect, or delete entries.
3. Each entry exposes its metaphone key, Indian-English phonetic normalization, soundex, confidence score, reinforcement count, positive context triggers, and negative contexts - including the negative context added automatically by Journey 4 rather than typed by hand.

### Journey 6: Evaluation From the UI
1. Open the **Evaluate** tab and click **Run benchmark**.
2. This calls `GET /api/eval` and runs **only Suite 1** (seeded regression). It is a quick in-app sanity check, not the full evaluation.
3. For the complete picture - all four suites, including the large-scale suite that reports the non-perfect numbers - use the terminal command in step 9 and read `EVALUATION_SUMMARY.md` first.

---

## 9. Exact Command to Run the Evaluation
Run the full, reproducible evaluation - all four suites - from your terminal:
```bash
python -m eval.run_eval
```
This resets and reseeds the database, then runs, in order: the seeded regression suite, the holdout generalization suite (teaching new entities live), the ablation/sensitivity study, and the large-scale generalization suite (49 entities taught live, ~694 transcripts) - and writes 9 files (see below). It takes roughly 30 seconds, most of it in suite 4. **Read `EVALUATION_SUMMARY.md` first.**

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
- **Via Web UI:** Click **Reset** in the top navigation bar (calls `POST /api/reset?with_seed=true`).
- **Via CLI / Python:**
  ```bash
  python -c "from db.database import reset_db; from db.seed_data import seed_database, SessionLocal; reset_db(); seed_database(SessionLocal())"
  ```
- Running `python -m eval.run_eval` also resets and reseeds the database as its first step (unless called with `--no-reset`).
