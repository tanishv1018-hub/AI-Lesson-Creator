import json
from typing import Dict, Any, List
from google.genai import types
from utils.llm_client import generate_with_retry


class LessonGenerator:
    def __init__(self, api_key: str, model_name: str = "gemini-3.8-flash"):
        self.api_key = api_key
        self.model_name = model_name

    def generate_lesson(self, title: str, objective: str, research: Dict[str, Any]) -> str:
        prompt = f"""
You are a Senior Instructional Designer and Technical Subject Matter Expert.
Create a comprehensive, engaging, and factually rigorous lesson strictly designed to be completed in **45 MINUTES** (suitable for self-paced learning or instructor-led delivery).

LESSON TITLE: {title}
LEARNING OBJECTIVE: {objective}

RETRIEVED RESEARCH CORPUS (Ground all facts and citations in these sources):
- Books: {json.dumps(research.get("books", []), indent=2)}
- Web Articles: {json.dumps(research.get("web_articles", []), indent=2)}
- YouTube Videos: {json.dumps(research.get("youtube_videos", []), indent=2)}

MANDATORY 45-MINUTE LESSON STRUCTURE & TIME ALLOCATION:

# {title}
**Estimated Time:** 45 Minutes | **Learning Objective:** {objective}

## 1. Hook & Lesson Overview (5 Minutes)
- Engaging real-world scenario explaining *why* this topic matters.
- Bullet-point breakdown of what learners will achieve.

## 2. Core Concepts & Technical Explanations (15 Minutes)
- Clear, structured explanation of every concept mentioned in the learning objective.
- Include comparison tables, architectural diagrams (using clean ASCII/Markdown blocks), and concrete syntax/mechanics.
- Cite the retrieved sources inline (e.g., [Source 1]) where relevant.

## 3. Real-World Examples & Common Pitfalls (10 Minutes)
- At least 2 concrete industry use cases showing the concepts in action.
- "Watch Out!" section addressing common misconceptions or edge cases.

## 4. Guided Practical Activity (10 Minutes)
- A hands-on, step-by-step exercise that takes ~10 minutes to complete.
- Provide the problem setup, exact steps to perform, and the expected output/solution.

## 5. Knowledge Check & Assessment (5 Minutes)
- 4 diagnostic questions (mix of scenario-based multiple choice and short conceptual questions) directly testing the Learning Objective.
- Include a clearly marked **Answer Key with Explanations** at the end of the section.

## 6. Supplementary YouTube Learning Resources
- List the retrieved YouTube videos with clickable Markdown links, channel names, and a 1-sentence guide on what to watch for in each video.

## 7. References & Further Reading
- Properly formatted reference list grouping all Books and Web Articles with clickable links.
"""
        response = generate_with_retry(
            api_key=self.api_key,
            model_name=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3),
        )
        return response.text

    def apply_qc_recommendations(
        self, title: str, objective: str, current_content: str, selected_fixes: List[str]
    ) -> str:
        """Applies selected QC Layer 1 and QC Layer 2 recommendations to the lesson."""
        fixes_formatted = "\n".join([f"- {fix}" for fix in selected_fixes])
        prompt = f"""
You are a Senior Curriculum Editor. Revise the lesson below to resolve the specific Quality Control (QC) audit findings selected by the instructor.

LESSON TITLE: {title}
LEARNING OBJECTIVE: {objective}

SELECTED QC RECOMMENDATIONS TO APPLY:
{fixes_formatted}

CURRENT LESSON CONTENT:
{current_content}

INSTRUCTIONS:
1. Directly fix every issue listed in the Selected QC Recommendations.
2. Maintain the 45-minute time budget (5m Hook, 15m Core Concepts, 10m Examples, 10m Activity, 5m Assessment).
3. Keep all existing valid references and YouTube links intact.
4. Return ONLY the complete, updated Markdown lesson.
"""
        response = generate_with_retry(
            api_key=self.api_key,
            model_name=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return response.text