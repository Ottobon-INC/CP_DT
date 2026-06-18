import logging
from datetime import datetime, timezone, date
from typing import Dict, Any, Optional, List
from app.services.supabase_client import (
    insert_engagement_snapshot,
    get_engagement_snapshots,
    fetch_learner_data_rest,
    get_login_sessions,
    load_inactivity_state,
)
from app.services.login_tracking import get_days_since_last_login

logger = logging.getLogger(__name__)


def _compute_engagement_score(
    progress_pct: float,
    quiz_pass_rate: float,
    days_since_login: Optional[int],
    inactivity_stage: int,
) -> float:
    """
    Computes a 0–100 engagement score from multiple metrics.
    Higher = more engaged.
    """
    score = 0.0

    # Progress contribution (0-35 points)
    score += min(progress_pct * 0.35, 35.0)

    # Quiz performance (0-25 points)
    score += min(quiz_pass_rate * 25.0, 25.0)

    # Login recency (0-30 points): full marks if logged in today, decays over 30 days
    if days_since_login is not None:
        login_score = max(0, 30.0 - (days_since_login * 1.0))
        score += login_score
    else:
        score += 0  # No login history

    # Inactivity penalty (-5 per stage)
    inactivity_penalty = min(inactivity_stage * 5, 20)
    score -= inactivity_penalty

    # Baseline engagement (10 points just for being enrolled)
    score += 10

    return round(max(0, min(score, 100)), 1)


def capture_engagement_snapshot(learner_id: str, course_id: str) -> Optional[Dict[str, Any]]:
    """
    Captures a point-in-time engagement snapshot for a learner in a specific course.
    Aggregates data from multiple sources into a single record.
    """
    try:
        today = date.today().isoformat()

        # 1. Fetch learner progress data
        raw_data = fetch_learner_data_rest(learner_id, course_id=course_id)
        module_progress = raw_data.get("module_progress", [])
        quiz_attempts = raw_data.get("quiz_attempts", [])

        # Module stats
        total_modules = len(module_progress)
        modules_completed = sum(1 for m in module_progress if m.get("status") == "completed")
        overall_progress_pct = 0.0
        if total_modules > 0:
            overall_progress_pct = round(
                sum(m.get("completed_percentage", 0) for m in module_progress) / total_modules, 1
            )

        # Quiz stats
        total_quiz_attempts = len(quiz_attempts)
        quiz_pass_rate = 0.0
        avg_quiz_score = 0.0
        if total_quiz_attempts > 0:
            passed = sum(1 for q in quiz_attempts if q.get("passed"))
            quiz_pass_rate = round(passed / total_quiz_attempts, 2)
            avg_quiz_score = round(
                sum(q.get("score", 0) for q in quiz_attempts) / total_quiz_attempts, 1
            )

        # 2. Login stats
        days_since_login = get_days_since_last_login(learner_id)
        login_sessions = get_login_sessions(learner_id, limit=100)
        total_login_count = len(login_sessions)
        total_duration = sum(s.get("duration_seconds", 0) or 0 for s in login_sessions)
        avg_session_duration = total_duration // total_login_count if total_login_count > 0 else 0

        # 3. Inactivity state
        inactivity_record = load_inactivity_state(learner_id)
        inactivity_stage = inactivity_record.get("inactivity_stage", 0) if inactivity_record else 0

        # 4. Compute engagement score
        engagement_score = _compute_engagement_score(
            progress_pct=overall_progress_pct,
            quiz_pass_rate=quiz_pass_rate,
            days_since_login=days_since_login,
            inactivity_stage=inactivity_stage,
        )

        # 5. Build and insert snapshot
        snapshot = {
            "learner_id": learner_id,
            "course_id": course_id,
            "snapshot_date": today,
            "overall_progress_pct": overall_progress_pct,
            "modules_completed": modules_completed,
            "total_modules": total_modules,
            "days_since_last_login": days_since_login,
            "total_login_count": total_login_count,
            "avg_session_duration_seconds": avg_session_duration,
            "quiz_pass_rate": quiz_pass_rate,
            "avg_quiz_score": avg_quiz_score,
            "total_quiz_attempts": total_quiz_attempts,
            "inactivity_stage": inactivity_stage,
            "engagement_score": engagement_score,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = insert_engagement_snapshot(snapshot)
        logger.info(
            f"Engagement snapshot captured for learner {learner_id}, "
            f"course {course_id}: score={engagement_score}"
        )
        return result

    except Exception as e:
        logger.error(f"Error capturing engagement snapshot for learner {learner_id}: {e}")
        return None


def get_engagement_history(learner_id: str, course_id: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
    """Returns historical engagement snapshots for a learner."""
    return get_engagement_snapshots(learner_id, course_id=course_id, limit=limit)
