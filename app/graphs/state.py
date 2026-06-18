from typing import TypedDict, Optional, Dict, Any

class TwinState(TypedDict):
    """
    TwinState defines the shared state schema passed across LangGraph nodes
    within the Digital Twin orchestration graph.
    """
    learner_id: Optional[str]
    course_id: Optional[str]
    tutor_id: Optional[str]
    conversation_id: Optional[str]
    learner_context: Optional[Dict[str, Any]]
    tutor_context: Optional[Dict[str, Any]]
    latest_event: Optional[Dict[str, Any]]
    latest_message: Optional[str]
    inactivity_level: Optional[int]
    response_mode: Optional[str]
    generated_response: Optional[str]
    should_email: Optional[bool]
