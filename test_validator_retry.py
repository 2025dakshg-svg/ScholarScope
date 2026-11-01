"""Unit test for pipeline validator retry mechanism.

Uses an isolated test stub exclusively within this file to:
1. Return an invalid scoring output on the first attempt (arithmetic inconsistency)
2. Verify that Stage 3 detects the error and triggers a retry of Stage 2 with correction hint
3. Return a valid scoring output on the second attempt
4. Assert that the pipeline's Notes field explicitly records the retry reason
"""

import pipeline


def test_validator_retry_mechanism():
    print("=================================================================")
    print("RUNNING test_validator_retry.py (Isolated Model Stub)")
    print("=================================================================")

    call_count = 0
    captured_hints = []

    # Isolated stub defined ONLY inside this test file
    def stub_generate_topic_scoring(topic, analysis, version="V3", correction_hint=None):
        nonlocal call_count
        call_count += 1
        captured_hints.append(correction_hint)

        if call_count == 1:
            print("[Stub Call 1]: Deliberately returning inconsistent scores (total=12, sum=17)...")
            return {
                "scope": {"score": 4, "reason": "The topic scope is well bounded for an undergraduate project."},
                "resources": {"score": 5, "reason": "Doable on a standard personal laptop with free tooling."},
                "sources": {"score": 4, "reason": "Sufficient literature and open academic datasets exist."},
                "outcomes": {"score": 4, "reason": "Measurable classification accuracy and precision metrics."},
                "total": 12,  # Arithmetic error: 4 + 5 + 4 + 4 = 17 != 12
                "verdict": "Needs Refinement"
            }
        else:
            print(f"[Stub Call 2]: Received correction hint -> '{correction_hint}'")
            print("[Stub Call 2]: Returning corrected valid scores (total=17)...")
            return {
                "scope": {"score": 4, "reason": "The topic scope is well bounded for an undergraduate project."},
                "resources": {"score": 5, "reason": "Doable on a standard personal laptop with free tooling."},
                "sources": {"score": 4, "reason": "Sufficient literature and open academic datasets exist."},
                "outcomes": {"score": 4, "reason": "Measurable classification accuracy and precision metrics."},
                "total": 17,  # Corrected sum
                "verdict": "Feasible"
            }

    # Stub analysis and report to avoid external network calls during this unit test
    def stub_analysis(topic):
        return {
            "domain": "Natural Language Processing",
            "research_question": "Can sentiment analysis be performed on student feedback using Python?",
            "is_researchable": True,
            "ambiguities": []
        }

    def stub_report(topic, scoring):
        return "## Summary\nValid feasibility report generated after successful retry."

    # Monkeypatch strictly for this unit test
    original_scoring = pipeline.generate_topic_scoring
    original_analysis = pipeline.generate_topic_analysis
    original_report = pipeline.generate_report

    pipeline.generate_topic_scoring = stub_generate_topic_scoring
    pipeline.generate_topic_analysis = stub_analysis
    pipeline.generate_report = stub_report

    try:
        topic = "Sentiment analysis of student feedback using Python"
        result = run_pipeline_with_captured_notes(topic)

        print("\n[Assertions & Verifications]:")
        assert call_count == 2, f"Expected 2 calls to scoring, but got {call_count}"
        print(f"✓ Model stub was invoked exactly twice (Attempt 1 + Attempt 2 Retry).")

        assert captured_hints[0] is None, "First call should have no correction hint"
        assert captured_hints[1] is not None, "Second call must receive a correction hint"
        print(f"✓ Second call received correction hint: '{captured_hints[1]}'")

        notes = result["notes"]
        print(f"\n[Recorded Notes Field]:")
        print(f"\"{notes}\"")

        assert "Validator retry triggered" in notes, "Notes must indicate retry was triggered"
        assert "Arithmetic error" in notes, "Notes must contain the specific reason for retry"
        assert "Final: Passed" in notes, "Notes must indicate final outcome"
        print("✓ Pipeline Notes field successfully recorded the retry reason and outcome!")

        assert result["status"] == "success", f"Expected success, got {result['status']}"
        print("✓ Pipeline completed successfully after retry.")

        print("\n=================================================================")
        print("🎉 ALL RETRY UNIT TESTS PASSED SUCCESSFULLY!")
        print("=================================================================")

    finally:
        # Restore originals
        pipeline.generate_topic_scoring = original_scoring
        pipeline.generate_topic_analysis = original_analysis
        pipeline.generate_report = original_report


def run_pipeline_with_captured_notes(topic):
    """Runs pipeline and intercepts the exact notes passed to sheets.append_to_results."""
    captured = {}
    original_append = pipeline.append_to_results

    def spy_append(topic, version, scoring, validation_status, notes):
        captured["notes"] = notes
        captured["status"] = validation_status
        # Call original or return dummy row to avoid polluting sheet
        return True, 999, None

    pipeline.append_to_results = spy_append
    try:
        res = pipeline.run_pipeline(topic, version="V3")
        res["notes"] = captured.get("notes", "")
        return res
    finally:
        pipeline.append_to_results = original_append


if __name__ == "__main__":
    test_validator_retry_mechanism()

