from typing import Dict, Any
from app.graphs.state import TwinState
from app.services.tutor_context import aggregate_tutor_context

def retrieve_tutor_context(state: TwinState) -> Dict[str, Any]:
    """
    RetrieveTutorContext node: Reads the tutor_id from state, queries and 
    aggregates telemetry data into the tutor_context dictionary, and updates 
    the state.
    """
    tutor_id = state.get("tutor_id")
    course_id = state.get("course_id")
    
    if not tutor_id:
        default_context = {
            "tutor_display_name": "AI Assistant",
            "tutor_bio": "Default tutoring assistant profile.",
            "courses_taught": [],
            "tutor_prompt_guidance": [],
            "relevant_course_knowledge": {
                "topics": [],
                "recent_submissions_summary": {
                    "total_reviewed": 0,
                    "pending_reviews": 0
                }
            }
        }
        return {"tutor_context": default_context}

    context = aggregate_tutor_context(tutor_id, course_id=course_id)
    return {"tutor_context": context}
