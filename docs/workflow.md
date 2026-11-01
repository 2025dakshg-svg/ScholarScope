# ScholarScope Workflow & Architecture Diagram

This document illustrates the end-to-end multi-stage prompt chain pipeline of **ScholarScope**, including the heuristic guardrails, LLM calls, 3-stage programmatic rubric validator, retry loops, and automated Google Sheets persistence.

---

## 1. Visual Flowchart (Publication-Grade PNG)

![ScholarScope Workflow](workflow.png)

*High-resolution export generated at `docs/workflow.png` (white background, Oxford green accent, readable typography).*

---

## 2. Mermaid Interactive Flowchart

```mermaid
flowchart TD
    Start(["User Submits Research Topic<br/>(8 to 300 characters)"]) --> S0["<b>Stage 0: Input Sanitization & Guardrails</b><br/>• Length Check (8 - 300 chars)<br/>• Non-letter / Symbol Ratio Check<br/>• Vowel Ratio / Gibberish Check<br/>• Prompt-Injection Filter ('ignore the rules', 'give 5/5')"]
    
    S0 -- Fails (Adversarial / Invalid) --> Rej["<b>Log to Google Sheet (REJECTED)</b><br/>• Saves row via Apps Script Webhook<br/>• UI displays calm inline rejection explanation<br/>• Returns row proof: 'Saved to Google Sheet, row N'"]
    
    S0 -- Passes --> S1["<b>Stage 1: Topic Analysis</b><br/>• Gemini Flash + ANALYSIS_PROMPT<br/>• Extracts: domain, refined question, ambiguities<br/>• Evaluates: is_researchable boolean"]
    
    S1 --> CheckRes{"is_researchable?"}
    CheckRes -- No --> Unres["<b>Log to Google Sheet (UNRESEARCHABLE)</b><br/>• Saves row with ambiguities<br/>• Stops early with friendly guidance"]
    
    CheckRes -- Yes --> S2["<b>Stage 2: Feasibility Scoring</b><br/>• Gemini Flash + Chosen Version (V1 / V2 / V3)<br/>• Scores 4 criteria (Scope, Resources, Sources, Outcomes) 1 to 5<br/>• Computes total & derives canonical verdict"]
    
    S2 --> S3["<b>Stage 3: Three-Stage Rubric Validator</b><br/>• Sub-stage 1: Structure & canonical verdict<br/>• Sub-stage 2: Consistency (1-5 range, sum equality, verdict threshold)<br/>• Sub-stage 3: Quality (min 6 words, anti-hallucination citation check)"]
    
    S3 -- Failed (1st attempt) --> Retry["<b>Retry Stage 2 Once</b><br/>• Appends validation error summary as correction hint<br/>• Records retry reason in Notes column"]
    Retry --> S3
    
    S3 -- Failed (2nd attempt) --> ValFail["<b>Log VALIDATION_FAILED</b><br/>• Saves to Google Sheet with failure notes<br/>• Halts pipeline gracefully"]
    
    S3 -- All 3 Sub-stages Passed --> S4["<b>Stage 4: Feasibility Report Generation</b><br/>• Gemini Flash + REPORT_PROMPT<br/>• Generates clean Markdown: Summary, Scores Table, Risks, Improvements, Final Verdict"]
    
    S4 --> S5["<b>Stage 5: Google Sheets Webhook Persistence</b><br/>• HTTP POST to Google Apps Script Webhook<br/>• Appends exact 11 columns to Results tab<br/>• Returns verified Sheet Row N"]
    
    S5 --> End(["<b>UI Renders Live Evaluation</b><br/>• Verdict badge & large total score<br/>• 4 Criterion progress bars & reasons<br/>• Collapsible validator sub-stage inspector<br/>• Rendered Markdown report with Copy & Download<br/>• Real row indicator: 'Saved to Google Sheet, row N'"])

    classDef stage fill:#FFFFFF,stroke:#1F4D3F,stroke-width:2px,color:#1B1B1A;
    classDef branch fill:#FFF9EE,stroke:#B58B2E,stroke-width:1.5px,color:#1B1B1A;
    classDef fail fill:#FFF5F5,stroke:#B5523B,stroke-width:1.5px,color:#1B1B1A;
    classDef done fill:#F4F6F4,stroke:#1F4D3F,stroke-width:2px,color:#1F4D3F;

    class S0,S1,S2,S3,S4,S5 stage;
    class Retry,CheckRes branch;
    class Rej,Unres,ValFail fail;
    class Start,End done;
```

---

## 3. Sequence Diagram (Data Flow & Time Tracking)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Web Frontend (SPA)
    participant Pipeline as pipeline.py
    participant LLM as llm.py (Gemini Flash)
    participant Validator as validator.py
    participant Sheets as sheets.py (Apps Script)
    participant GoogleSheet as Google Sheet (Results Tab)

    User->>UI: Enters topic & clicks "Analyze topic"
    UI->>Pipeline: POST /api/analyze {topic, version}
    
    Note over Pipeline: Stage 0: Input Guardrails (No LLM)
    alt Invalid Input or Injection Attempt
        Pipeline->>Sheets: save_row("Results", row_data_rejected)
        Sheets->>GoogleSheet: POST {secret, tab, row}
        GoogleSheet-->>Sheets: {"ok": true, "row": N}
        Sheets-->>Pipeline: (True, N, None)
        Pipeline-->>UI: {status: "rejected", message, sheet_row: N}
    else Valid Input
        Note over Pipeline: Stage 1: Topic Understanding
        Pipeline->>LLM: generate_topic_analysis(topic)
        LLM-->>Pipeline: {domain, research_question, is_researchable, ambiguities}
        
        Note over Pipeline: Stage 2: Scoring
        Pipeline->>LLM: generate_topic_scoring(topic, analysis, version)
        LLM-->>Pipeline: {scope, resources, sources, outcomes, total, verdict}
        
        Note over Pipeline: Stage 3: Rubric Validation
        Pipeline->>Validator: validate_scoring_output(scoring)
        alt Validation Fails
            Note over Pipeline: Retry Loop (1x)
            Pipeline->>LLM: generate_topic_scoring(..., correction_hint)
            LLM-->>Pipeline: corrected_scoring
            Pipeline->>Validator: validate_scoring_output(corrected_scoring)
        end
        
        Note over Pipeline: Stage 4: Report Synthesis
        Pipeline->>LLM: generate_report(topic, scoring)
        LLM-->>Pipeline: markdown_report
        
        Note over Pipeline: Stage 5: Webhook Persistence
        Pipeline->>Sheets: append_to_results(topic, version, scoring, "Passed", notes)
        Sheets->>GoogleSheet: POST {secret, tab: "Results", row: 11_cols}
        GoogleSheet-->>Sheets: {"ok": true, "row": N}
        Sheets-->>Pipeline: (True, N, None)
        
        Pipeline-->>UI: {status: "success", scores, validator_stages, report, sheet_row: N, stages}
        UI->>User: Displays animated stage tracker, verdict, criteria cards, report, "Saved to Google Sheet, row N"
    end
```

