import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.services.supabase_client import (
    insert_login_session,
    update_login_session_logout,
    get_latest_login_session,
    get_login_sessions,
)

logger = logging.getLogger(__name__)


def record_login(learner_id: str) -> Optional[Dict[str, Any]]:
    """
    Records a new login session for the learner.
    Returns the created session record including session_id.
    """
    result = insert_login_session(learner_id)
    if result:
        logger.info(f"Login session recorded for learner {learner_id}: {result.get('session_id')}")
    else:
        logger.warning(f"Failed to record login session for learner {learner_id}")
    return result


def record_logout(learner_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Records a logout event for an existing session.
    Calculates and stores the session duration in seconds.
    """
    # Get the session to calculate duration
    session = get_latest_login_session(learner_id)
    if not session or session.get("session_id") != session_id:
        logger.warning(f"Session {session_id} not found for learner {learner_id}")
        return None

    login_at_str = session.get("login_at")
    if not login_at_str:
        logger.warning(f"No login_at timestamp for session {session_id}")
        return None

    try:
        if isinstance(login_at_str, str):
            login_at = datetime.fromisoformat(login_at_str.replace("Z", "+00:00"))
        else:
            login_at = login_at_str

        if login_at.tzinfo is None:
            login_at = login_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        duration_seconds = int((now - login_at).total_seconds())
    except Exception as e:
        logger.warning(f"Error calculating session duration: {e}")
        duration_seconds = 0

    result = update_login_session_logout(session_id, duration_seconds)
    if result:
        logger.info(f"Logout recorded for session {session_id}. Duration: {duration_seconds}s")
    return result


def get_days_since_last_login(learner_id: str) -> Optional[int]:
    """
    Calculates the number of days since the learner's last login.
    Returns None if no login history exists.
    """
    session = get_latest_login_session(learner_id)
    if not session:
        return None

    login_at_str = session.get("login_at")
    if not login_at_str:
        return None

    try:
        if isinstance(login_at_str, str):
            login_at = datetime.fromisoformat(login_at_str.replace("Z", "+00:00"))
        else:
            login_at = login_at_str

        if login_at.tzinfo is None:
            login_at = login_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        return (now - login_at).days
    except Exception:
        return None


def get_login_history(learner_id: str, limit: int = 20) -> Dict[str, Any]:
    """
    Returns the learner's login history along with computed statistics.
    """
    sessions = get_login_sessions(learner_id, limit=limit)
    days_since = get_days_since_last_login(learner_id)

    total_sessions = len(sessions)
    total_duration = sum(s.get("duration_seconds", 0) or 0 for s in sessions)
    avg_duration = total_duration // total_sessions if total_sessions > 0 else 0

    return {
        "learner_id": learner_id,
        "days_since_last_login": days_since,
        "total_sessions": total_sessions,
        "total_duration_seconds": total_duration,
        "average_session_duration_seconds": avg_duration,
        "sessions": sessions,
    }
