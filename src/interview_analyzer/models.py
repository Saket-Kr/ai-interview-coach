from enum import Enum

from pydantic import BaseModel, Field


# --- Transcript models ---


class Segment(BaseModel):
    speaker: str
    text: str
    start: float
    end: float


class Transcript(BaseModel):
    segments: list[Segment]
    speakers: list[str]


# --- Q&A extraction ---


class QAPair(BaseModel):
    question_number: int
    question: str
    answer: str
    topic: str = Field(default="General")


# --- Per-question analysis ---


class ContentScore(BaseModel):
    technical_accuracy: int  # 1-10
    depth: int
    specificity: int
    completeness: int
    tradeoff_awareness: int
    commentary: str
    strengths: list[str]
    gaps: list[str]


class CommunicationScore(BaseModel):
    structure: int  # 1-10
    conciseness: int
    clarity: int
    filler_word_count: int
    filler_words: list[str]
    recovery: int
    commentary: str


class InteractionScore(BaseModel):
    clarifying_questions: int  # 1-10
    listening: int
    adaptability: int
    commentary: str


class QuestionAnalysis(BaseModel):
    qa: QAPair
    content: ContentScore
    communication: CommunicationScore
    interaction: InteractionScore
    overall_score: float
    summary: str


# --- Overall assessment ---


class Severity(str, Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    POLISH = "polish"


class Improvement(BaseModel):
    severity: Severity
    area: str
    gap: str
    what_to_study: str
    how_to_practice: str
    reference_moment: str = Field(default="")


class TopicDepth(str, Enum):
    SURFACE = "surface"
    WORKING = "working"
    DEEP = "deep"


class TechnicalDepthEntry(BaseModel):
    topic: str
    depth: TopicDepth
    evidence: str


class OverallAssessment(BaseModel):
    executive_summary: str
    overall_score: float
    role_fit: str
    strengths: list[str]
    weaknesses: list[str]
    technical_depth_map: list[TechnicalDepthEntry]
    communication_profile: str
    improvements: list[Improvement]
    practice_prompts: list[str]


class AnalysisResult(BaseModel):
    transcript: Transcript
    qa_pairs: list[QAPair]
    question_analyses: list[QuestionAnalysis]
    overall: OverallAssessment
