from pydantic import BaseModel, Field
from typing import List, Literal

class SearchQueries(BaseModel):
    book_query: str = Field(description="Concise 3-5 word technical keyword query for Google Books API")
    web_query: str = Field(description="Targeted search query for official documentation and technical articles")
    youtube_query: str = Field(description="Search query for educational YouTube video tutorials")

class QCFinding(BaseModel):
    id: str = Field(description="Unique identifier like ACC-1, ACC-2")
    severity: Literal["High", "Medium", "Low"] = Field(description="Severity of the factual or source issue")
    issue: str = Field(description="Clear description of the unsupported claim, inaccuracy, or source gap")
    location: str = Field(description="The specific section heading or quote where the issue appears")
    suggested_fix: str = Field(description="Concrete rewrite or addition to fix the issue")

class QC1Report(BaseModel):
    overall_verdict: Literal["Pass", "Needs Revision", "Fail"]
    accuracy_score: int = Field(description="Score from 0 to 100 based on factual correctness and source backing")
    source_reliability_summary: str = Field(description="Evaluation of the credibility and usage of retrieved sources")
    findings: List[QCFinding] = Field(description="List of specific factual issues, inconsistencies, or missing citations")

class PedagogicalGap(BaseModel):
    id: str = Field(description="Unique identifier like PED-1, PED-2")
    category: Literal["Objective Alignment", "45-Min Pacing", "Clarity & Examples", "Assessment"]
    issue: str = Field(description="Description of the instructional or timing weakness")
    suggested_improvement: str = Field(description="Actionable adjustment to improve learning effectiveness")

class QC2Report(BaseModel):
    overall_verdict: Literal["Pass", "Needs Revision", "Fail"]
    pedagogy_score: int = Field(description="Score from 0 to 100 for instructional quality")
    alignment_check: str = Field(description="Assessment of how thoroughly the lesson meets the Learning Objective")
    pacing_evaluation: str = Field(description="Verification of whether the lesson fits realistically into 45 minutes")
    instructional_gaps: List[PedagogicalGap] = Field(description="List of pedagogical improvements needed")