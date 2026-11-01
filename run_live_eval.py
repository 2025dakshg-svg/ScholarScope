"""Script to run live evaluations for items 4 and 5.

Performs:
1. T1 with V3: Raw Gemini output, parsed scores, verdict, 3 validator stages, real sheet row.
2. T2 ("Artificial intelligence") with V2 and V3: Compares reasons against worked example.
"""

import json
from pipeline import run_pipeline
from llm import call_gemini, generate_topic_analysis, generate_topic_scoring, get_api_key
from validator import validate_scoring_output, is_all_valid
from prompts import ANALYSIS_PROMPT, SCORING_PROMPTS, PROMPT_V3
from sheets import append_to_results


def run_item_4():
    print("=================================================================")
    print("ITEM 4: Running real pipeline on T1 ('Sentiment analysis...') with V3")
    print("=================================================================")
    topic = "Sentiment analysis of student feedback using Python"

    # Step 1: Analysis
    analysis = generate_topic_analysis(topic)
    print("\n[Stage 1 Analysis Output]:")
    print(json.dumps(analysis, indent=2))

    # Step 2: Raw Gemini scoring call
    system_prompt = SCORING_PROMPTS["V3"]
    context_block = f"Topic Domain: {analysis.get('domain', 'General')}\nRefined Question: {analysis.get('research_question', topic)}"
    prompt = f"{system_prompt}\n\nContext Analysis:\n{context_block}\n\n<topic>\n{topic}\n</topic>"

    print("\n[Stage 2: RAW GEMINI API RESPONSE BEFORE PARSING]:")
    raw_response = call_gemini(prompt, temperature=0.2, json_mode=True)
    print(raw_response)

    # Step 3: Parsed scores & verdict
    scoring_data = json.loads(raw_response.strip().strip("`").replace("json\n", ""))
    print("\n[Parsed Scores]:")
    print(json.dumps(scoring_data, indent=2))
    print(f"Total: {scoring_data.get('total')} / 20")
    print(f"Verdict: {scoring_data.get('verdict')}")

    # Step 4: Validator sub-stages
    val_stages = validate_scoring_output(scoring_data)
    print("\n[Validator Sub-Stage Results]:")
    for s in val_stages:
        status_symbol = "PASS" if s["passed"] else "FAIL"
        print(f" - {s['stage']}: {status_symbol} (Errors: {s['errors']})")

    # Step 5: Save to Sheet
    ok, row_num, err = append_to_results(
        topic=topic,
        version="V3",
        scoring=scoring_data,
        validation_status="Passed",
        notes="Item 4 live verification run"
    )
    print(f"\n[Google Sheet Append Result]:")
    print(f"Saved: {ok}, Row Number: {row_num}, Error: {err}")


def run_item_5():
    print("\n=================================================================")
    print("ITEM 5: Comparing T2 ('Artificial intelligence') on V2 vs V3")
    print("=================================================================")
    topic = "Artificial intelligence"
    analysis = generate_topic_analysis(topic)

    # V2 scoring
    prompt_v2 = f"{SCORING_PROMPTS['V2']}\n\n<topic>\n{topic}\n</topic>"
    raw_v2 = call_gemini(prompt_v2, temperature=0.2, json_mode=True)
    parsed_v2 = json.loads(raw_v2.strip().strip("`").replace("json\n", ""))

    # V3 scoring
    prompt_v3 = f"{SCORING_PROMPTS['V3']}\n\n<topic>\n{topic}\n</topic>"
    raw_v3 = call_gemini(prompt_v3, temperature=0.2, json_mode=True)
    parsed_v3 = json.loads(raw_v3.strip().strip("`").replace("json\n", ""))

    print("\n[V2 Reasons]:")
    for crit in ["scope", "resources", "sources", "outcomes"]:
        print(f" - {crit} ({parsed_v2.get(crit, {}).get('score')}): {parsed_v2.get(crit, {}).get('reason')}")

    print("\n[V3 Reasons]:")
    for crit in ["scope", "resources", "sources", "outcomes"]:
        print(f" - {crit} ({parsed_v3.get(crit, {}).get('score')}): {parsed_v3.get(crit, {}).get('reason')}")

    # The worked example in PROMPT_V3
    worked_example_reasons = {
        "scope": "The topic covers an entire field, so no single project can address it.",
        "resources": "Depends on which sub-area is chosen; some need heavy compute.",
        "sources": "Very large amount of literature exists, though it needs filtering.",
        "outcomes": "No specific metric can be defined without a narrower question."
    }

    print("\n[Comparison with PROMPT_V3 Worked Example]:")
    for crit in ["scope", "resources", "sources", "outcomes"]:
        v3_reason = parsed_v3.get(crit, {}).get("reason", "").strip()
        example_reason = worked_example_reasons[crit].strip()
        is_identical = (v3_reason == example_reason)
        print(f"Criterion '{crit}':")
        print(f"  Worked Example : \"{example_reason}\"")
        print(f"  V3 Model Output: \"{v3_reason}\"")
        print(f"  Exact Match?    : {is_identical}")


if __name__ == "__main__":
    if not get_api_key():
        print("ERROR: GEMINI_API_KEY is not set in .env. Please save your key in .env.")
    else:
        run_item_4()
        run_item_5()

