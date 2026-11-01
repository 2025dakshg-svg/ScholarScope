"""Pipeline orchestrator for ScholarScope.

Executes the prompt chain across 6 distinct stages:
- Stage 0: Input Sanitization & Guardrails (Heuristics, no LLM)
- Stage 1: Topic Analysis (Gemini Flash + ANALYSIS_PROMPT)
- Stage 2: Feasibility Scoring (Gemini Flash + chosen V1/V2/V3 prompt)
- Stage 3: 3-Stage Rubric Validation (Structure, Consistency, Quality) with 1x Retry
- Stage 4: Report Generation (Gemini Flash + REPORT_PROMPT)
- Stage 5: Google Sheets Webhook Persistence (Apps Script POST)

Provides:
- run_pipeline(): Synchronous execution for test scripts and batch CLI runs
- run_pipeline_stream(): Generator yielding real-time per-stage events for SSE
"""

import time
from typing import Any, Dict, Generator, List, Optional, Tuple

from llm import generate_topic_analysis, generate_topic_scoring, generate_report
from validator import validate_scoring_output, is_all_valid, get_validation_errors
from sheets import append_to_results

PROMPT_INJECTION_PHRASES = [
    "ignore the rules",
    "give 5/5",
    "system prompt",
    "you are now",
    "disregard",
    "bypass",
    "jailbreak",
    "developer mode"
]


def check_input_stage0(topic: str) -> Tuple[bool, Optional[str]]:
    """Stage 0: Fast heuristic input check (no LLM)."""
    cleaned = topic.strip()

    if len(cleaned) < 8:
        return False, "Topic is too short. Minimum 8 characters required for a research topic."
    if len(cleaned) > 300:
        return False, "Topic exceeds maximum allowed length of 300 characters."

    non_space = [c for c in cleaned if not c.isspace()]
    letters = [c for c in non_space if c.isalpha()]
    if not letters or (len(letters) / len(non_space)) < 0.60:
        return False, "Topic must consist primarily of letters and words, not symbols or numbers."

    vowels = [c for c in letters if c.lower() in "aeiou"]
    if len(letters) >= 6 and (len(vowels) / len(letters)) < 0.15:
        return False, "Input appears to be gibberish or unpronounceable text."

    lowered = cleaned.lower()
    for phrase in PROMPT_INJECTION_PHRASES:
        if phrase in lowered:
            return False, f"Prompt injection guardrail triggered: Prohibited phrase '{phrase}' detected."

    return True, None


def run_pipeline(
    topic: str,
    version: str = "V3",
    skip_report: bool = False,
    precomputed_analysis: Optional[Dict[str, Any]] = None,
    save_to_results: bool = True
) -> Dict[str, Any]:
    """Runs the full pipeline synchronously and returns complete results."""
    final_result = None
    for event in run_pipeline_stream(
        topic,
        version=version,
        skip_report=skip_report,
        precomputed_analysis=precomputed_analysis,
        save_to_results=save_to_results
    ):
        if event.get("type") == "final":
            final_result = event.get("result")
    return final_result or {}


def run_pipeline_stream(
    topic: str,
    version: str = "V3",
    skip_report: bool = False,
    precomputed_analysis: Optional[Dict[str, Any]] = None,
    save_to_results: bool = True
) -> Generator[Dict[str, Any], None, None]:
    """
    Generator executing the 6 stages and yielding real-time progress events.
    Supports precomputed_analysis reuse and skip_report flag to conserve quota.
    """
    start_total = time.perf_counter()
    version = version.upper() if version in ["V1", "V2", "V3"] else "V3"

    stages_tracker = [
        {"name": "Check input", "status": "pending", "duration_ms": 0},
        {"name": "Understand topic", "status": "pending", "duration_ms": 0},
        {"name": "Score", "status": "pending", "duration_ms": 0},
        {"name": "Validate", "status": "pending", "duration_ms": 0},
        {"name": "Write report", "status": "pending", "duration_ms": 0},
        {"name": "Save", "status": "pending", "duration_ms": 0}
    ]

    # ----------------------------------------------------
    # Stage 0: Input Guardrails & Sanitation (No LLM)
    # ----------------------------------------------------
    stages_tracker[0]["status"] = "active"
    yield {"type": "stage_update", "stage": 0, "status": "active"}

    t0_start = time.perf_counter()
    is_valid_input, rejection_reason = check_input_stage0(topic)
    t0_ms = round((time.perf_counter() - t0_start) * 1000)
    stages_tracker[0]["duration_ms"] = t0_ms

    if not is_valid_input:
        stages_tracker[0]["status"] = "failed"
        yield {"type": "stage_update", "stage": 0, "status": "failed", "duration_ms": t0_ms}

        stages_tracker[5]["status"] = "active"
        yield {"type": "stage_update", "stage": 5, "status": "active"}

        t5_start = time.perf_counter()
        ok_save, row_num, err_save = append_to_results(
            topic=topic,
            version=version,
            scoring=None,
            validation_status="REJECTED",
            notes=rejection_reason or "Input rejected by Stage 0 guardrail"
        )
        t5_ms = round((time.perf_counter() - t5_start) * 1000)
        stages_tracker[5]["duration_ms"] = t5_ms
        stages_tracker[5]["status"] = "done" if ok_save else "failed"

        yield {"type": "stage_update", "stage": 5, "status": stages_tracker[5]["status"], "duration_ms": t5_ms}

        sheet_msg = f"Saved to Google Sheet, row {row_num}" if ok_save else f"Not saved to Google Sheet: {err_save}"

        res = {
            "status": "rejected",
            "message": rejection_reason,
            "analysis": None,
            "scores": None,
            "validation_stages": [],
            "report": None,
            "sheet_row": row_num if ok_save else None,
            "sheet_saved": ok_save,
            "sheet_message": sheet_msg,
            "stages": stages_tracker,
            "total_duration_ms": round((time.perf_counter() - start_total) * 1000)
        }
        yield {"type": "final", "result": res}
        return

    stages_tracker[0]["status"] = "done"
    yield {"type": "stage_update", "stage": 0, "status": "done", "duration_ms": t0_ms}

    # ----------------------------------------------------
    # Stage 1: Topic Analysis (Gemini Flash)
    # ----------------------------------------------------
    stages_tracker[1]["status"] = "active"
    yield {"type": "stage_update", "stage": 1, "status": "active"}

    t1_start = time.perf_counter()
    if precomputed_analysis is not None:
        analysis = precomputed_analysis
        t1_ms = 0
    else:
        analysis = generate_topic_analysis(topic)
        t1_ms = round((time.perf_counter() - t1_start) * 1000)
    stages_tracker[1]["duration_ms"] = t1_ms

    if not analysis.get("is_researchable", True):
        stages_tracker[1]["status"] = "failed"
        yield {"type": "stage_update", "stage": 1, "status": "failed", "duration_ms": t1_ms}

        ambiguities = analysis.get("ambiguities", [])
        ambiguity_str = "; ".join(ambiguities) if ambiguities else "Topic cannot be framed as a measurable research hypothesis."
        msg = f"Topic is not researchable in its current form: {ambiguity_str}"

        stages_tracker[5]["status"] = "active"
        yield {"type": "stage_update", "stage": 5, "status": "active"}

        t5_start = time.perf_counter()
        ok_save, row_num, err_save = append_to_results(
            topic=topic,
            version=version,
            scoring=None,
            validation_status="UNRESEARCHABLE",
            notes=msg
        )
        t5_ms = round((time.perf_counter() - t5_start) * 1000)
        stages_tracker[5]["duration_ms"] = t5_ms
        stages_tracker[5]["status"] = "done" if ok_save else "failed"

        yield {"type": "stage_update", "stage": 5, "status": stages_tracker[5]["status"], "duration_ms": t5_ms}

        sheet_msg = f"Saved to Google Sheet, row {row_num}" if ok_save else f"Not saved to Google Sheet: {err_save}"

        res = {
            "status": "unresearchable",
            "message": msg,
            "analysis": analysis,
            "scores": None,
            "validation_stages": [],
            "report": None,
            "sheet_row": row_num if ok_save else None,
            "sheet_saved": ok_save,
            "sheet_message": sheet_msg,
            "stages": stages_tracker,
            "total_duration_ms": round((time.perf_counter() - start_total) * 1000)
        }
        yield {"type": "final", "result": res}
        return

    stages_tracker[1]["status"] = "done"
    yield {"type": "stage_update", "stage": 1, "status": "done", "duration_ms": t1_ms}

    # ----------------------------------------------------
    # Stage 2: Feasibility Scoring (LLM)
    # ----------------------------------------------------
    stages_tracker[2]["status"] = "active"
    yield {"type": "stage_update", "stage": 2, "status": "active"}

    t2_start = time.perf_counter()
    scoring = generate_topic_scoring(topic, analysis, version=version)
    t2_ms = round((time.perf_counter() - t2_start) * 1000)
    stages_tracker[2]["duration_ms"] = t2_ms
    stages_tracker[2]["status"] = "done"
    yield {"type": "stage_update", "stage": 2, "status": "done", "duration_ms": t2_ms}

    # ----------------------------------------------------
    # Stage 3: Three-Stage Rubric Validation + 1x Retry
    # ----------------------------------------------------
    stages_tracker[3]["status"] = "active"
    yield {"type": "stage_update", "stage": 3, "status": "active"}

    t3_start = time.perf_counter()
    val_stages = validate_scoring_output(scoring)
    pipeline_notes = "Automated pipeline analysis"

    if not is_all_valid(val_stages):
        err_list = get_validation_errors(val_stages)
        correction_hint = "; ".join(err_list)
        # Attempt retry of Stage 2
        scoring_retry = generate_topic_scoring(
            topic, analysis, version=version, correction_hint=correction_hint
        )
        val_stages_retry = validate_scoring_output(scoring_retry)
        if is_all_valid(val_stages_retry):
            scoring = scoring_retry
            val_stages = val_stages_retry
            pipeline_notes = f"Validator retry triggered: {correction_hint}; Final: Passed"
        else:
            stages_tracker[3]["duration_ms"] = round((time.perf_counter() - t3_start) * 1000)
            stages_tracker[3]["status"] = "failed"
            yield {"type": "stage_update", "stage": 3, "status": "failed", "duration_ms": stages_tracker[3]["duration_ms"]}

            pipeline_notes = f"Failed rubric validation after retry: {correction_hint}"

            stages_tracker[5]["status"] = "active"
            yield {"type": "stage_update", "stage": 5, "status": "active"}

            t5_start = time.perf_counter()
            ok_save, row_num, err_save = append_to_results(
                topic=topic,
                version=version,
                scoring=scoring_retry,
                validation_status="VALIDATION_FAILED",
                notes=pipeline_notes
            )
            t5_ms = round((time.perf_counter() - t5_start) * 1000)
            stages_tracker[5]["duration_ms"] = t5_ms
            stages_tracker[5]["status"] = "done" if ok_save else "failed"
            yield {"type": "stage_update", "stage": 5, "status": stages_tracker[5]["status"], "duration_ms": t5_ms}

            sheet_msg = f"Saved to Google Sheet, row {row_num}" if ok_save else f"Not saved to Google Sheet: {err_save}"

            res = {
                "status": "validation_failed",
                "message": "Output failed rubric validation even after correction retry.",
                "analysis": analysis,
                "scores": scoring_retry,
                "validation_stages": val_stages_retry,
                "report": None,
                "sheet_row": row_num if ok_save else None,
                "sheet_saved": ok_save,
                "sheet_message": sheet_msg,
                "stages": stages_tracker,
                "total_duration_ms": round((time.perf_counter() - start_total) * 1000)
            }
            yield {"type": "final", "result": res}
            return

    t3_ms = round((time.perf_counter() - t3_start) * 1000)
    stages_tracker[3]["duration_ms"] = t3_ms
    stages_tracker[3]["status"] = "done"
    yield {"type": "stage_update", "stage": 3, "status": "done", "duration_ms": t3_ms}

    # ----------------------------------------------------
    # Stage 4: Markdown Report Generation (LLM)
    # ----------------------------------------------------
    stages_tracker[4]["status"] = "active"
    yield {"type": "stage_update", "stage": 4, "status": "active"}

    t4_start = time.perf_counter()
    if skip_report:
        report = "(Report generation skipped via --no-report flag)"
        t4_ms = 0
    else:
        report = generate_report(topic, scoring)
        t4_ms = round((time.perf_counter() - t4_start) * 1000)
    stages_tracker[4]["duration_ms"] = t4_ms
    stages_tracker[4]["status"] = "done"
    yield {"type": "stage_update", "stage": 4, "status": "done", "duration_ms": t4_ms}

    # ----------------------------------------------------
    # Stage 5: Save to Google Sheets Webhook
    # ----------------------------------------------------
    stages_tracker[5]["status"] = "active"
    yield {"type": "stage_update", "stage": 5, "status": "active"}

    if save_to_results:
        t5_start = time.perf_counter()
        ok_save, row_num, err_save = append_to_results(
            topic=topic,
            version=version,
            scoring=scoring,
            validation_status="Passed",
            notes=pipeline_notes
        )
        t5_ms = round((time.perf_counter() - t5_start) * 1000)
        stages_tracker[5]["duration_ms"] = t5_ms
        stages_tracker[5]["status"] = "done" if ok_save else "failed"
        sheet_msg = f"Saved to Google Sheet, row {row_num}" if ok_save else f"Not saved to Google Sheet: {err_save}"
    else:
        ok_save = True
        row_num = None
        err_save = None
        t5_ms = 0
        stages_tracker[5]["duration_ms"] = 0
        stages_tracker[5]["status"] = "done"
        sheet_msg = "Skipped saving to Results tab (batch test mode)"

    yield {"type": "stage_update", "stage": 5, "status": stages_tracker[5]["status"], "duration_ms": t5_ms}

    res = {
        "status": "success",
        "message": f"Topic successfully evaluated. {sheet_msg}",
        "analysis": analysis,
        "scores": scoring,
        "validation_stages": val_stages,
        "report": report,
        "sheet_row": row_num if ok_save else None,
        "sheet_saved": ok_save,
        "sheet_message": sheet_msg,
        "stages": stages_tracker,
        "total_duration_ms": round((time.perf_counter() - start_total) * 1000)
    }
    yield {"type": "final", "result": res}
