import json
from llm import call_gemini, generate_topic_analysis
from prompts import SCORING_PROMPTS
from validator import validate_scoring_output

topic = "Artificial intelligence"
analysis = generate_topic_analysis(topic)
domain = analysis.get("domain", "General")
rq = analysis.get("research_question", topic)
context_block = f"Topic Domain: {domain}\nRefined Question: {rq}"

system_prompt = SCORING_PROMPTS["V3"]
prompt = f"{system_prompt}\n\nContext Analysis:\n{context_block}\n\n<topic>\n{topic}\n</topic>"

raw_output = call_gemini(prompt, temperature=0.2, json_mode=True)
print("\n[Raw Model Output for T2 with Updated V3]:")
print(raw_output)

parsed = json.loads(raw_output.strip().strip("`").replace("json\n", ""))
print("\n[Parsed Scores]:")
print(json.dumps(parsed, indent=2))

val_stages = validate_scoring_output(parsed)
print("\n[Validator Sub-Stages]:")
for s in val_stages:
    status_str = "PASS" if s["passed"] else "FAIL"
    print(f" - {s['stage']}: {status_str} (Errors: {s['errors']})")

