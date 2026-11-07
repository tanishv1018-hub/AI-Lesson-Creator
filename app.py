import os
import json
import streamlit as st
from dotenv import load_dotenv

from core.research import ResearchEngine
from core.generator import LessonGenerator
from core.qc_engine import QualityControlEngine
from utils.storage import (
    save_workspace,
    list_saved_workspaces,
    load_workspace,
    build_complete_markdown_package,
    slugify,
)

load_dotenv()

st.set_page_config(
    page_title="AI Lesson Creation & Dual-QC Studio",
    page_icon="🎓",
    layout="wide",
)

# ---------------- SESSION STATE INITIALIZATION ----------------
defaults = {
    "title": "HTTP Requests and Responses",
    "objective": "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories.",
    "research_data": None,
    "lesson_content": "",
    "qc1_report": None,
    "qc2_report": None,
    "last_saved_path": None,
    "failed_step": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def auto_persist():
    """Automatically save current progress locally so work is never lost."""
    if st.session_state.title.strip() and (
        st.session_state.research_data or st.session_state.lesson_content
    ):
        path = save_workspace(
            st.session_state.title,
            st.session_state.objective,
            st.session_state.research_data,
            st.session_state.lesson_content,
            st.session_state.qc1_report,
            st.session_state.qc2_report,
        )
        st.session_state.last_saved_path = path


# ---------------- SIDEBAR: CONFIG, PRESETS & SAVED WORKSPACES ----------------
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=os.getenv("GEMINI_API_KEY", ""),
        help="Get a free API key from aistudio.google.com",
    )
    model_name = st.selectbox(
        "AI Model",
        [
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
            "gemini-flash-latest",
        ],
        index=0,
    )

    st.divider()
    st.subheader("🧪 Test Case Presets")
    preset_choice = st.radio(
        "Select Input Preset:",
        [
            "Sample 1: HTTP Requests & Responses (Required)",
            "Sample 2: Binary Search & Time Complexity (Custom)",
            "Custom Topic",
        ],
    )

    if st.button("Load Selected Preset", use_container_width=True):
        if "Sample 1" in preset_choice:
            st.session_state.title = "HTTP Requests and Responses"
            st.session_state.objective = (
                "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
            )
        elif "Sample 2" in preset_choice:
            st.session_state.title = "Binary Search Algorithm and Complexity Analysis"
            st.session_state.objective = (
                "Explain O(log n) logarithmic time complexity, implement iterative binary search on sorted arrays, and handle off-by-one boundary conditions."
            )
        else:
            st.session_state.title = ""
            st.session_state.objective = ""
        st.rerun()

    st.divider()
    st.subheader("💾 Saved Workspaces")
    saved_files = list_saved_workspaces()
    if saved_files:
        selected_file = st.selectbox("Restore Previous Session:", saved_files)
        if st.button("📂 Load Workspace", use_container_width=True):
            data = load_workspace(selected_file)
            st.session_state.title = data.get("title", "")
            st.session_state.objective = data.get("objective", "")
            st.session_state.research_data = data.get("research_data")
            st.session_state.lesson_content = data.get("lesson_content", "")
            st.session_state.qc1_report = data.get("qc1_report")
            st.session_state.qc2_report = data.get("qc2_report")
            st.success(f"Restored {selected_file} (Saved {data.get('updated_at')})")
            st.rerun()
    else:
        st.caption("No saved workspaces yet. Work is auto-saved as you generate and edit.")


# ---------------- MAIN HEADER & INPUT FORM ----------------
st.title("🎓 AI-Powered 45-Minute Lesson Creation & Dual-QC Tool")
st.markdown(
    "Research books, documentation, and YouTube videos; synthesize a **45-minute lesson**; and validate through **two independent Quality Control (QC) layers**."
)

col_in1, col_in2 = st.columns([1, 2])
with col_in1:
    title_input = st.text_input(
        "Lesson Title *",
        value=st.session_state.title,
        placeholder="e.g., HTTP Requests and Responses",
    )
    st.session_state.title = title_input

with col_in2:
    obj_input = st.text_area(
        "Learning Objective *",
        value=st.session_state.objective,
        height=68,
        placeholder="e.g., Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories.",
    )
    st.session_state.objective = obj_input


# ---------------- PIPELINE EXECUTION & GRANULAR RETRY CONTROLS ----------------
def validate_inputs() -> bool:
    if not api_key.strip():
        st.error("⚠️ Missing Gemini API Key. Please enter your API key in the left sidebar.")
        return False
    if not st.session_state.title.strip() or len(st.session_state.title.strip()) < 3:
        st.error("⚠️ Invalid Input: Please enter a meaningful Lesson Title (at least 3 characters).")
        return False
    if not st.session_state.objective.strip() or len(st.session_state.objective.strip()) < 10:
        st.error("⚠️ Invalid Input: Please provide a clear Learning Objective (at least 10 characters).")
        return False
    return True


btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([2, 1, 1, 1])

with btn_col1:
    run_full = st.button("🚀 Run Full Pipeline (Research → Generate → Dual QC)", type="primary", use_container_width=True)
with btn_col2:
    retry_research = st.button("🔄 1. Retry Research Only", use_container_width=True)
with btn_col3:
    retry_gen = st.button(
        "🔄 2. Retry Lesson Gen",
        disabled=st.session_state.research_data is None,
        use_container_width=True,
    )
with btn_col4:
    retry_qc = st.button(
        "🔄 3. Re-Run QC Audits",
        disabled=not bool(st.session_state.lesson_content),
        use_container_width=True,
    )

# Step-by-step execution with fault isolation
if run_full and validate_inputs():
    with st.status("Executing End-to-End Lesson Pipeline...", expanded=True) as status:
        try:
            st.write("🔍 **Stage 1/3:** Decomposing queries & researching Books, Web Docs, and YouTube...")
            res_engine = ResearchEngine(api_key, model_name)
            st.session_state.research_data = res_engine.run_research_pipeline(
                st.session_state.title, st.session_state.objective
            )
            auto_persist()

            st.write("✍️ **Stage 2/3:** Synthesizing structured 45-minute lesson content...")
            gen_engine = LessonGenerator(api_key, model_name)
            st.session_state.lesson_content = gen_engine.generate_lesson(
                st.session_state.title, st.session_state.objective, st.session_state.research_data
            )
            auto_persist()

            st.write("🛡️ **Stage 3/3:** Running Independent QC Layer 1 (Factuality) & QC Layer 2 (Pedagogy) in parallel...")
            qc_engine = QualityControlEngine(api_key, model_name)
            qc1, qc2 = qc_engine.run_both_qc_layers_parallel(
                st.session_state.title,
                st.session_state.objective,
                st.session_state.lesson_content,
                st.session_state.research_data,
            )
            st.session_state.qc1_report = qc1
            st.session_state.qc2_report = qc2
            st.session_state.failed_step = None
            auto_persist()

            status.update(label="✅ Pipeline Complete! All stages saved locally.", state="complete", expanded=False)
        except Exception as e:
            st.session_state.failed_step = str(e)
            status.update(label="❌ Pipeline Interrupted — Previous stages preserved!", state="error", expanded=True)
            st.error(f"Error encountered: {e}. Use the granular retry buttons above to resume without losing prior steps.")

elif retry_research and validate_inputs():
    with st.spinner("Re-running Multi-Source Research..."):
        try:
            res_engine = ResearchEngine(api_key, model_name)
            st.session_state.research_data = res_engine.run_research_pipeline(
                st.session_state.title, st.session_state.objective
            )
            auto_persist()
            st.success("Research updated and saved!")
        except Exception as e:
            st.error(f"Research step failed: {e}")

elif retry_gen and validate_inputs():
    with st.spinner("Regenerating 45-minute lesson from saved research..."):
        try:
            gen_engine = LessonGenerator(api_key, model_name)
            st.session_state.lesson_content = gen_engine.generate_lesson(
                st.session_state.title, st.session_state.objective, st.session_state.research_data
            )
            auto_persist()
            st.success("Lesson regenerated and saved!")
        except Exception as e:
            st.error(f"Generation failed: {e}")

elif retry_qc and validate_inputs():
    with st.spinner("Running Independent QC Layer 1 & Layer 2 Audits on current lesson..."):
        try:
            qc_engine = QualityControlEngine(api_key, model_name)
            qc1, qc2 = qc_engine.run_both_qc_layers_parallel(
                st.session_state.title,
                st.session_state.objective,
                st.session_state.lesson_content,
                st.session_state.research_data or {},
            )
            st.session_state.qc1_report = qc1
            st.session_state.qc2_report = qc2
            auto_persist()
            st.success("Both QC Audit Reports updated!")
        except Exception as e:
            st.error(f"QC Audit failed: {e}")


# ---------------- DISPLAY SECTION 1: RESEARCH SOURCES ----------------
if st.session_state.research_data:
    st.divider()
    with st.expander("📚 Stage 1 Output: Multi-Source Research & YouTube References", expanded=False):
        queries = st.session_state.research_data.get("generated_queries", {})
        if queries:
            st.caption(
                f"**Decomposed Queries** → Books: `{queries.get('book_query')}` | Web: `{queries.get('web_query')}` | YouTube: `{queries.get('youtube_query')}`"
            )
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown("#### 📖 Books (Google Books)")
            for b in st.session_state.research_data.get("books", []):
                st.markdown(f"**[{b['title']}]({b['link']})**  \n*{b['authors']}* ({b.get('publishedDate', 'N/A')})  \n{b['snippet']}")
        with r2:
            st.markdown("#### 🌐 Web Documentation")
            for w in st.session_state.research_data.get("web_articles", []):
                st.markdown(f"**[{w['title']}]({w['link']})**  \n{w['snippet']}")
        with r3:
            st.markdown("#### 🎥 YouTube Videos")
            for y in st.session_state.research_data.get("youtube_videos", []):
                st.markdown(f"**[{y['title']}]({y['link']})**  \nChannel: *{y['channel']}*")
                if "watch?v=" in y["link"] or "youtu.be/" in y["link"]:
                    st.video(y["link"])


# ---------------- DISPLAY SECTION 2: DUAL QC AUDIT REPORTS & REMEDIATION ----------------
if st.session_state.qc1_report or st.session_state.qc2_report:
    st.divider()
    st.subheader("🛡️ Independent Quality Control (QC) Audit Layers")

    selected_recommendations = []
    qc_col1, qc_col2 = st.columns(2)

    with qc_col1:
        st.markdown("### 🔬 QC Layer 1: Research & Factual Accuracy")
        q1 = st.session_state.qc1_report
        if q1:
            m1, m2 = st.columns(2)
            m1.metric("Factual Accuracy Score", f"{q1.get('accuracy_score', 0)}/100")
            m2.metric("Layer 1 Verdict", q1.get("overall_verdict", "N/A"))
            st.info(f"**Source Reliability:** {q1.get('source_reliability_summary', '')}")

            st.markdown("**Identified Factual / Source Findings (Select to Auto-Apply):**")
            for idx, f in enumerate(q1.get("findings", [])):
                label = f"[{f['id']} - {f['severity']}] {f['issue']}"
                checked = st.checkbox(label, value=True, key=f"qc1_chk_{idx}")
                st.caption(f"📍 *Location:* {f['location']}  \n💡 *Suggested Fix:* {f['suggested_fix']}")
                if checked:
                    selected_recommendations.append(
                        f"[QC1 Factual Fix - {f['location']}]: {f['issue']} -> {f['suggested_fix']}"
                    )

    with qc_col2:
        st.markdown("### 📐 QC Layer 2: Instructional Quality & 45-Min Pacing")
        q2 = st.session_state.qc2_report
        if q2:
            m3, m4 = st.columns(2)
            m3.metric("Pedagogical Score", f"{q2.get('pedagogy_score', 0)}/100")
            m4.metric("Layer 2 Verdict", q2.get("overall_verdict", "N/A"))
            st.info(
                f"**Objective Alignment:** {q2.get('alignment_check', '')}\n\n**45-Min Pacing Check:** {q2.get('pacing_evaluation', '')}"
            )

            st.markdown("**Identified Pedagogical Improvements (Select to Auto-Apply):**")
            for idx, g in enumerate(q2.get("instructional_gaps", [])):
                label = f"[{g['id']} - {g['category']}] {g['issue']}"
                checked = st.checkbox(label, value=True, key=f"qc2_chk_{idx}")
                st.caption(f"💡 *Suggested Improvement:* {g['suggested_improvement']}")
                if checked:
                    selected_recommendations.append(
                        f"[QC2 Pedagogical Fix - {g['category']}]: {g['issue']} -> {g['suggested_improvement']}"
                    )

    if selected_recommendations:
        if st.button(
            f"✨ Apply {len(selected_recommendations)} Selected QC Recommendations to Lesson",
            type="primary",
            use_container_width=True,
        ):
            if validate_inputs():
                with st.spinner("Applying selected QC fixes and re-validating lesson..."):
                    try:
                        gen_engine = LessonGenerator(api_key, model_name)
                        updated_lesson = gen_engine.apply_qc_recommendations(
                            st.session_state.title,
                            st.session_state.objective,
                            st.session_state.lesson_content,
                            selected_recommendations,
                        )
                        st.session_state.lesson_content = updated_lesson
                        auto_persist()
                        st.success(
                            "✅ Lesson updated with QC recommendations! Click 'Re-Run QC Audits' above if you want to verify the new score."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to apply QC fixes: {e}")


# ---------------- DISPLAY SECTION 3: INSTRUCTOR REVIEW, EDIT & PREVIEW ----------------
if st.session_state.lesson_content:
    st.divider()
    st.subheader("📝 Instructor Review, Edit & Preview Studio")

    word_count = len(st.session_state.lesson_content.split())
    st.caption(
        f"📊 **Lesson Metrics:** ~{word_count} words | Designed for **45-Minute Completion** (25m Theory/Examples + 10m Hands-on Activity + 5m Assessment + 5m Hook) | Auto-saved to `{st.session_state.last_saved_path or 'local storage'}`"
    )

    tab_preview, tab_edit = st.tabs(["👁️ Final Lesson Preview (Student View)", "✏️ Manual Markdown Editor"])

    with tab_preview:
        st.markdown(st.session_state.lesson_content)

    with tab_edit:
        edited_content = st.text_area(
            "Edit Lesson Markdown Directly:",
            value=st.session_state.lesson_content,
            height=550,
        )
        if st.button("💾 Save Manual Edits", type="primary"):
            st.session_state.lesson_content = edited_content
            auto_persist()
            st.success("Manual edits saved to local workspace!")
            st.rerun()


    # ---------------- DISPLAY SECTION 4: EXPORT DELIVERABLES ----------------
    st.divider()
    st.subheader("📦 Export Finalized Lesson, References & QC Reports")

    file_slug = slugify(st.session_state.title)
    ex1, ex2, ex3, ex4 = st.columns(4)

    with ex1:
        st.download_button(
            label="📥 1. Final Lesson (.md)",
            data=st.session_state.lesson_content,
            file_name=f"{file_slug}_lesson.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with ex2:
        qc_export = {
            "lesson_title": st.session_state.title,
            "learning_objective": st.session_state.objective,
            "qc_layer_1_factual_accuracy": st.session_state.qc1_report,
            "qc_layer_2_instructional_quality": st.session_state.qc2_report,
        }
        st.download_button(
            label="📥 2. Dual QC Reports (.json)",
            data=json.dumps(qc_export, indent=2),
            file_name=f"{file_slug}_qc_reports.json",
            mime="application/json",
            use_container_width=True,
        )
    with ex3:
        st.download_button(
            label="📥 3. Research & Links (.json)",
            data=json.dumps(st.session_state.research_data, indent=2),
            file_name=f"{file_slug}_references.json",
            mime="application/json",
            use_container_width=True,
        )
    with ex4:
        full_package_md = build_complete_markdown_package(
            st.session_state.title,
            st.session_state.objective,
            st.session_state.lesson_content,
            st.session_state.research_data or {},
            st.session_state.qc1_report or {},
            st.session_state.qc2_report or {},
        )
        st.download_button(
            label="📥 4. Complete Bundle (.md)",
            data=full_package_md,
            file_name=f"{file_slug}_complete_package.md",
            mime="text/markdown",
            use_container_width=True,
        )