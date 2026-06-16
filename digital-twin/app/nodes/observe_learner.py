from typing import Dict, Any
from app.graphs.state import TwinState
from app.services.telemetry import get_latest_learner_event

def observe_learner(state: TwinState) -> Dict[str, Any]:
    """
    ObserveLearner node: Reads the learner_id from the state, retrieves the 
    latest event from the database telemetry system, and updates the state's 
    latest_event field.
    
    Returns a dictionary of state updates.
    """
    learner_id = state.get("learner_id")
    course_id = state.get("course_id")
    
    if not learner_id:
        # Default fallback event when learner_id is missing
        default_event = {
            "event_type": "unknown",
            "derived_status": "engaged",
            "created_at": None,
            "status": "engaged"
        }
        return {"latest_event": default_event}

    event = get_latest_learner_event(learner_id, course_id=course_id)
    
    if event:
        derived_status = event.get("derived_status")
        # Ensure it maps to one of: engaged, attention_drift, content_friction
        if derived_status not in ["engaged", "attention_drift", "content_friction"]:
            status = "engaged"
        else:
            status = derived_status
            
        latest_event = {
            "event_type": event.get("event_type"),
            "derived_status": derived_status,
            "created_at": event.get("created_at"),
            "status": status
        }
    else:
        # Default fallback event when no telemetry events exist
        latest_event = {
            "event_type": "none",
            "derived_status": "engaged",
            "created_at": None,
            "status": "engaged"
        }

    return {"latest_event": latest_event}
