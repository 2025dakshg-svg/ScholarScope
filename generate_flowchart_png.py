"""Generates a high-resolution, publication-grade PNG flowchart of the pipeline.

Features:
- Pure white background (#FFFFFF)
- Large, crystal-clear readable text
- Oxford forest green (#1F4D3F) and charcoal ink (#1B1B1A) palette
- Clear visualization of:
  1) Stage 0 reject branch
  2) Stage 1 not-researchable branch
  3) Stage 3 validator retry loop
  4) Stage 5 sheet-save step
  5) Stage 5 'Not saved to Google Sheet' webhook failure path
- Exports directly to docs/workflow.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches


def draw_flowchart():
    fig, ax = plt.subplots(figsize=(15, 17), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    # Dimensions
    w = 0.52
    h = 0.072

    stages = [
        {"y": 0.91, "num": "USER INPUT", "title": "Research Topic Input (Form / Textarea)", "sub": "Topic string bounded between 8 and 300 characters", "color": "#F4F6F4", "border": "#1F4D3F"},
        {"y": 0.78, "num": "STAGE 0", "title": "Input Sanitization & Heuristic Guardrails", "sub": "Checks: Length, vowel ratio, symbol ratio, prompt injection phrases", "color": "#FFFFFF", "border": "#1F4D3F"},
        {"y": 0.64, "num": "STAGE 1", "title": "Topic Understanding & Analysis (Gemini Flash)", "sub": "ANALYSIS_PROMPT -> Extracts domain, research question, is_researchable", "color": "#FFFFFF", "border": "#1F4D3F"},
        {"y": 0.50, "num": "STAGE 2", "title": "Feasibility Scoring (Gemini Flash + V1/V2/V3)", "sub": "Scores 4 criteria (Scope, Resources, Sources, Outcomes) on 1-5 scale", "color": "#FFFFFF", "border": "#1F4D3F"},
        {"y": 0.36, "num": "STAGE 3", "title": "Three-Stage Programmatic Rubric Validator", "sub": "Checks: 1) Structure/schema, 2) Consistency (math & verdict), 3) Quality", "color": "#FFFFFF", "border": "#1F4D3F"},
        {"y": 0.22, "num": "STAGE 4", "title": "Feasibility Report Generation (Gemini Flash)", "sub": "REPORT_PROMPT -> Synthesizes Markdown summary, table, risks, next steps", "color": "#FFFFFF", "border": "#1F4D3F"},
        {"y": 0.08, "num": "STAGE 5", "title": "Automated Google Sheets Webhook Persistence", "sub": "POST to Apps Script -> Appends 11 columns to Results tab", "color": "#F4F6F4", "border": "#1F4D3F"},
    ]

    for s in stages:
        rect = patches.FancyBboxPatch(
            (0.50 - w/2, s["y"] - h/2), w, h,
            boxstyle="round,pad=0.015,rounding_size=0.015",
            facecolor=s["color"],
            edgecolor=s["border"],
            linewidth=2.0
        )
        ax.add_patch(rect)

        # Stage header tag
        ax.text(
            0.50 - w/2 + 0.02, s["y"] + 0.018, s["num"],
            fontsize=11, fontweight="bold", color="#1F4D3F", fontfamily="sans-serif"
        )
        # Stage title
        ax.text(
            0.50 - w/2 + 0.02, s["y"] - 0.003, s["title"],
            fontsize=13, fontweight="bold", color="#1B1B1A", fontfamily="sans-serif"
        )
        # Stage subtitle
        ax.text(
            0.50 - w/2 + 0.02, s["y"] - 0.023, s["sub"],
            fontsize=10, color="#555552", fontfamily="sans-serif"
        )

    # Downward Arrows between main stages
    for i in range(len(stages) - 1):
        y_top = stages[i]["y"] - h/2
        y_bot = stages[i+1]["y"] + h/2
        ax.annotate(
            "", xy=(0.50, y_bot), xytext=(0.50, y_top),
            arrowprops=dict(arrowstyle="-|>", color="#1F4D3F", lw=2.2, mutation_scale=18)
        )

    # 1. Side Branch: Stage 0 Rejection
    rect_rej = patches.FancyBboxPatch(
        (0.80, 0.78 - h/2), 0.17, h,
        boxstyle="round,pad=0.015,rounding_size=0.015",
        facecolor="#FFF5F5", edgecolor="#B5523B", linewidth=1.8
    )
    ax.add_patch(rect_rej)
    ax.text(0.885, 0.78 + 0.012, "INPUT REJECTED", fontsize=10.5, fontweight="bold", color="#B5523B", ha="center")
    ax.text(0.885, 0.78 - 0.010, "Log to Sheet (REJECTED)\nShow calm inline feedback", fontsize=8.5, color="#662211", ha="center")

    ax.annotate(
        "Adversarial / Invalid", xy=(0.80, 0.78), xytext=(0.50 + w/2, 0.78),
        arrowprops=dict(arrowstyle="-|>", color="#B5523B", lw=1.8, mutation_scale=15),
        fontsize=9, color="#B5523B", fontweight="bold", va="bottom", ha="center"
    )

    # 2. Side Branch: Stage 1 Not Researchable
    rect_unres = patches.FancyBboxPatch(
        (0.80, 0.64 - h/2), 0.17, h,
        boxstyle="round,pad=0.015,rounding_size=0.015",
        facecolor="#FFF9EE", edgecolor="#B58B2E", linewidth=1.8
    )
    ax.add_patch(rect_unres)
    ax.text(0.885, 0.64 + 0.012, "UNRESEARCHABLE", fontsize=10.5, fontweight="bold", color="#B58B2E", ha="center")
    ax.text(0.885, 0.64 - 0.010, "Log UNRESEARCHABLE\nReturn advice & stop", fontsize=8.5, color="#554411", ha="center")

    ax.annotate(
        "is_researchable=False", xy=(0.80, 0.64), xytext=(0.50 + w/2, 0.64),
        arrowprops=dict(arrowstyle="-|>", color="#B58B2E", lw=1.8, mutation_scale=15),
        fontsize=9, color="#B58B2E", fontweight="bold", va="bottom", ha="center"
    )

    # 3. Retry Loop: Stage 3 to Stage 2
    ax.annotate(
        "", xy=(0.50 - w/2, 0.50), xytext=(0.50 - w/2, 0.36),
        arrowprops=dict(
            arrowstyle="-|>", color="#B58B2E", lw=2.2,
            connectionstyle="arc3,rad=0.6", mutation_scale=18
        )
    )
    ax.text(
        0.09, 0.43, "Validation Failed (1st try)\nRetry Stage 2 once with schema hint\n[Write retry reason in Notes]",
        fontsize=9.5, fontweight="bold", color="#B58B2E", ha="center", va="center",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFFDF7", edgecolor="#B58B2E", lw=1.2)
    )

    # 4. Success Path: Saved to Google Sheet
    rect_saved = patches.FancyBboxPatch(
        (0.50 - 0.22, 0.01), 0.44, 0.035,
        boxstyle="round,pad=0.008,rounding_size=0.01",
        facecolor="#EBF4F0", edgecolor="#1F4D3F", linewidth=1.5
    )
    ax.add_patch(rect_saved)
    ax.text(0.50, 0.027, "SUCCESS: UI shows 'Saved to Google Sheet, row N'", fontsize=10, fontweight="bold", color="#1F4D3F", ha="center")

    # 5. Side Branch: Stage 5 Webhook Failure ("Not saved to Google Sheet")
    rect_sheet_fail = patches.FancyBboxPatch(
        (0.80, 0.08 - h/2), 0.17, h,
        boxstyle="round,pad=0.015,rounding_size=0.015",
        facecolor="#FFF5F5", edgecolor="#B5523B", linewidth=1.8
    )
    ax.add_patch(rect_sheet_fail)
    ax.text(0.885, 0.08 + 0.012, "WEBHOOK FAILED", fontsize=10.5, fontweight="bold", color="#B5523B", ha="center")
    ax.text(0.885, 0.08 - 0.010, "UI shows calm warning:\n'Not saved to Google Sheet:\n<reason>' (row: None)", fontsize=8, color="#662211", ha="center")

    ax.annotate(
        "ok: false / network error", xy=(0.80, 0.08), xytext=(0.50 + w/2, 0.08),
        arrowprops=dict(arrowstyle="-|>", color="#B5523B", lw=1.8, mutation_scale=15),
        fontsize=8.5, color="#B5523B", fontweight="bold", va="bottom", ha="center"
    )

    # Title Banner at Top
    ax.text(
        0.50, 0.985, "ScholarScope — Complete Pipeline Architecture & Data Flow",
        fontsize=18, fontweight="bold", color="#1B1B1A", ha="center", fontfamily="serif"
    )
    ax.text(
        0.50, 0.962, "B.Tech AI Tools & Prompt Engineering Mini Project (Daksh Ghandaat, 150096725209)",
        fontsize=11.5, color="#6B6860", ha="center", fontfamily="sans-serif"
    )

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis('off')

    plt.tight_layout()
    plt.savefig("docs/workflow.png", dpi=300, facecolor='#FFFFFF', bbox_inches='tight')
    plt.close()
    print("✓ Successfully updated docs/workflow.png with all required branches.")


if __name__ == "__main__":
    draw_flowchart()
