"""Three-stage rubric validator for ScholarScope.

Validates LLM scoring output against academic rubric requirements:
- Sub-stage 1 (Structure): Keys exist, types are valid, canonical verdict.
- Sub-stage 2 (Consistency): Scores in [1, 5], total == sum(scores), verdict threshold.
- Sub-stage 3 (Quality): Reason length (>= 6 words) and anti-hallucination citation checks.
"""

import re
from typing import Any, Dict, List

REQUIRED_CRITERIA = ["scope", "resources", "sources", "outcomes"]
VALID_VERDICTS = ["Feasible", "Needs Refinement", "Not Feasible"]

# Regex patterns for fabricated academic citations or links
CITATION_PATTERNS = [
    (r"\bet\s+al\.?\b", "Prohibited author citation ('et al.')"),
    (r"\[\s*(?:19|20)\d{2}\s*\]", "Prohibited year citation in brackets (e.g. [2023])"),
    (r"\(\s*(?:19|20)\d{2}\s*\)", "Prohibited year citation in parentheses (e.g. (2024))"),
    (r"https?://[^\s]+", "Prohibited URL link"),
    (r"\bdoi\s*:\s*[^\s]+", "Prohibited DOI reference"),
    (r"\barxiv\s*:\s*[^\s]+", "Prohibited arXiv identifier")
]


def validate_scoring_output(data: Any) -> List[Dict[str, Any]]:
    """Runs all 3 validation sub-stages on scoring data and returns structured results."""
    stage1 = {"stage": "Sub-stage 1: Structure", "passed": True, "errors": []}
    stage2 = {"stage": "Sub-stage 2: Consistency", "passed": True, "errors": []}
    stage3 = {"stage": "Sub-stage 3: Quality", "passed": True, "errors": []}

    # ----------------------------------------------------
    # Sub-stage 1: Structure
    # ----------------------------------------------------
    if not isinstance(data, dict):
        stage1["passed"] = False
        stage1["errors"].append("Scoring output must be a valid JSON dictionary.")
        # If not a dict, later stages cannot run
        stage2["passed"] = False
        stage2["errors"].append("Skipped due to invalid structure.")
        stage3["passed"] = False
        stage3["errors"].append("Skipped due to invalid structure.")
        return [stage1, stage2, stage3]

    for criterion in REQUIRED_CRITERIA:
        if criterion not in data:
            stage1["passed"] = False
            stage1["errors"].append(f"Missing required criterion: '{criterion}'.")
        else:
            val = data[criterion]
            if not isinstance(val, dict):
                stage1["passed"] = False
                stage1["errors"].append(f"Criterion '{criterion}' must be an object with 'score' and 'reason'.")
            else:
                if "score" not in val or not isinstance(val["score"], int) or isinstance(val["score"], bool):
                    stage1["passed"] = False
                    stage1["errors"].append(f"Criterion '{criterion}.score' must be an integer.")
                if "reason" not in val or not isinstance(val["reason"], str) or not val["reason"].strip():
                    stage1["passed"] = False
                    stage1["errors"].append(f"Criterion '{criterion}.reason' must be a non-empty string.")

    if "total" not in data or not isinstance(data["total"], int) or isinstance(data["total"], bool):
        stage1["passed"] = False
        stage1["errors"].append("Missing or invalid integer 'total' field.")

    if "verdict" not in data or not isinstance(data["verdict"], str):
        stage1["passed"] = False
        stage1["errors"].append("Missing or invalid string 'verdict' field.")
    elif data["verdict"] not in VALID_VERDICTS:
        stage1["passed"] = False
        stage1["errors"].append(
            f"Verdict '{data['verdict']}' is invalid. Must be one of: {', '.join(VALID_VERDICTS)}."
        )

    # ----------------------------------------------------
    # Sub-stage 2: Consistency
    # ----------------------------------------------------
    if stage1["passed"]:
        computed_sum = 0
        for criterion in REQUIRED_CRITERIA:
            score = data[criterion]["score"]
            if score < 1 or score > 5:
                stage2["passed"] = False
                stage2["errors"].append(f"Score for '{criterion}' ({score}) must be between 1 and 5.")
            computed_sum += score

        reported_total = data["total"]
        if reported_total != computed_sum:
            stage2["passed"] = False
            stage2["errors"].append(
                f"Arithmetic error: reported total is {reported_total}, but sum of criteria scores is {computed_sum}."
            )

        reported_verdict = data["verdict"]
        expected_verdict = (
            "Feasible" if computed_sum >= 16
            else "Needs Refinement" if computed_sum >= 11
            else "Not Feasible"
        )
        if reported_verdict != expected_verdict:
            stage2["passed"] = False
            stage2["errors"].append(
                f"Verdict mismatch: sum is {computed_sum}, which requires '{expected_verdict}', but got '{reported_verdict}'."
            )
    else:
        stage2["passed"] = False
        stage2["errors"].append("Cannot evaluate consistency due to structural errors in Sub-stage 1.")

    # ----------------------------------------------------
    # Sub-stage 3: Quality (Word count & anti-hallucination)
    # ----------------------------------------------------
    if stage1["passed"]:
        for criterion in REQUIRED_CRITERIA:
            reason = data[criterion]["reason"]
            words = reason.strip().split()
            if len(words) < 6:
                stage3["passed"] = False
                stage3["errors"].append(
                    f"Reason for '{criterion}' has only {len(words)} word(s); minimum is 6 words for academic justification."
                )

            # Check citation / link patterns
            for pattern, desc in CITATION_PATTERNS:
                if re.search(pattern, reason, flags=re.IGNORECASE):
                    stage3["passed"] = False
                    stage3["errors"].append(
                        f"Fabricated citation detected in '{criterion}': {desc}."
                    )
    else:
        stage3["passed"] = False
        stage3["errors"].append("Cannot evaluate quality due to structural errors in Sub-stage 1.")

    return [stage1, stage2, stage3]


def is_all_valid(stages: List[Dict[str, Any]]) -> bool:
    """Returns True only if all sub-stages passed."""
    return all(s["passed"] for s in stages)


def get_validation_errors(stages: List[Dict[str, Any]]) -> List[str]:
    """Flattens all error messages across failed sub-stages."""
    all_errs = []
    for s in stages:
        if not s["passed"]:
            all_errs.extend(s["errors"])
    return all_errs

