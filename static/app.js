/**
 * ScholarScope — Vanilla JavaScript SPA Router and UI Controller
 * B.Tech AI Tools & Prompt Engineering Mini Project
 * Student: Daksh Ghandaat (150096725209)
 */

document.addEventListener("DOMContentLoaded", () => {
  initRouter();
  initForm();
  initExampleChips();
  initReportActions();
});

// =====================================================================
// 1. Single Page Application (SPA) Hash Router
// =====================================================================

function initRouter() {
  const navLinks = document.querySelectorAll(".nav-item");
  const views = {
    home: document.getElementById("view-home"),
    analyze: document.getElementById("view-analyze"),
    "how-it-works": document.getElementById("view-how-it-works"),
    "compare-prompts": document.getElementById("view-compare-prompts"),
    history: document.getElementById("view-history"),
    "responsible-ai": document.getElementById("view-responsible-ai")
  };

  function handleRoute() {
    let hash = window.location.hash.replace("#", "").toLowerCase() || "home";
    if (!views[hash]) hash = "home";

    // Update nav links
    navLinks.forEach(link => {
      if (link.dataset.view === hash) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      } else {
        link.classList.remove("active");
        link.removeAttribute("aria-current");
      }
    });

    // Update view panels
    Object.keys(views).forEach(key => {
      if (views[key]) {
        if (key === hash) {
          views[key].classList.add("active");
        } else {
          views[key].classList.remove("active");
        }
      }
    });

    // Lazy load data for views
    if (hash === "history") fetchHistory();
  }

  window.addEventListener("hashchange", handleRoute);
  handleRoute(); // Initial load

  // Refresh buttons
  const refreshHistoryBtn = document.getElementById("refresh-history-btn");
  if (refreshHistoryBtn) refreshHistoryBtn.addEventListener("click", fetchHistory);

  // Live comparison quota warning modal
  const openModalBtn = document.getElementById("open-live-compare-modal-btn");
  const modal = document.getElementById("live-compare-modal");
  const cancelModalBtn = document.getElementById("modal-cancel-btn");
  const proceedModalBtn = document.getElementById("modal-proceed-btn");

  if (openModalBtn && modal) {
    openModalBtn.addEventListener("click", () => modal.classList.remove("hidden"));
    if (cancelModalBtn) cancelModalBtn.addEventListener("click", () => modal.classList.add("hidden"));
    if (proceedModalBtn) proceedModalBtn.addEventListener("click", () => modal.classList.add("hidden"));
  }
}

// =====================================================================
// 2. Form Handling & Character Counter (with Real SSE Streaming)
// =====================================================================

function initForm() {
  const form = document.getElementById("analyze-form");
  const textarea = document.getElementById("topic-input");
  const counter = document.getElementById("char-counter");
  const submitBtn = document.getElementById("submit-btn");
  const versionRadios = document.querySelectorAll('input[name="prompt_version"]');
  const versionBadge = document.getElementById("selected-version-badge");

  // Character counter
  textarea.addEventListener("input", () => {
    const len = textarea.value.length;
    counter.textContent = `${len} / 300`;
    if (len > 280) {
      counter.classList.add("at-limit");
      counter.classList.remove("near-limit");
    } else if (len > 240) {
      counter.classList.add("near-limit");
      counter.classList.remove("at-limit");
    } else {
      counter.classList.remove("near-limit", "at-limit");
    }
  });

  // Enter to submit (Shift+Enter for newline)
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  // Version selector badge
  versionRadios.forEach(radio => {
    radio.addEventListener("change", (e) => {
      versionBadge.textContent = `${e.target.value} (${e.target.value === "V3" ? "Default" : "Custom"})`;
    });
  });

  // Submit handler driven by real SSE streaming
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const topic = textarea.value.trim();
    if (!topic) return;

    const selectedVersion = document.querySelector('input[name="prompt_version"]:checked')?.value || "V3";

    // UI state: running
    submitBtn.disabled = true;
    submitBtn.querySelector(".btn-text").textContent = "Analyzing topic...";
    
    // Reset output panels
    hideAllResults();
    const stageTracker = document.getElementById("stage-tracker");
    stageTracker.classList.remove("hidden");
    resetStageTracker();

    try {
      // Connect to real-time Server-Sent Events stream
      const response = await fetch("/api/analyze-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic, version: selectedVersion })
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let finalResult = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop(); // Retain incomplete chunk

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data: ")) {
            try {
              const event = JSON.parse(trimmed.substring(6));
              if (event.type === "stage_update") {
                // Real server event: only marks done when server actually finishes that stage
                setStageState(event.stage, event.status, event.duration_ms);
              } else if (event.type === "final") {
                finalResult = event.result;
              }
            } catch (pErr) {
              console.warn("Failed to parse SSE line:", trimmed);
            }
          }
        }
      }

      if (finalResult) {
        if (finalResult.status === "success") {
          renderSuccessResults(finalResult);
        } else if (finalResult.status === "rejected" || finalResult.status === "unresearchable") {
          renderNotice(finalResult);
        } else if (finalResult.status === "validation_failed") {
          renderValidationFailed(finalResult);
        }
      }

    } catch (err) {
      console.error("[Analyze Error]:", err);
      renderNotice({
        status: "error",
        message: `Evaluation failed: ${err.message}. Please verify server status.`,
        sheet_saved: false,
        sheet_message: "Not saved to Google Sheet"
      });
      setStageState(0, "failed");
    } finally {
      submitBtn.disabled = false;
      submitBtn.querySelector(".btn-text").textContent = "Analyze topic";
    }
  });
}

function initExampleChips() {
  const chips = document.querySelectorAll(".chip");
  const textarea = document.getElementById("topic-input");
  const counter = document.getElementById("char-counter");

  chips.forEach(chip => {
    chip.addEventListener("click", () => {
      textarea.value = chip.dataset.topic;
      textarea.focus();
      counter.textContent = `${textarea.value.length} / 300`;
    });
  });
}

// =====================================================================
// 3. Stage Tracker Animations & Server-Driven Updates
// =====================================================================

function resetStageTracker() {
  for (let i = 0; i <= 5; i++) {
    const el = document.getElementById(`stage-${i}`);
    if (el) el.className = "stage-item";
    const timer = document.getElementById(`stage-timer-${i}`);
    if (timer) timer.textContent = "-";
  }
}

function setStageState(idx, state, durationMs = null) {
  const el = document.getElementById(`stage-${idx}`);
  if (!el) return;
  el.className = `stage-item ${state}`;
  if (durationMs !== null && durationMs !== undefined) {
    const timer = document.getElementById(`stage-timer-${idx}`);
    if (timer) timer.textContent = `${durationMs}ms`;
  }
}

// =====================================================================
// 4. Render Evaluation Results
// =====================================================================

function hideAllResults() {
  document.getElementById("results-container").classList.add("hidden");
  document.getElementById("notice-block").classList.add("hidden");
}

function renderSuccessResults(data) {
  const container = document.getElementById("results-container");
  container.classList.remove("hidden");

  const scores = data.scores || {};
  const total = scores.total || 0;
  const verdict = scores.verdict || "Feasible";

  // Verdict title & class
  const verdictTitle = document.getElementById("result-verdict");
  verdictTitle.textContent = verdict;
  verdictTitle.className = "verdict-title " + verdict.toLowerCase().replace(/\s+/g, "-");

  // Total score
  const totalScoreEl = document.getElementById("result-total-score");
  totalScoreEl.innerHTML = `${total} <span class="total-denom">/ 20</span>`;

  // Segmented total bar (20 ticks)
  renderSegmentedBar(total, verdict);

  // Criteria rows
  renderCriterion("scope", scores.scope);
  renderCriterion("resources", scores.resources);
  renderCriterion("sources", scores.sources);
  renderCriterion("outcomes", scores.outcomes);

  // Validator Inspector
  renderValidatorPanel(data.validation_stages || []);

  // Markdown Report
  renderMarkdownReport(data.report || "");

  // Sheet Confirmation line
  const sheetConfirmBar = document.getElementById("sheet-confirm-bar");
  const sheetConfirmText = document.getElementById("sheet-confirm-text");
  if (data.sheet_saved) {
    sheetConfirmText.textContent = `Saved to Google Sheet, row ${data.sheet_row}`;
    sheetConfirmBar.style.color = "var(--muted)";
  } else {
    sheetConfirmText.textContent = data.sheet_message || "Not saved to Google Sheet";
    sheetConfirmBar.style.color = "var(--score-low)";
  }

  // Scroll gently to results
  container.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderSegmentedBar(total, verdict) {
  const track = document.getElementById("total-bar-track");
  track.innerHTML = "";

  const colorClass = (verdict === "Feasible") ? "filled-high" :
                     (verdict === "Needs Refinement") ? "filled-mid" : "filled-low";

  for (let i = 1; i <= 20; i++) {
    const seg = document.createElement("div");
    seg.className = "total-segment" + (i <= total ? ` ${colorClass}` : "");
    track.appendChild(seg);
  }
}

function renderCriterion(id, critData) {
  if (!critData) return;
  const score = critData.score || 0;
  const reason = critData.reason || "";

  document.getElementById(`score-val-${id}`).textContent = `${score} / 5`;
  document.getElementById(`reason-${id}`).textContent = reason;

  const meter = document.getElementById(`meter-${id}`);
  meter.style.width = `${(score / 5) * 100}%`;
  meter.className = `criterion-fill score-${score}`;
}

function renderValidatorPanel(stages) {
  const details = document.getElementById("validator-details");
  const overallBadge = document.getElementById("validator-overall-badge");
  const list = document.getElementById("validator-stage-list");
  list.innerHTML = "";

  const allPassed = stages.every(s => s.passed);

  if (allPassed) {
    overallBadge.textContent = "All 3 Validator Sub-Stages Passed";
    overallBadge.className = "validator-badge pass";
    details.open = false;
  } else {
    overallBadge.textContent = "Validator Errors Detected";
    overallBadge.className = "validator-badge fail";
    details.open = true; // Open by default on failure
  }

  stages.forEach(s => {
    const li = document.createElement("li");
    li.className = "validator-stage-item";

    const icon = document.createElement("span");
    icon.className = `val-icon ${s.passed ? "pass" : "fail"}`;
    icon.textContent = s.passed ? "✓" : "✕";

    const textWrap = document.createElement("div");
    textWrap.className = "val-stage-text";
    textWrap.innerHTML = `<strong>${s.stage}</strong>: ${s.passed ? "Passed" : "Failed"}`;

    if (!s.passed && s.errors && s.errors.length) {
      s.errors.forEach(err => {
        const p = document.createElement("p");
        p.className = "val-err-msg";
        p.textContent = `• ${err}`;
        textWrap.appendChild(p);
      });
    }

    li.appendChild(icon);
    li.appendChild(textWrap);
    list.appendChild(li);
  });
}

function renderNotice(data) {
  const noticeBlock = document.getElementById("notice-block");
  noticeBlock.classList.remove("hidden");

  const titleEl = document.getElementById("notice-title");
  const bodyEl = document.getElementById("notice-body");
  const proofEl = document.getElementById("notice-sheet-proof");

  if (data.status === "rejected") {
    titleEl.textContent = "Input Guardrail Rejection";
  } else if (data.status === "unresearchable") {
    titleEl.textContent = "Topic Not Currently Researchable";
  } else {
    titleEl.textContent = "System Notice";
  }

  bodyEl.textContent = data.message || "Request could not be processed.";

  if (data.sheet_saved) {
    proofEl.textContent = `Saved to Google Sheet, row ${data.sheet_row}`;
  } else {
    proofEl.textContent = data.sheet_message || "Not saved to Google Sheet";
  }

  noticeBlock.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderValidationFailed(data) {
  renderNotice({
    status: "rejected",
    message: "Topic scoring output failed rubric validation even after correction retry.",
    sheet_saved: data.sheet_saved,
    sheet_row: data.sheet_row,
    sheet_message: data.sheet_message
  });
}

// =====================================================================
// 5. Markdown Report Rendering & Export
// =====================================================================

let currentRawMarkdown = "";

function renderMarkdownReport(rawMd) {
  currentRawMarkdown = rawMd;
  const container = document.getElementById("report-rendered-body");
  container.innerHTML = parseSimpleMarkdown(rawMd);
}

function parseSimpleMarkdown(md) {
  if (!md) return "<p>No report generated.</p>";

  const lines = md.split("\n");
  let html = [];
  let inTable = false;
  let inUl = false;
  let tableRows = [];

  for (let line of lines) {
    let trimmed = line.trim();

    // Table rows: | Col 1 | Col 2 |
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      if (inUl) { html.push("</ul>"); inUl = false; }
      if (!inTable) { inTable = true; tableRows = []; }
      if (!trimmed.includes("---")) {
        tableRows.push(trimmed);
      }
      continue;
    } else if (inTable) {
      html.push(renderTableHtml(tableRows));
      inTable = false;
      tableRows = [];
    }

    // Headings
    if (trimmed.startsWith("## ")) {
      if (inUl) { html.push("</ul>"); inUl = false; }
      html.push(`<h2>${formatInline(trimmed.substring(3))}</h2>`);
      continue;
    }

    // Unordered lists
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      if (!inUl) { html.push("<ul>"); inUl = true; }
      html.push(`<li>${formatInline(trimmed.substring(2))}</li>`);
      continue;
    } else if (inUl && trimmed === "") {
      html.push("</ul>");
      inUl = false;
      continue;
    }

    if (trimmed.length > 0) {
      if (inUl) { html.push("</ul>"); inUl = false; }
      html.push(`<p>${formatInline(trimmed)}</p>`);
    }
  }

  if (inTable) html.push(renderTableHtml(tableRows));
  if (inUl) html.push("</ul>");

  return html.join("\n");
}

function renderTableHtml(rows) {
  if (!rows || !rows.length) return "";
  let out = ["<table>"];
  rows.forEach((r, idx) => {
    const cells = r.split("|").slice(1, -1).map(c => c.trim());
    const tag = (idx === 0) ? "th" : "td";
    out.push("<tr>" + cells.map(c => `<${tag}>${formatInline(c)}</${tag}>`).join("") + "</tr>");
  });
  out.push("</table>");
  return out.join("");
}

function formatInline(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, "<code>$1</code>");
}

function initReportActions() {
  const copyBtn = document.getElementById("copy-report-btn");
  const downloadBtn = document.getElementById("download-report-btn");

  copyBtn.addEventListener("click", async () => {
    if (!currentRawMarkdown) return;
    try {
      await navigator.clipboard.writeText(currentRawMarkdown);
      const original = copyBtn.textContent;
      copyBtn.textContent = "Copied!";
      setTimeout(() => copyBtn.textContent = original, 2000);
    } catch (err) {
      alert("Failed to copy report to clipboard.");
    }
  });

  downloadBtn.addEventListener("click", () => {
    if (!currentRawMarkdown) return;
    const blob = new Blob([currentRawMarkdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ScholarScope_Report_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  });
}

// =====================================================================
// 6. View Data Fetchers (History, Prompts, Tests)
// =====================================================================

async function fetchHistory() {
  const tbody = document.getElementById("history-tbody");
  tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Fetching history from Google Sheets...</td></tr>`;

  try {
    const res = await fetch("/api/history");
    const json = await res.json();
    const rows = json.data || [];

    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No evaluations recorded yet in the Results tab.</td></tr>`;
      return;
    }

    tbody.innerHTML = rows.map(r => `
      <tr>
        <td><small>${escapeHtml(r.timestamp)}</small></td>
        <td><strong>${escapeHtml(r.topic)}</strong></td>
        <td><code>${escapeHtml(r.version)}</code></td>
        <td class="num-col">${escapeHtml(r.total || "-")}</td>
        <td>${renderVerdictTag(r.verdict)}</td>
        <td><small>${escapeHtml(r.validation || "-")}</small></td>
        <td><small class="text-muted">${escapeHtml(r.notes || "-")}</small></td>
      </tr>
    `).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Failed to load history: ${err.message}</td></tr>`;
  }
}

async function fetchPrompts() {
  const logTbody = document.getElementById("prompt-log-tbody");
  const blocksList = document.getElementById("prompt-blocks-list");

  try {
    const res = await fetch("/api/prompts");
    const json = await res.json();

    const log = json.prompt_log || [];
    logTbody.innerHTML = log.map(item => `
      <tr>
        <td><strong>${escapeHtml(item.version)}</strong><br><small>${escapeHtml(item.name)}</small></td>
        <td><small>${item.techniques.map(t => `• ${escapeHtml(t)}`).join("<br>")}</small></td>
        <td><small>${escapeHtml(item.changes)}</small></td>
        <td><small>${item.failure_modes.map(f => `• ${escapeHtml(f)}`).join("<br>")}</small></td>
      </tr>
    `).join("");

    const promptsToDisplay = [
      { id: "v3", title: "PROMPT_V3 — Production Grade Scoring Prompt", text: json.scoring_prompts?.V3 },
      { id: "v2", title: "PROMPT_V2 — Role + Rubric Prompt", text: json.scoring_prompts?.V2 },
      { id: "v1", title: "PROMPT_V1 — Zero-Shot Baseline Prompt", text: json.scoring_prompts?.V1 },
      { id: "analysis", title: "ANALYSIS_PROMPT — Topic Understanding & Question Synthesis", text: json.analysis_prompt },
      { id: "report", title: "REPORT_PROMPT — Markdown Feasibility Report Prompt", text: json.report_prompt }
    ];

    blocksList.innerHTML = promptsToDisplay.map(p => `
      <div class="card prompt-block-card">
        <div class="prompt-block-header">
          <h3 class="prompt-title">${escapeHtml(p.title)}</h3>
          <button type="button" class="btn btn-secondary btn-sm copy-prompt-btn" data-text="${encodeURIComponent(p.text || '')}">Copy prompt</button>
        </div>
        <pre class="prompt-pre"><code>${escapeHtml(p.text || "")}</code></pre>
      </div>
    `).join("");

    document.querySelectorAll(".copy-prompt-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const text = decodeURIComponent(btn.dataset.text);
        await navigator.clipboard.writeText(text);
        const orig = btn.textContent;
        btn.textContent = "Copied!";
        setTimeout(() => btn.textContent = orig, 1800);
      });
    });

  } catch (err) {
    console.error("Failed to load prompts:", err);
  }
}

async function fetchTests() {
  const tbody = document.getElementById("tests-tbody");
  tbody.innerHTML = `<tr><td colspan="8" class="empty-state">Fetching test records from Google Sheet Tests tab...</td></tr>`;

  try {
    const res = await fetch("/api/tests");
    const json = await res.json();
    const rows = json.data || [];

    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No test records found in the Tests tab.</td></tr>`;
      return;
    }

    tbody.innerHTML = rows.map(r => `
      <tr>
        <td><small>${escapeHtml(r.timestamp)}</small></td>
        <td><code>${escapeHtml(r.test_id || "-")}</code></td>
        <td><strong>${escapeHtml(r.topic)}</strong></td>
        <td><code>${escapeHtml(r.version)}</code></td>
        <td class="num-col">${escapeHtml(r.total || "-")}</td>
        <td>${renderVerdictTag(r.verdict)}</td>
        <td><small>${escapeHtml(r.validation || "-")}</small></td>
        <td><small class="text-muted">${escapeHtml(r.notes || "-")}</small></td>
      </tr>
    `).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty-state">Failed to load tests: ${err.message}</td></tr>`;
  }
}

function renderVerdictTag(verdict) {
  if (!verdict) return "-";
  const norm = verdict.toLowerCase().replace(/\s+/g, "-");
  return `<span class="verdict-tag ${norm}">${escapeHtml(verdict)}</span>`;
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
