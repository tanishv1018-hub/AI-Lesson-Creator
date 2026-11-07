# AI-Powered Lesson Creation & Dual-QC Studio

An automated educational workflow that researches authoritative books, technical web documentation, and YouTube tutorials to synthesize structured **45-minute lessons**, validated by two independent Quality Control (QC) layers.

## Key Architectural Decisions
1. **Dynamic Multi-Source Search RAG:** Instead of a static vector database limited to pre-indexed files, the `ResearchEngine` performs LLM-driven query decomposition followed by real-time retrieval across the **Google Books API**, **DuckDuckGo Web Search**, and **YouTube Video Search**.
2. **Explicit 45-Minute Pedagogical Pacing:** Prompts enforce a deterministic 45-minute instructional structure (5m Hook, 15m Core Concepts, 10m Real-World Examples, 10m Hands-On Activity, 5m Assessment).
3. **Concurrent, Independent Dual QC Layers:** `QC Layer 1` (Factual & Source Accuracy) and `QC Layer 2` (Instructional Quality & Pacing) execute in parallel threads (`ThreadPoolExecutor`) with strict Pydantic JSON schemas (`google-genai` structured outputs).
4. **Fault Isolation & Local State Persistence:** Every stage automatically snapshots state to `saved_workspaces/*.json`. If any API step fails, previously saved research or instructor edits are preserved, and individual stages can be retried independently.

## Quick Setup Instructions

1. **Clone the repository and create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt