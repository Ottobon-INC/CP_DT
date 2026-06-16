from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.graphs.state import TwinState
from app.services.inactivity import track_learner_inactivity

def parse_datetime(dt_val) -> Optional[datetime]:
    """
    Safely parses various datetime representations (str, datetime, or None) into a tz-aware object.
    """
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val
    if isinstance(dt_val, str):
        try:
            iso_str = dt_val.replace("Z", "+00:00")
            return datetime.fromisoformat(iso_str)
        except Exception:
            return None
    return None

def determine_learner_state(state: TwinState) -> Dict[str, Any]:
    """
    DetermineLearnerState node: Loads/updates the persistent inactivity stage record
    for the learner, determines if any re-engagement transitions occur, and updates
    the TwinState fields accordingly.
    """
    learner_id = state.get("learner_id")
    latest_event = state.get("latest_event") or {}
    created_at_val = latest_event.get("created_at")
    derived_status = latest_event.get("derived_status", "engaged")
    
    if not learner_id:
        # Fallback if no learner_id is provided
        updated_event = dict(latest_event)
        updated_event["learner_state"] = "ACTIVE"
        return {
            "inactivity_level": 0,
            "should_email": False,
            "latest_event": updated_event
        }

    latest_activity_time = parse_datetime(created_at_val)

    # Track inactivity state using persistence layer
    outcome = track_learner_inactivity(
        learner_id=learner_id,
        latest_activity_time=latest_activity_time,
        derived_status=derived_status
    )

    inactivity_level = outcome["inactivity_level"]
    should_email = outcome["should_email"]
    determined_state = outcome["learner_state"]

    updated_event = dict(latest_event)
    updated_event["learner_state"] = determined_state

    return {
        "inactivity_level": inactivity_level,
        "should_email": should_email,
        "latest_event": updated_event
    }

