# ScholarScope: Research Topic Feasibility Analyzer
**Academic Mini Project** (20 Marks)  
**Subject:** AI Tools and Prompt Engineering  
**Student:** Daksh Ghandaat  
**Roll No:** 150096725209  
**Degree:** B.Tech Computer Science & Engineering  

---

## 1. Executive Summary & Purpose

ScholarScope is an automated research feasibility analyzer designed to help undergraduate engineering students rigorously evaluate thesis and capstone project proposals before committing an entire semester of development.

Evaluating research proposals is challenging for undergraduate students: ideas often suffer from unbounded scope (e.g. attempting to solve general AI), excessive compute/laboratory requirements (e.g. wet-lab clinical trials), or unmeasurable outcomes. ScholarScope decomposes feasibility evaluation into a deterministic **6-stage pipeline** that combines lightweight heuristic guardrails, Google Gemini Flash prompt chaining, a 3-stage programmatic rubric validator with automatic retry, and cloud persistence via Google Apps Script Web App webhooks into Google Sheets.

The application has been completely built as a **server-rendered multi-page website** served by FastAPI and Jinja2 templates without client-side frameworks, build steps, or SPA routers.

---

## 2. Multi-Page Architecture & Route Catalog

Every page in ScholarScope is its own distinct URL served by FastAPI with full page navigation, bookmarkability, and zero client-side routing dependencies:

| URL Path | Page Name | Primary Content & Behavioral Contract |
| :--- | :--- | :--- |
| **`/`** | **Home** | Calm headline, one-sentence purpose, primary CTA button, **real latest passed result** from the Google Sheets Results tab (`Validation = Passed`), 3-step guide, and operational boundaries note (*"What it will not do"*). |
| **`/analyze`** | **Analyze** | Interactive topic form (300 char counter, 5 benchmark example chips, V3/V2/V1 segmented selector), **real-time SSE stage progress tracker** with measured millisecond timings, verdict & total `/20`, 4 criterion score bars with reasons, collapsible 3-stage validator panel, sanitized Markdown report viewer (Copy, Download `.md`, Print), and saved-row line. |
| **`/how-it-works`** | **Methodology** | Vertical breakdown of the 6 pipeline stages, 3 validator gate specifications, single-retry correction rule, degraded mode fallbacks, and embedded 300 DPI architecture flowchart (`docs/workflow.png`). |
| **`/prompts`** | **Prompt Library** | Monospace blocks with copy buttons for `ANALYSIS_PROMPT`, `PROMPT_V1`, `PROMPT_V2`, `PROMPT_V3`, `REPORT_PROMPT`, and complete `PROMPT_LOG` iteration table with evolution rationale. |
| **`/tests`** | **Benchmark Tests** | 5 benchmark test cases (T1–T5) with expected vs actual results, prompt engineering version comparison matrix (V1 vs V2 vs V3), data integrity transparency notice, and complete historical log from the Tests tab. |
| **`/history`** | **History** | Clean academic table displaying the last 10 evaluation runs persisted to the Google Sheet Results tab via the Apps Script Webhook, with verdict and validation status badges. |
| **`/responsible-ai`** | **Responsible AI** | 4 ethical pillars: Human-in-the-loop oversight, zero invented citations (strict anti-hallucination checks), deterministic prompt injection defense, and immutable cloud audit logging. |
| **`*` (Any invalid URL)** | **404 Not Found** | Custom academic 404 error template returning HTTP 404 for web navigation; API paths (`/api/*`) return JSON `{"detail": "Not Found"}`. |

---

## 3. The 6-Stage Pipeline & Validator Architecture

```
+---------------------------------------------------------------------------------------------------+
|                                      SCHOLARSCOPE PIPELINE                                        |
+---------------------------------------------------------------------------------------------------+
|  [Stage 0: Input Guardrails & Sanitization] (Regex/Heuristics, No LLM Quota)                      |
|    |--> Length boundary check (8 to 300 characters)                                               |
|    |--> Alpha ratio (>60%) & vowel distribution (anti-gibberish)                                  |
|    |--> Prompt injection signatures ("ignore the rules", "give 5/5", "developer mode")            |
|    \---> [REJECTED] --> Log to Google Sheets (row recorded) & Terminate with calm inline note     |
|    \---> [VALID]                                                                                  |
|           v                                                                                       |
|  [Stage 1: Topic Understanding & Researchability] (Gemini Flash + ANALYSIS_PROMPT)                 |
|    |--> Academic summary, core scientific inquiry, key assumptions, ambiguities                   |
|    \---> [NOT RESEARCHABLE] --> Log to Google Sheets & Return specific ambiguity notice           |
|    \---> [RESEARCHABLE]                                                                           |
|           v                                                                                       |
|  [Stage 2: Feasibility Rubric Evaluation] (Gemini Flash + V1 / V2 / V3 Prompt)                    |
|    |--> 4 Rubric Pillars (1 to 5 points each; Max 20 points):                                     |
|    |      1. Scope (boundaries, 4-week undergraduate timeline)                                    |
|    |      2. Resources (1 standard laptop, free open-source tools, $0 budget)                     |
|    |      3. Sources (peer-reviewed papers, open benchmark datasets)                              |
|    |      4. Measurable Outcomes (quantitative metrics, baseline comparisons)                     |
|           v                                                                                       |
|  [Stage 3: 3-Stage Programmatic Rubric Validation] (validator.py, No LLM Judge)                   |
|    |--> Sub-stage 1: Structure (JSON dictionary, keys present, integer types, bounds [1, 5])      |
|    |--> Sub-stage 2: Consistency (Sum == Total, Total -> Canonical Verdict mapping)                |
|    |--> Sub-stage 3: Quality / Anti-Hallucination (Justifications cite Stage 1 text; no fake DOIs)|
|    \---> [FAIL] --> Automatic Single Retry (1x) with targeted diagnostic correction hint          |
|    \---> [PASS]                                                                                   |
|           v                                                                                       |
|  [Stage 4: Feasibility Report Synthesis] (Gemini Flash + REPORT_PROMPT)                           |
|    |--> Executive summary, strengths, challenges, next steps, recommended readings                |
|           v                                                                                       |
|  [Stage 5: Google Sheets Cloud Persistence] (Google Apps Script Web App Webhook)                  |
|    |--> Appends immutable 11-column record to Google Sheet ('Results' or 'Tests' tab)             |
|    \---> UI: "Saved to Google Sheet, row N" (or honest fallback status message)                   |
+---------------------------------------------------------------------------------------------------+
```

---

## 4. Academic Rubric & Scoring Anchors

The scoring engine evaluates proposals across four criteria, each scored on a 1 to 5 scale (Total: 4 to 20):

| Criterion | Score 1 (Impractical / Out of Scope) | Score 3 (Needs Refinement / Moderate) | Score 5 (Feasible / Well-Calibrated) |
| :--- | :--- | :--- | :--- |
| **Scope** | Vague, unbounded, requires multi-year PhD research (e.g., *"Artificial intelligence"*). | Manageable topic but boundary conditions are blurry; requires clear scope delimitations. | Tight, well-defined problem achievable by an undergraduate within a 4-week development period. |
| **Resources** | Requires wet labs, clinical trials, supercomputing clusters, or thousands of dollars. | Requires mid-tier GPUs or non-standard datasets with modest setup friction. | Runs comfortably on a standard student laptop using free, open-source libraries and public data. |
| **Sources** | Obscure topic, proprietary trade secrets, classified datasets, or zero academic literature. | Emerging topic with preprints or blog posts, but few indexed peer-reviewed studies. | Abundant peer-reviewed literature (IEEE, ACM, arXiv) and established public benchmarks. |
| **Outcomes** | Purely qualitative, subjective, or speculative with no possible quantitative validation. | Indirect metrics or proxies; difficult to establish a formal baseline comparison. | Quantitative metrics (e.g. Accuracy, F1-score, Latency, BLEU) compared against an established baseline. |

### Canonical Verdict Thresholds
- **Feasible:** $\text{Total} \ge 16$
- **Needs Refinement:** $11 \le \text{Total} \le 15$
- **Not Feasible:** $\text{Total} \le 10$

---

## 5. Prompt Engineering Iterations (V1 vs V2 vs V3)

The evaluation prompt evolved through three distinct iterations to resolve real LLM failure modes:

| Dimension | Version 1 (Baseline) | Version 2 (Few-Shot Calibrated) | Version 3 (Production Anchored) |
| :--- | :--- | :--- | :--- |
| **Technique** | Zero-shot directive prompting with generic instructions. | 1 few-shot calibrated example in prompt body. | Domain-separated few-shot anchor with explicit negative constraints. |
| **Anchor Topic** | None (model relied on internal training bias). | Topic was *"Sentiment analysis of student feedback"* (collided directly with test case T1). | Topic changed to *"IoT soil moisture sensor"* (completely distinct domain, zero leakage). |
| **Few-Shot Leakage** | None. | **High vulnerability:** Model memorized exact scores for T1 rather than evaluating. | **Zero leakage:** Rigorously validated across NLP, computer vision, embedded systems, and civil topics. |
| **Undergraduate Bounds** | Vague 1–5 range without realistic constraints. | Anchor points defined for 1, 3, 5 across all 4 criteria. | Strictly anchored: 4 weeks time horizon, 8GB laptop RAM, open-access papers only. |
| **Anti-Hallucination Gate** | None (unstructured reasons permitted). | Required reasoning strings for each criterion. | Validator Gate 3 verifies reasons cite exact phrases from Stage 1 analysis; prohibits fake citations. |
| **Output Schema** | Loose JSON (frequent trailing markdown fences). | Strict JSON object schema enforced in prompt text. | Pydantic-compliant raw JSON with deterministic 3-stage validation and single retry. |

---

## 6. Design System & Frontend Architecture

The user interface follows the **"Warm Editorial"** design system inspired by academic research publications:

- **Typography:** Newsreader serif for titles and headings; Inter for interface elements; tabular figures (`tabular-nums`) for numeric scores.
- **Palette:** Paper background (`#F6F3EC` canvas / `#161715` dark), deep forest green accent (`#1F4D3F` / `#4FA888`), ink text (`#1B1B1A` / `#ECEAE4`), hairline borders (`#DDD8CD` / `#2C2D2A`).
- **Responsive Viewports:** Tested and verified from 360px mobile to 1440px desktop.
- **Accessibility:** Skip-to-content landmark, semantic HTML5 tags, visible focus rings with 2px offset, WCAG AA contrast compliance, and full `prefers-reduced-motion` support.
- **Vanilla Controllers:** Separated modular scripts:
  - `static/js/theme.js`: Dark/light toggle with `localStorage` and `?theme=` query param.
  - `static/js/nav.js`: Accessible mobile navigation toggle.
  - `static/js/copy.js`: Monospace code copy utility with 2s feedback.
  - `static/js/analyze.js`: SSE stream reader, stage updater, safe Markdown renderer, report copy/download/print.
- **Print Optimization:** `static/css/print.css` strips navigation headers, footers, and buttons, allowing clean report printing or PDF export.

---

## 7. Security, In-Memory Caching & Anti-XSS

1. **Jinja2 Autoescaping:** Enabled by default. **Never uses `| safe`** on user topics, Google Sheets data, or diagnostic notes.
2. **Safe Markdown Rendering:** In `analyze.js`, all raw HTML characters (`&`, `<`, `>`, `"`, `'`) are strictly converted to character entities *before* regex transforms for markdown elements, guaranteeing zero script injection or XSS execution.
3. **In-Memory Caching (60s TTL):** Home (`/`), History (`/history`), and Tests (`/tests`) implement a 60-second in-memory cache for Google Sheets read-backs. This avoids Apps Script rate limits and delivers sub-10ms response times on page reloads.
4. **Backend Secrets Isolation:** API keys (`GEMINI_API_KEY`) and webhook secrets (`APPS_SCRIPT_SECRET`) reside exclusively in the backend `.env` file and are never passed to templates or static client assets.

---

## 8. Verification & Test Suite

The codebase includes an automated regression test suite:

```bash
# Run route and security regression test suite
python test_routes.py

# Run isolated validator retry unit test
python test_validator_retry.py

# Run Google Apps Script webhook connectivity check
python test_webhook.py
```

### Route Test Suite (`test_routes.py`) Coverage:
- ✓ All 7 HTML routes (`/`, `/analyze`, `/how-it-works`, `/prompts`, `/tests`, `/history`, `/responsible-ai`) return HTTP 200.
- ✓ Custom 404 page returns HTTP 404 with styled academic HTML for web routes; `/api/*` returns JSON `{"detail": "Not Found"}`.
- ✓ Core static assets (`logo.svg`, `favicon.svg`, `tokens.css`, `style.css`, `print.css`, `theme.js`, `nav.js`, `analyze.js`) return HTTP 200.
- ✓ Core REST API endpoints (`/api/health`, `/api/prompts`, `/api/history`, `/api/tests`) return valid JSON.
- ✓ Strict security verification: No API keys or webhook secrets leaked into HTML or static assets.

---

## 9. Local Installation & Reproduction Guide

### Prerequisites
- Python 3.11+
- Google Gemini API key ([Google AI Studio](https://aistudio.google.com/))
- Google Sheet with Google Apps Script Web App deployed

### Setup Steps
```bash
# 1. Clone repository and navigate to folder
git clone https://github.com/2025dakshg-svg/ScholarScope.git
cd ScholarScope

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install minimal dependencies
pip install -r requirements.txt

# 4. Configure environment variables in .env
cp .env.example .env
# Edit .env with your real GEMINI_API_KEY, GEMINI_MODEL, APPS_SCRIPT_URL, APPS_SCRIPT_SECRET

# 5. Start the web application
uvicorn main:app --port 8000 --reload

# 6. Run regression test suite
python test_routes.py
```

Open your browser at `http://127.0.0.1:8000` to view the multi-page website.
