from typing import Dict, Any
from app.graphs.state import TwinState
from app.services.learner_context import aggregate_learner_context

def retrieve_learner_context(state: TwinState) -> Dict[str, Any]:
    """
    RetrieveLearnerContext node: Reads the learner_id from state, queries and 
    aggregates telemetry data into the learner_context dictionary, and updates 
    the state.
    """
    learner_id = state.get("learner_id")
    course_id = state.get("course_id")
    
    if not learner_id:
        default_context = {
            "current_course_progress": {
                "average_completed_percentage": 0.0,
                "modules_tracked": 0,
                "statuses": []
            },
            "active_topic": None,
            "quiz_performance_summary": {
                "total_attempts": 0,
                "pass_rate": 0.0,
                "average_score": 0.0
            },
            "learner_persona": {
                "type": "standard",
                "profile_details": {}
            },
            "recent_ai_chat_summaries": []
        }
        return {"learner_context": default_context}

    context = aggregate_learner_context(learner_id, course_id=course_id)
    return {"learner_context": context}
