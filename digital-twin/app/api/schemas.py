"""
Pydantic response schemas for the Learner Details API.
These models drive the Swagger/OpenAPI documentation with
rich descriptions, examples, and typed sub-objects.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime


# ─── Raw Data Schemas ───────────────────────────────────────────────

class TopicProgressItem(BaseModel):
    topic_id: str = Field(..., description="Unique identifier of the topic")
    completed: bool = Field(..., description="Whether the learner completed this topic")
    score: Optional[float] = Field(None, description="Score achieved on this topic (0-100)")

    model_config = {"json_schema_extra": {"examples": [{"topic_id": "topic_101", "completed": True, "score": 85.5}]}}


class ModuleProgressItem(BaseModel):
    module_id: str = Field(..., description="Unique identifier of the module")
    completed_percentage: float = Field(..., description="Completion percentage (0-100)")
    status: Optional[str] = Field(None, description="Current status: in_progress, completed, not_started")

    model_config = {"json_schema_extra": {"examples": [{"module_id": "mod_01", "completed_percentage": 72.5, "status": "in_progress"}]}}


class QuizAttemptItem(BaseModel):
    quiz_id: str = Field(..., description="Unique identifier of the quiz")
    score: float = Field(..., description="Score achieved on this quiz attempt")
    passed: bool = Field(..., description="Whether the learner passed this quiz")

    model_config = {"json_schema_extra": {"examples": [{"quiz_id": "quiz_42", "score": 78.0, "passed": True}]}}


class ChatMessageItem(BaseModel):
    session_id: str = Field(..., description="Chat session identifier")
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Full message content")

    model_config = {"json_schema_extra": {"examples": [{"session_id": "sess_abc", "role": "user", "content": "Explain prosthetic alignment"}]}}


class PersonaProfileItem(BaseModel):
    persona_type: Optional[str] = Field(None, description="Learner persona category")
    profile_data: Optional[Any] = Field(None, description="Detailed persona profile payload")


class LatestActivityEvent(BaseModel):
    event_type: str = Field(..., description="Type of the latest telemetry event")
    derived_status: Optional[str] = Field(None, description="Derived activity status")
    created_at: datetime = Field(..., description="Timestamp of the event")


class LearnerRawDataResponse(BaseModel):
    """All raw database records retrieved for the learner."""
    topic_progress: List[TopicProgressItem] = Field(default_factory=list, description="Topic-level progress records")
    module_progress: List[ModuleProgressItem] = Field(default_factory=list, description="Module-level progress records")
    quiz_attempts: List[QuizAttemptItem] = Field(default_factory=list, description="Quiz attempt records")
    cp_rag_chat_messages: List[ChatMessageItem] = Field(default_factory=list, description="Recent CP RAG chat messages")
    learner_persona_profiles: List[PersonaProfileItem] = Field(default_factory=list, description="Learner persona profiles")
    latest_activity_event: Optional[LatestActivityEvent] = Field(None, description="Most recent telemetry event")


# ─── Aggregated Context Schemas ─────────────────────────────────────

class CourseProgressSummary(BaseModel):
    average_completed_percentage: float = Field(..., description="Average module completion percentage")
    modules_tracked: int = Field(..., description="Number of modules being tracked")
    statuses: List[Optional[str]] = Field(default_factory=list, description="List of module statuses")


class QuizPerformanceSummary(BaseModel):
    total_attempts: int = Field(..., description="Total quiz attempts")
    pass_rate: float = Field(..., description="Ratio of passed quizzes (0.0 to 1.0)")
    average_score: float = Field(..., description="Average quiz score")


class LearnerPersona(BaseModel):
    type: str = Field(..., description="Persona type classification")
    profile_details: Optional[Any] = Field(None, description="Detailed persona profile data")


class ChatSummaryItem(BaseModel):
    session_id: Optional[str] = Field(None, description="Chat session identifier")
    role: Optional[str] = Field(None, description="Message role")
    message_snippet: str = Field(..., description="Truncated message preview (max 60 chars)")


class AggregatedContextResponse(BaseModel):
    """Processed and aggregated learner context derived from raw telemetry."""
    current_course_progress: CourseProgressSummary
    active_topic: Optional[str] = Field(None, description="Currently active/in-progress topic ID")
    quiz_performance_summary: QuizPerformanceSummary
    learner_persona: LearnerPersona
    recent_ai_chat_summaries: List[ChatSummaryItem] = Field(default_factory=list, description="Recent AI chat message previews")


# ─── Inactivity State Schema ───────────────────────────────────────

class InactivityStateResponse(BaseModel):
    """Inactivity tracking state for the learner."""
    learner_id: str
    last_activity_at: Optional[datetime] = None
    inactivity_stage: int = 0
    first_message_sent_at: Optional[datetime] = None
    second_message_sent_at: Optional[datetime] = None
    third_message_sent_at: Optional[datetime] = None
    email_sent_at: Optional[datetime] = None
    is_active: bool = True
    updated_at: Optional[datetime] = None


# ─── Top-Level Response ────────────────────────────────────────────

class CourseSpecificDetails(BaseModel):
    """Segmented raw data and aggregated context for a specific course."""
    course_id: str = Field(..., description="Unique course identifier")
    course_name: str = Field(..., description="The name of the course")
    raw_data: LearnerRawDataResponse = Field(..., description="Raw database records for this course")
    aggregated_context: AggregatedContextResponse = Field(..., description="Processed analytics and context for this course")


class LearnerDetailsResponse(BaseModel):
    """
    Complete learner profile combining raw data, aggregated analytics per course,
    and inactivity tracking state. Returned by GET /learner/{learner_id}/details.
    """
    learner_id: str = Field(..., description="The queried learner identifier")
    courses: List[CourseSpecificDetails] = Field(default_factory=list, description="Individually segmented details for all enrolled courses")
    inactivity_state: Optional[InactivityStateResponse] = Field(None, description="Inactivity tracking state (null if not tracked)")
