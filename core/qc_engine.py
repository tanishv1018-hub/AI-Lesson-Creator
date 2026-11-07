import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Tuple
from google.genai import types
from core.schemas import QC1Report, QC2Report
from utils.llm_client import generate_with_retry


class QualityControlEngine:
    def __init__(self, api_key: str, model_name: str = "gemini-3.8-flash"):
        self.api_key = api_key
        self.model_name = model_name

    def run_qc_layer_1_factual(
        self, title: str, objective: str, lesson_content: str, research: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Independent QC Layer 1: Factual Accuracy, Source Reliability, and Gap Analysis."""
        prompt = f"""
You are an independent Technical Fact-Checker and Research Auditor (QC Layer 1).
Critically audit the following generated lesson against authoritative technical standards and the retrieved research sources.

LESSON TITLE: {title}
LEARNING OBJECTIVE: {objective}

RETRIEVED RESEARCH SOURCES:
{json.dumps(research, indent=2)}

GENERATED LESSON CONTENT:
{lesson_content}

AUDIT CRITERIA:
1. Factual Correctness: Verify all technical definitions, protocols, formulas, or code examples. Flag any unsupported, oversimplified, or misleading claims.
2. Source Reliability & Usage: Check if retrieved books, web articles, and YouTube links are reliable, relevant, and properly cited.
3. Content Gaps & Inconsistencies: Identify any missing technical nuances required to accurately represent the topic.
Be rigorous: even if the lesson is good, identify at least 1-2 constructive factual or citation refinements.
"""
        response = generate_with_retry(
            api_key=self.api_key,
            model_name=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QC1Report,
                temperature=0.1,
            ),
        )
        return QC1Report.model_validate_json(response.text).model_dump()

    def run_qc_layer_2_instructional(
        self, title: str, objective: str, lesson_content: str
    ) -> Dict[str, Any]:
        """Independent QC Layer 2: Instructional Quality, Objective Alignment, and 45-Min Pacing."""
        # Slight 1s stagger so parallel threads don't hit free-tier burst limit simultaneously
        time.sleep(1.0)
        prompt = f"""
You are an independent Principal Instructional Designer and Pedagogical Auditor (QC Layer 2).
Critically evaluate the instructional effectiveness of the generated lesson. Do NOT evaluate raw factual trivia—focus strictly on learning design.

LESSON TITLE: {title}
TARGET LEARNING OBJECTIVE: {objective}

GENERATED LESSON CONTENT:
{lesson_content}

AUDIT CRITERIA:
1. Learning Objective Alignment: Does every section, example, and assessment question directly build toward the stated Learning Objective?
2. 45-Minute Pacing Feasibility: Can a learner or instructor realistically cover the explanations, 10-minute activity, and 5-minute knowledge check within 45 minutes without cognitive overload?
3. Clarity, Scaffolding & Practical Application: Are explanations clear for the target level? Are examples concrete? Does the hands-on activity actively test the skill?
Be rigorous: identify at least 1-2 actionable pedagogical improvements.
"""
        response = generate_with_retry(
            api_key=self.api_key,
            model_name=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QC2Report,
                temperature=0.1,
            ),
        )
        return QC2Report.model_validate_json(response.text).model_dump()

    def run_both_qc_layers_parallel(
        self, title: str, objective: str, lesson_content: str, research: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Executes QC Layer 1 and QC Layer 2 concurrently and independently."""
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_qc1 = executor.submit(
                self.run_qc_layer_1_factual, title, objective, lesson_content, research
            )
            future_qc2 = executor.submit(
                self.run_qc_layer_2_instructional, title, objective, lesson_content
            )
            qc1_result = future_qc1.result()
            qc2_result = future_qc2.result()

        return qc1_result, qc2_result