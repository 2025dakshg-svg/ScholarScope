/**
 * ScholarScope Analyze Controller
 * Manages topic submission, real-time Server-Sent Events (SSE) stage tracking,
 * safe markdown report rendering, and report actions (Copy, Download, Print).
 */
(function() {
  "use strict";

  // Elements
  const form = document.getElementById("analyze-form");
  const topicInput = document.getElementById("topic-input");
  const charCounter = document.getElementById("char-counter");
  const submitBtn = document.getElementById("submit-btn");
  const resetBtn = document.getElementById("reset-btn");
  const chipBtns = document.querySelectorAll(".chip-btn");

  const stageTrackerSection = document.getElementById("stage-tracker-section");
  const trackerElapsedBadge = document.getElementById("tracker-elapsed-badge");

  const alertInline = document.getElementById("alert-inline");
  const alertInlineTitle = document.getElementById("alert-inline-title");
  const alertInlineText = document.getElementById("alert-inline-text");

  const resultsSection = document.getElementById("results-section");
  const resultVerdictContainer = document.getElementById("result-verdict-container");
  const resultTotalNum = document.getElementById("result-total-num");
  const resultValidationPill = document.getElementById("result-validation-pill");

  const scopeBarFill = document.getElementById("scope-bar-fill");
  const scopeScoreNum = document.getElementById("scope-score-num");
  const scopeReason = document.getElementById("scope-reason");

  const resourcesBarFill = document.getElementById("resources-bar-fill");
  const resourcesScoreNum = document.getElementById("resources-score-num");
  const resourcesReason = document.getElementById("resources-reason");

  const sourcesBarFill = document.getElementById("sources-bar-fill");
  const sourcesScoreNum = document.getElementById("sources-score-num");
  const sourcesReason = document.getElementById("sources-reason");

  const outcomesBarFill = document.getElementById("outcomes-bar-fill");
  const outcomesScoreNum = document.getElementById("outcomes-score-num");
  const outcomesReason = document.getElementById("outcomes-reason");

  const savedRowLine = document.getElementById("saved-row-line");
  const savedLineIcon = document.getElementById("saved-line-icon");
  const savedLineText = document.getElementById("saved-line-text");

  const validatorDetails = document.getElementById("validator-details");
  const validatorSummaryBadge = document.getElementById("validator-summary-badge");
  const validatorDetailsContent = document.getElementById("validator-details-content");

  const reportCard = document.getElementById("report-card");
  const reportRendered = document.getElementById("report-rendered");
  const copyReportBtn = document.getElementById("copy-report-btn");
  const downloadReportBtn = document.getElementById("download-report-btn");
  const printReportBtn = document.getElementById("print-report-btn");

  let currentReportMarkdown = "";
  let elapsedInterval = null;
  let startTime = 0;

  // Initialize
  function init() {
    setupCharCounter();
    setupChips();
    setupForm();
    setupReportActions();
    setupReset();
  }

  // 1. Character Counter
  function setupCharCounter() {
    if (!topicInput || !charCounter) return;
    function updateCounter() {
      const len = topicInput.value.length;
      charCounter.textContent = `${len} / 300`;
      if (len > 280) {
        charCounter.style.color = "var(--verdict-refine)";
        charCounter.style.fontWeight = "600";
      } else {
        charCounter.style.color = "var(--muted)";
        charCounter.style.fontWeight = "400";
      }
    }
    topicInput.addEventListener("input", updateCounter);
    updateCounter();
  }

  // 2. Example Chips
  function setupChips() {
    chipBtns.forEach(function(btn) {
      btn.addEventListener("click", function() {
        const topic = btn.getAttribute("data-topic");
        if (topic && topicInput) {
          topicInput.value = topic;
          topicInput.dispatchEvent(new Event("input"));
          topicInput.focus();
        }
      });
    });
  }

  // 3. Form Submission & Stream Handling
  function setupForm() {
    if (!form) return;
    form.addEventListener("submit", async function(e) {
      e.preventDefault();

      const topic = (topicInput ? topicInput.value.trim() : "");
      if (topic.length < 8) {
        showInlineAlert("Input Validation Error", "Research topic must be at least 8 characters long.");
        if (topicInput) topicInput.focus();
        return;
      }

      const versionInput = document.querySelector('input[name="version"]:checked');
      const version = versionInput ? versionInput.value : "V3";

      // Reset state & show progress
      startPipelineRun();

      try {
        const response = await fetch("/api/analyze-stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic: topic, version: version })
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || `Server returned HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split("\n\n");
          buffer = events.pop(); // Keep incomplete chunk in buffer

          for (const ev of events) {
            const trimmed = ev.trim();
            if (trimmed.startsWith("data: ")) {
              try {
                const data = JSON.parse(trimmed.slice(6));
                handlePipelineEvent(data);
              } catch (parseErr) {
                console.warn("Could not parse SSE JSON payload:", parseErr, trimmed);
              }
            }
          }
        }
      } catch (err) {
        stopPipelineRun();
        showInlineAlert("Execution Error", err.message || "An unexpected error occurred during pipeline execution.");
        console.error("Pipeline run error:", err);
      }
    });
  }

  function startPipelineRun() {
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Analyzing topic...";
    }
    if (resetBtn) resetBtn.style.display = "none";
    if (alertInline) alertInline.style.display = "none";
    if (resultsSection) resultsSection.style.display = "none";

    // Show stage tracker
    if (stageTrackerSection) {
      stageTrackerSection.style.display = "block";
      stageTrackerSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    // Reset all 6 stage items to pending
    for (let i = 0; i < 6; i++) {
      const row = document.getElementById(`stage-row-${i}`);
      const statusBadge = document.getElementById(`stage-status-${i}`);
      const timeSpan = document.getElementById(`stage-time-${i}`);
      if (row) {
        row.className = "stage-item";
      }
      if (statusBadge) {
        statusBadge.className = "badge badge-neutral";
        statusBadge.textContent = "Pending";
      }
      if (timeSpan) {
        timeSpan.textContent = "";
      }
    }

    // Start elapsed timer
    startTime = performance.now();
    if (trackerElapsedBadge) trackerElapsedBadge.textContent = "Elapsed: 0ms";
    clearInterval(elapsedInterval);
    elapsedInterval = setInterval(function() {
      const elapsed = Math.round(performance.now() - startTime);
      if (trackerElapsedBadge) trackerElapsedBadge.textContent = `Elapsed: ${elapsed}ms`;
    }, 100);
  }

  function stopPipelineRun() {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Analyze Topic";
    }
    if (resetBtn) resetBtn.style.display = "inline-flex";
    clearInterval(elapsedInterval);
  }

  function handlePipelineEvent(event) {
    if (event.type === "stage_update") {
      updateStage(event.stage, event.status, event.duration_ms);
    } else if (event.type === "final") {
      stopPipelineRun();
      if (event.result) {
        const totalDuration = event.result.total_duration_ms || Math.round(performance.now() - startTime);
        if (trackerElapsedBadge) trackerElapsedBadge.textContent = `Total: ${totalDuration}ms`;
        renderFinalResult(event.result);
      }
    }
  }

  function updateStage(stageIndex, status, durationMs) {
    const row = document.getElementById(`stage-row-${stageIndex}`);
    const statusBadge = document.getElementById(`stage-status-${stageIndex}`);
    const timeSpan = document.getElementById(`stage-time-${stageIndex}`);

    if (!row || !statusBadge) return;

    if (status === "active") {
      row.className = "stage-item stage-active";
      statusBadge.className = "badge badge-feasible";
      statusBadge.textContent = "Running";
    } else if (status === "done") {
      row.className = "stage-item stage-done";
      statusBadge.className = "badge badge-neutral";
      statusBadge.textContent = "Done";
      if (timeSpan && durationMs !== undefined) {
        timeSpan.textContent = `${durationMs}ms`;
      }
    } else if (status === "failed") {
      row.className = "stage-item stage-failed";
      statusBadge.className = "badge badge-rejected";
      statusBadge.textContent = "Failed";
      if (timeSpan && durationMs !== undefined) {
        timeSpan.textContent = `${durationMs}ms`;
      }
    }
  }

  // 4. Render Final Result Payload
  function renderFinalResult(res) {
    if (res.status === "rejected" || res.status === "unresearchable") {
      const title = res.status === "rejected" ? "Topic Rejection Notice" : "Topic Not Researchable";
      showInlineAlert(title, res.message || "Input could not be evaluated by the pipeline.");

      // If Google Sheet row was appended, show status line
      if (res.sheet_message && savedRowLine && savedLineText) {
        savedRowLine.style.display = "flex";
        savedRowLine.className = res.sheet_saved ? "saved-line saved-success" : "saved-line saved-notice";
        if (savedLineIcon) savedLineIcon.textContent = res.sheet_saved ? "✓" : "!";
        savedLineText.textContent = res.sheet_message;
      }
      return;
    }

    if (res.status === "success" && res.scores) {
      if (resultsSection) resultsSection.style.display = "block";

      // 1. Verdict Badge
      if (resultVerdictContainer) {
        const v = res.scores.verdict;
        let badgeClass = "badge-neutral";
        if (v === "Feasible") badgeClass = "badge-feasible";
        else if (v === "Needs Refinement") badgeClass = "badge-refine";
        else if (v === "Not Feasible") badgeClass = "badge-not-feasible";
        resultVerdictContainer.innerHTML = `<span class="badge ${badgeClass}" style="font-size: var(--text-sm); padding: 4px 10px;">${escapeHtml(v)}</span>`;
      }

      // 2. Total Score & Validation Pill
      if (resultTotalNum) {
        resultTotalNum.textContent = res.scores.total;
      }
      if (resultValidationPill) {
        resultValidationPill.innerHTML = `<span class="badge badge-feasible">Validation: Passed</span>`;
      }

      // 3. Four Criteria Bars & Reasons
      renderCriterion(res.scores.scope, scopeBarFill, scopeScoreNum, scopeReason);
      renderCriterion(res.scores.resources, resourcesBarFill, resourcesScoreNum, resourcesReason);
      renderCriterion(res.scores.sources, sourcesBarFill, sourcesScoreNum, sourcesReason);
      renderCriterion(res.scores.outcomes, outcomesBarFill, outcomesScoreNum, outcomesReason);

      // 4. Saved-row Line
      if (savedRowLine && savedLineText && res.sheet_message) {
        savedRowLine.style.display = "flex";
        savedRowLine.className = res.sheet_saved ? "saved-line saved-success" : "saved-line saved-notice";
        if (savedLineIcon) savedLineIcon.textContent = res.sheet_saved ? "✓" : "!";
        savedLineText.textContent = res.sheet_message;
      }

      // 5. Validator Panel
      renderValidatorPanel(res.validation_stages);

      // 6. Synthesis Report
      if (res.report && reportCard && reportRendered) {
        currentReportMarkdown = res.report;
        reportRendered.innerHTML = renderMarkdownSafely(res.report);
        reportCard.style.display = "block";
      }

      // Scroll to results
      resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function renderCriterion(critObj, barElem, numElem, reasonElem) {
    if (!critObj) return;
    const score = critObj.score || 0;
    const reason = critObj.reason || "";
    const pct = Math.min(Math.max(score * 20, 0), 100);

    if (numElem) {
      numElem.textContent = `${score} / 5`;
    }
    if (barElem) {
      barElem.style.width = `${pct}%`;
      barElem.className = "score-bar-fill";
      if (score >= 4) barElem.classList.add("fill-high");
      else if (score === 3) barElem.classList.add("fill-mid");
      else barElem.classList.add("fill-low");
    }
    if (reasonElem) {
      reasonElem.textContent = reason;
    }
  }

  function renderValidatorPanel(stages) {
    if (!validatorDetailsContent) return;
    if (!stages || stages.length === 0) {
      validatorDetailsContent.innerHTML = "<p>No validator sub-stages recorded.</p>";
      return;
    }

    let allPassed = true;
    let html = '<div style="display: flex; flex-direction: column; gap: var(--space-3);">';

    stages.forEach(function(s) {
      if (!s.passed) allPassed = false;
      const statusBadge = s.passed
        ? '<span class="badge badge-feasible" style="font-size: 11px;">Passed</span>'
        : '<span class="badge badge-rejected" style="font-size: 11px;">Failed</span>';

      html += `<div style="padding: var(--space-3); border: 1px solid var(--border-subtle); border-radius: var(--radius-xs); background-color: var(--surface-subtle);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <strong style="color: var(--ink); font-size: var(--text-xs);">${escapeHtml(s.stage || "Sub-stage")}</strong>
          ${statusBadge}
        </div>`;

      if (s.errors && s.errors.length > 0) {
        html += '<ul style="margin: 4px 0 0; padding-left: var(--space-4); color: var(--verdict-rejected); font-size: 11px;">';
        s.errors.forEach(function(err) {
          html += `<li>${escapeHtml(err)}</li>`;
        });
        html += '</ul>';
      } else {
        html += '<div style="font-size: 11px; color: var(--muted);">Passed with zero schema or contract violations.</div>';
      }
      html += '</div>';
    });

    html += '</div>';
    validatorDetailsContent.innerHTML = html;

    if (validatorSummaryBadge) {
      validatorSummaryBadge.className = allPassed ? "badge badge-feasible" : "badge badge-rejected";
      validatorSummaryBadge.textContent = allPassed ? "All Gates Passed" : "Validation Failed";
    }
  }

  // 5. Safe Markdown Renderer (Strictly Escapes Raw HTML First)
  function renderMarkdownSafely(text) {
    if (!text) return "";

    // Step 1: Escape all raw HTML entities first to prevent XSS
    let s = escapeHtml(text);

    // Step 2: Fenced code blocks
    s = s.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, function(_, lang, code) {
      return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Step 3: Inline code
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Step 4: Headers
    s = s.replace(/^#### (.*?)$/gm, "<h5>$1</h5>");
    s = s.replace(/^### (.*?)$/gm, "<h4>$1</h4>");
    s = s.replace(/^## (.*?)$/gm, "<h3>$1</h3>");
    s = s.replace(/^# (.*?)$/gm, "<h2>$1</h2>");

    // Step 5: Bold and Italic
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");

    // Step 6: Blockquotes
    s = s.replace(/^> (.*?)$/gm, "<blockquote>$1</blockquote>");

    // Step 7: Bullet lists
    s = s.replace(/(?:^[*-] .*(?:\n|$))+/gm, function(block) {
      const items = block.trim().split("\n").map(function(line) {
        return `<li>${line.replace(/^[*-] /, "").trim()}</li>`;
      }).join("");
      return `<ul>${items}</ul>`;
    });

    // Step 8: Numbered lists
    s = s.replace(/(?:^\d+\. .*(?:\n|$))+/gm, function(block) {
      const items = block.trim().split("\n").map(function(line) {
        return `<li>${line.replace(/^\d+\. /, "").trim()}</li>`;
      }).join("");
      return `<ol>${items}</ol>`;
    });

    // Step 9: Paragraphs (split by blank lines)
    const blocks = s.split(/\n{2,}/);
    return blocks.map(function(b) {
      const trimmed = b.trim();
      if (!trimmed) return "";
      if (trimmed.startsWith("<h") || trimmed.startsWith("<ul") || trimmed.startsWith("<ol") || trimmed.startsWith("<pre") || trimmed.startsWith("<blockquote")) {
        return trimmed;
      }
      return `<p>${trimmed.replace(/\n/g, "<br>")}</p>`;
    }).join("\n");
  }

  function escapeHtml(str) {
    if (typeof str !== "string") return String(str || "");
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // 6. Report Action Buttons
  function setupReportActions() {
    if (copyReportBtn) {
      copyReportBtn.addEventListener("click", async function() {
        if (!currentReportMarkdown) return;
        try {
          await navigator.clipboard.writeText(currentReportMarkdown);
          const origText = copyReportBtn.textContent;
          copyReportBtn.textContent = "Copied!";
          setTimeout(function() {
            copyReportBtn.textContent = origText;
          }, 2000);
        } catch (err) {
          console.error("Clipboard copy failed:", err);
        }
      });
    }

    if (downloadReportBtn) {
      downloadReportBtn.addEventListener("click", function() {
        if (!currentReportMarkdown) return;
        const blob = new Blob([currentReportMarkdown], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        const ts = new Date().toISOString().slice(0, 10);
        a.href = url;
        a.download = `ScholarScope_Feasibility_Report_${ts}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      });
    }

    if (printReportBtn) {
      printReportBtn.addEventListener("click", function() {
        window.print();
      });
    }
  }

  // 7. Reset Form
  function setupReset() {
    if (!resetBtn) return;
    resetBtn.addEventListener("click", function() {
      if (form) form.reset();
      if (topicInput) topicInput.dispatchEvent(new Event("input"));
      if (stageTrackerSection) stageTrackerSection.style.display = "none";
      if (alertInline) alertInline.style.display = "none";
      if (resultsSection) resultsSection.style.display = "none";
      resetBtn.style.display = "none";
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Analyze Topic";
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  function showInlineAlert(title, message) {
    if (!alertInline) return;
    if (alertInlineTitle) alertInlineTitle.textContent = title + ": ";
    if (alertInlineText) alertInlineText.textContent = message;
    alertInline.style.display = "flex";
    alertInline.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  document.addEventListener("DOMContentLoaded", init);
})();

