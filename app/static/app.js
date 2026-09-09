// Kivi Phonetic Memory System - Frontend Application Logic

const PRESETS = {
  "brief-core": {
    asr: "ask aditya to review the sarvam kiwi service",
    formatted: "Ask Aditya to review the Sarvam Kiwi service."
  },
  "homophone-fruit": {
    asr: "i want to eat a fresh kiwi fruit for breakfast",
    formatted: "I want to eat a fresh kiwi fruit for breakfast."
  },
  "homophone-kneel": {
    asr: "please kneel down on the floor to check the cable",
    formatted: "Please kneel down on the floor to check the cable."
  },
  "person-neil": {
    asr: "i had a sync call with kneel to discuss the backend roadmap",
    formatted: "I had a sync call with kneel to discuss the backend roadmap."
  },
  "indian-deeksha": {
    asr: "please assign the jira ticket to diksha for product review",
    formatted: "Please assign the jira ticket to Diksha for product review."
  },
  "jargon-pytorch": {
    asr: "we trained our model using pie torch on multi gpu cluster",
    formatted: "We trained our model using pie torch on multi GPU cluster."
  },
  "jargon-pie-suppress": {
    asr: "baking an apple pie with a culinary torch in the oven",
    formatted: "Baking an apple pie with a culinary torch in the oven."
  },
  "infra-k8s": {
    asr: "deploy the docker container to the coober nettees cluster",
    formatted: "Deploy the Docker container to the coober nettees cluster."
  },
  "db-supabase": {
    asr: "we migrated our postgres tables to super base",
    formatted: "We migrated our postgres tables to super base."
  },
  "clean-neutral": {
    asr: "the weather today in bangalore is quite pleasant and windy",
    formatted: "The weather today in Bangalore is quite pleasant and windy."
  }
};

function iconMarkup(name, className = "icon") {
  return `<svg class="${className}" aria-hidden="true"><use href="#icon-${name}"></use></svg>`;
}

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initStudio();
  initLearningHub();
  initMemoryInspector();
  initEvalBenchmark();
  initResetSystem();
  loadMemories();
});

// ==========================================
// TABS NAVIGATION
// ==========================================
function initTabs() {
  const tabs = document.querySelectorAll(".nav-tab");
  const contents = document.querySelectorAll(".tab-content");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetId = tab.getAttribute("data-tab");
      tabs.forEach(t => t.classList.remove("active"));
      contents.forEach(c => c.classList.remove("active"));
      tabs.forEach(t => t.setAttribute("aria-selected", "false"));

      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add("active");

      if (targetId === "memory-tab") {
        loadMemories();
      }
    });
  });
}

// ==========================================
// TRANSCRIPT STUDIO
// ==========================================
function initStudio() {
  const presetSelect = document.getElementById("scenario-preset");
  const asrInput = document.getElementById("asr-input");
  const formattedInput = document.getElementById("formatted-input");
  const slider = document.getElementById("confidence-threshold");
  const thresholdVal = document.getElementById("threshold-val");
  const btnProcess = document.getElementById("btn-process-transcript");

  slider.addEventListener("input", () => {
    thresholdVal.textContent = parseFloat(slider.value).toFixed(2);
  });

  presetSelect.addEventListener("change", () => {
    const val = presetSelect.value;
    if (PRESETS[val]) {
      asrInput.value = PRESETS[val].asr;
      formattedInput.value = PRESETS[val].formatted;
      processTranscript();
    }
  });

  btnProcess.addEventListener("click", processTranscript);

  // Load default brief example
  presetSelect.value = "brief-core";
  asrInput.value = PRESETS["brief-core"].asr;
  formattedInput.value = PRESETS["brief-core"].formatted;
  processTranscript();
}

async function processTranscript() {
  const asrInput = document.getElementById("asr-input").value.trim();
  const formattedInput = document.getElementById("formatted-input").value.trim();
  const threshold = parseFloat(document.getElementById("confidence-threshold").value);
  const outBox = document.getElementById("memory-aware-box");
  const tracesList = document.getElementById("traces-list");
  const statsBox = document.getElementById("processing-stats");

  if (!asrInput && !formattedInput) {
    outBox.innerHTML = `<div class="output-placeholder">Please enter an ASR or formatted transcript input.</div>`;
    return;
  }

  outBox.innerHTML = `<div class="output-placeholder">Evaluating phonetic matches & personal memory...</div>`;

  try {
    const response = await fetch("/api/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        asr_output: asrInput,
        formatted_output: formattedInput || null,
        confidence_threshold: threshold
      })
    });

    if (!response.ok) throw new Error("Processing failed");

    const data = await response.json();

    // Render Stats
    statsBox.hidden = false;
    document.getElementById("stat-latency").textContent = `${data.processing_latency_ms} ms`;
    document.getElementById("stat-interventions").textContent = `${data.interventions_count} interventions`;
    document.getElementById("stat-suppressions").textContent = `${data.suppressed_count} suppressed`;

    // Render Highlighted Output
    renderHighlightedOutput(data.formatted_output, data.memory_aware_output, data.traces, outBox);

    // Render Decision Traces
    renderDecisionTraces(data.traces, tracesList);

  } catch (err) {
    outBox.innerHTML = `<div class="output-placeholder text-danger">Error: ${err.message}</div>`;
  }
}

function renderHighlightedOutput(formattedText, memoryAwareText, traces, container) {
  if (!traces || traces.length === 0 || !traces.some(t => t.decision === "INTERVENED")) {
    container.innerHTML = `<p>${escapeHtml(memoryAwareText)}</p>`;
    return;
  }

  // Highlight replaced tokens
  let html = escapeHtml(memoryAwareText);
  traces.filter(t => t.decision === "INTERVENED").forEach(trace => {
    const rep = escapeHtml(trace.matched_memory_term);
    const regex = new RegExp(`\\b(${escapeRegExp(rep)})\\b`, "gi");
    const title = escapeHtml(`Replaced '${trace.original_span}' using personal memory`);
    html = html.replace(regex, `<span class="token-replaced" title="${title}">$1</span>`);
  });

  container.innerHTML = `<p>${html}</p>`;
}

function renderDecisionTraces(traces, container) {
  if (!traces || traces.length === 0) {
    container.innerHTML = `<div class="no-traces-message">No personal entity candidates triggered. Clean verbatim pass-through.</div>`;
    return;
  }

  container.innerHTML = "";

  traces.forEach(trace => {
    const isIntervened = trace.decision === "INTERVENED";
    const card = document.createElement("div");
    card.className = `trace-card ${isIntervened ? "decision-intervened" : "decision-suppressed"}`;

    const badgeClass = isIntervened ? "badge-success" : "badge-danger";
    const badgeText = isIntervened ? "Intervened" : "Suppressed / Do Nothing";

    const posTriggers = trace.details?.pos_matched_triggers?.join(", ") || "none";
    const negTriggers = trace.details?.neg_matched_triggers?.join(", ") || "none";

    card.innerHTML = `
      <div class="trace-top">
        <div class="trace-spans">
          <span class="span-original">${escapeHtml(trace.original_span)}</span>
          <span class="span-arrow">→</span>
          <span class="span-target">${escapeHtml(trace.matched_memory_term || "N/A")}</span>
        </div>
        <span class="badge ${badgeClass}">${badgeText}</span>
      </div>

      <div class="trace-metrics-grid">
        <div class="metric-item">
          <span class="metric-label">Phonetic Sim</span>
          <span class="metric-val">${(trace.phonetic_similarity * 100).toFixed(1)}%</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">Context Score</span>
          <span class="metric-val">${(trace.context_score * 100).toFixed(1)}%</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">Confidence</span>
          <span class="metric-val">${(trace.evidence_confidence * 100).toFixed(1)}%</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">Composite vs Min</span>
          <span class="metric-val">${trace.composite_decision_score.toFixed(2)} / ${trace.threshold.toFixed(2)}</span>
        </div>
      </div>

      <div class="trace-reason">
        <strong>Decision Rationale:</strong> ${escapeHtml(trace.reason)}
        ${negTriggers !== "none" ? `<span class="context-line context-negative">${iconMarkup("alert")}<span>Negative context: ${escapeHtml(negTriggers)}</span></span>` : ""}
        ${posTriggers !== "none" ? `<span class="context-line context-positive">${iconMarkup("check")}<span>Supporting context: ${escapeHtml(posTriggers)}</span></span>` : ""}
      </div>
    `;

    container.appendChild(card);
  });
}

// ==========================================
// OBSERVATION & LEARNING HUB
// ==========================================
function initLearningHub() {
  const formCorrection = document.getElementById("form-learn-correction");
  const formExplicit = document.getElementById("form-add-explicit");
  const formNegative = document.getElementById("form-learn-negative");
  const feedbackCard = document.getElementById("learn-feedback");
  const negativeFeedback = document.getElementById("negative-feedback");

  formCorrection.addEventListener("submit", async (e) => {
    e.preventDefault();
    const orig = document.getElementById("learn-orig-text").value.trim();
    const corr = document.getElementById("learn-corr-text").value.trim();

    try {
      const resp = await fetch("/api/learn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: "user_correction",
          original_text: orig,
          corrected_text: corr
        })
      });

      const data = await resp.json();
      if (data.status === "success") {
        feedbackCard.hidden = false;
        if (data.learned.length) {
          feedbackCard.innerHTML = `
            <span class="feedback-title">${iconMarkup("check")}<span>Memory updated</span></span>
            Extracted <strong>${data.learned.length}</strong> entity mapping${data.learned.length === 1 ? "" : "s"}:<br>
            ${data.learned.map(l => `<code>${escapeHtml(l.original_span)}</code> → <strong>${escapeHtml(l.canonical_term)}</strong> (confidence ${(l.confidence*100).toFixed(0)}%; context: ${l.context_triggers.map(escapeHtml).join(", ") || "none"})`).join("<br>")}
          `;
          loadMemories();
        } else {
          feedbackCard.innerHTML = `<strong>No phonetic mapping found.</strong><br>Add a replacement such as <code>shivon</code> → <strong>Siobhan</strong>, or use Method B for an explicit term.`;
        }
      }
    } catch (err) {
      alert("Failed to learn from correction: " + err.message);
    }
  });

  formExplicit.addEventListener("submit", async (e) => {
    e.preventDefault();
    const canonical = document.getElementById("dict-canonical").value.trim();
    const category = document.getElementById("dict-category").value;
    const aliases = document.getElementById("dict-aliases").value.split(",").map(s => s.trim()).filter(Boolean);
    const triggers = document.getElementById("dict-triggers").value.split(",").map(s => s.trim()).filter(Boolean);
    const negatives = document.getElementById("dict-negatives").value.split(",").map(s => s.trim()).filter(Boolean);

    try {
      const resp = await fetch("/api/memories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          canonical_term: canonical,
          category: category,
          aliases: aliases,
          context_triggers: triggers,
          negative_contexts: negatives,
          confidence_score: 0.90,
          source_type: "manual_dictionary"
        })
      });

      if (resp.ok) {
        alert(`Memory for '${canonical}' saved successfully!`);
        formExplicit.reset();
        loadMemories();
      }
    } catch (err) {
      alert("Failed to add memory: " + err.message);
    }
  });

  formNegative.addEventListener("submit", async (e) => {
    e.preventDefault();
    const memoryAwareText = document.getElementById("negative-memory-text").value.trim();
    const revertedText = document.getElementById("negative-reverted-text").value.trim();

    try {
      const resp = await fetch("/api/learn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: "negative_correction",
          original_text: memoryAwareText,
          corrected_text: revertedText,
          is_reversion: true
        })
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Negative correction failed");

      negativeFeedback.hidden = false;
      if (!data.penalized.length) {
        negativeFeedback.innerHTML = `<strong>No memory was changed.</strong><br>Make sure the wrong Kivi output contains the canonical term that performed the substitution.`;
      } else {
        negativeFeedback.innerHTML = `
          <span class="feedback-title">${iconMarkup("check")}<span>Negative context learned</span></span>
          ${data.penalized.map(entry =>
            `<code>${escapeHtml(entry.wrong_span)}</code> restored to <strong>${escapeHtml(entry.reverted_to)}</strong>` +
            ` (confidence ${(entry.new_confidence * 100).toFixed(0)}%; suppress around: ${entry.added_negative_contexts.map(escapeHtml).join(", ") || "no new context"})`
          ).join("<br>")}
        `;
        formNegative.reset();
        loadMemories();
      }
    } catch (err) {
      negativeFeedback.hidden = false;
      negativeFeedback.innerHTML = `<strong class="text-danger">Error:</strong> ${escapeHtml(err.message)}`;
    }
  });
}

// ==========================================
// MEMORY STATE INSPECTOR
// ==========================================
let globalMemories = [];

function initMemoryInspector() {
  const searchInput = document.getElementById("memory-search");
  searchInput.addEventListener("input", () => {
    const q = searchInput.value.toLowerCase();
    const filtered = globalMemories.filter(m => 
      m.canonical_term.toLowerCase().includes(q) ||
      m.category.toLowerCase().includes(q) ||
      m.phonetic_code.toLowerCase().includes(q)
    );
    renderMemoriesTable(filtered);
  });
}

async function loadMemories() {
  try {
    const resp = await fetch("/api/memories");
    const memories = await resp.json();
    globalMemories = memories;
    document.getElementById("nav-mem-count").textContent = memories.length;
    renderMemoriesTable(memories);
  } catch (err) {
    console.error("Failed to load memories", err);
  }
}

function renderMemoriesTable(memories) {
  const tbody = document.getElementById("memory-table-body");
  if (!memories || memories.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center">No memories in database.</td></tr>`;
    return;
  }

  tbody.innerHTML = memories.map(m => `
    <tr>
      <td><strong>${escapeHtml(m.canonical_term)}</strong></td>
      <td><span class="badge badge-info">${escapeHtml(m.category)}</span></td>
      <td>
        <span class="data-label">Metaphone:</span> <code>${escapeHtml(m.phonetic_code)}</code><br>
        <span class="data-label">Normalized:</span> <code>${escapeHtml(m.normalized_phonetic)}</code>
      </td>
      <td>
        <strong class="confidence-value">${(m.confidence_score * 100).toFixed(0)}%</strong><br>
        <small class="data-label">Used ${m.reinforcement_count}×</small>
      </td>
      <td>
        <div class="tag-list">
          ${m.context_triggers && m.context_triggers.length ? m.context_triggers.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join("") : `<span class="data-label">none</span>`}
        </div>
      </td>
      <td>
        <div class="tag-list">
          ${m.negative_contexts && m.negative_contexts.length ? m.negative_contexts.map(t => `<span class="tag tag-neg">${escapeHtml(t)}</span>`).join("") : `<span class="data-label">none</span>`}
        </div>
      </td>
      <td><small>${escapeHtml(m.source_type)}</small></td>
      <td>
        <button class="btn btn-outline-danger" onclick="deleteMemoryItem(${m.id})" aria-label="Delete memory ${escapeHtml(m.canonical_term)}">${iconMarkup("trash")}</button>
      </td>
    </tr>
  `).join("");
}

async function deleteMemoryItem(id) {
  if (!confirm("Are you sure you want to delete this memory?")) return;
  try {
    const resp = await fetch(`/api/memories/${id}`, { method: "DELETE" });
    if (resp.ok) {
      loadMemories();
    }
  } catch (err) {
    alert("Failed to delete memory");
  }
}

// ==========================================
// EVALUATION BENCHMARK DASHBOARD
// ==========================================
function initEvalBenchmark() {
  const btnRun = document.getElementById("btn-run-eval");
  btnRun.addEventListener("click", runBenchmarkEvaluation);
}

async function runBenchmarkEvaluation() {
  const btnRun = document.getElementById("btn-run-eval");
  const tbody = document.getElementById("eval-table-body");
  
  btnRun.disabled = true;
  btnRun.innerHTML = `<span class="spinner" aria-hidden="true"></span><span>Running benchmark</span>`;
  tbody.innerHTML = `<tr><td colspan="7" class="text-center">Executing test cases across dataset...</td></tr>`;

  try {
    const resp = await fetch("/api/eval?save_to_db=true");
    const summary = await resp.json();

    // Update KPI Cards
    document.getElementById("eval-kpi-acc").textContent = `${summary.accuracy_pct}%`;
    document.getElementById("eval-kpi-prec").textContent = `${summary.precision_pct}%`;
    document.getElementById("eval-kpi-rec").textContent = `${summary.recall_pct}%`;
    document.getElementById("eval-kpi-fir").textContent = `${summary.false_intervention_rate_pct}%`;
    document.getElementById("eval-kpi-lat").textContent = `${summary.latency.avg_ms} ms`;
    document.getElementById("eval-case-counts").textContent = `${summary.total_cases} cases (${summary.passed_cases} passed)`;

    // Render Table
    renderEvalCasesTable(summary.cases);

  } catch (err) {
    alert("Evaluation failed: " + err.message);
  } finally {
    btnRun.disabled = false;
    btnRun.innerHTML = `<span>Run benchmark</span>${iconMarkup("arrow")}`;
  }
}

function renderEvalCasesTable(cases) {
  const tbody = document.getElementById("eval-table-body");
  tbody.innerHTML = cases.map(c => `
    <tr>
      <td><code>${escapeHtml(c.id)}</code></td>
      <td><small class="data-label">${escapeHtml(c.category)}</small></td>
      <td>
        <span class="data-label">ASR:</span> ${escapeHtml(c.asr_input)}<br>
        <span class="data-label">Fmt:</span> ${escapeHtml(c.formatted_input || "N/A")}
      </td>
      <td>
        <span class="data-label">Exp:</span> <code>${escapeHtml(c.expected_output)}</code><br>
        <span class="data-label">Act:</span> <strong class="${c.passed ? "result-pass" : "result-fail"}">${escapeHtml(c.actual_output)}</strong>
      </td>
      <td>
        <span class="badge ${c.actual_decision === 'INTERVENE' ? 'badge-info' : 'badge-neutral'}">
          ${escapeHtml(c.actual_decision)}
        </span>
      </td>
      <td><code>${c.latency_ms} ms</code></td>
      <td>
        <span class="badge ${c.passed ? 'badge-success' : 'badge-danger'}">
          ${c.passed ? 'PASS' : 'FAIL'}
        </span>
      </td>
    </tr>
  `).join("");
}

// ==========================================
// RESET SYSTEM
// ==========================================
function initResetSystem() {
  const btnReset = document.getElementById("btn-reset-system");
  btnReset.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to reset the system? This will re-seed the standard demonstration persona.")) return;
    try {
      const resp = await fetch("/api/reset?with_seed=true", { method: "POST" });
      if (resp.ok) {
        alert("System memory successfully reset to benchmark seed state!");
        loadMemories();
        processTranscript();
      }
    } catch (err) {
      alert("Failed to reset system: " + err.message);
    }
  });
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeRegExp(text) {
  return String(text).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
