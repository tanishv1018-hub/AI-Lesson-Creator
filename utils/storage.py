import os
import json
import re
from datetime import datetime
from typing import Dict, Any, List

WORKSPACE_DIR = "saved_workspaces"


def ensure_workspace_dir():
    os.makedirs(WORKSPACE_DIR, exist_ok=True)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return slug[:50] or "untitled_lesson"


def save_workspace(
    title: str,
    objective: str,
    research_data: Any,
    lesson_content: str,
    qc1_report: Any,
    qc2_report: Any,
) -> str:
    """Save the complete lesson state to disk so edits are never lost."""
    ensure_workspace_dir()
    filename = f"{slugify(title)}.json"
    filepath = os.path.join(WORKSPACE_DIR, filename)

    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": title,
        "objective": objective,
        "research_data": research_data,
        "lesson_content": lesson_content,
        "qc1_report": qc1_report,
        "qc2_report": qc2_report,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return filepath


def list_saved_workspaces() -> List[str]:
    ensure_workspace_dir()
    files = [f for f in os.listdir(WORKSPACE_DIR) if f.endswith(".json")]
    return sorted(files)


def load_workspace(filename: str) -> Dict[str, Any]:
    filepath = os.path.join(WORKSPACE_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def build_complete_markdown_package(
    title: str,
    objective: str,
    lesson_content: str,
    research_data: Dict[str, Any],
    qc1_report: Dict[str, Any],
    qc2_report: Dict[str, Any],
) -> str:
    """Builds a single comprehensive Markdown file containing the lesson, references, and both QC audit reports."""
    md = [
        lesson_content,
        "\n\n---\n",
        "# Appendix A: Quality Control (QC) Audit Reports\n",
    ]

    if qc1_report:
        md.append(f"## QC Layer 1: Research & Factual Accuracy")
        md.append(f"- **Verdict:** {qc1_report.get('overall_verdict')} ({qc1_report.get('accuracy_score')}/100)")
        md.append(f"- **Source Evaluation:** {qc1_report.get('source_reliability_summary')}\n")
        for f in qc1_report.get("findings", []):
            md.append(f"  - **[{f['id']} - {f['severity']}]** {f['issue']} *(Location: {f['location']})*")
            md.append(f"    - *Suggested Fix:* {f['suggested_fix']}")

    if qc2_report:
        md.append(f"\n## QC Layer 2: Instructional Quality & 45-Min Pacing")
        md.append(f"- **Verdict:** {qc2_report.get('overall_verdict')} ({qc2_report.get('pedagogy_score')}/100)")
        md.append(f"- **Objective Alignment:** {qc2_report.get('alignment_check')}")
        md.append(f"- **45-Min Pacing Check:** {qc2_report.get('pacing_evaluation')}\n")
        for g in qc2_report.get("instructional_gaps", []):
            md.append(f"  - **[{g['id']} - {g['category']}]** {g['issue']}")
            md.append(f"    - *Suggested Improvement:* {g['suggested_improvement']}")

    return "\n".join(md)