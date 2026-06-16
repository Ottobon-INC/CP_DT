import logging
from typing import Optional, Dict, Any
from app.services.supabase_client import get_latest_learner_event_rest

logger = logging.getLogger(__name__)


def get_latest_learner_event(learner_id: str, course_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves the latest telemetry event for a given learner via Supabase REST API.
    """
    return get_latest_learner_event_rest(learner_id, course_id=course_id)
