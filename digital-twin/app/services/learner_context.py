import logging
from typing import Optional, Dict, Any, List
from app.services.supabase_client import fetch_learner_data_rest

logger = logging.getLogger(__name__)


def fetch_learner_data(learner_id: str, course_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches raw learner telemetry and progress records via Supabase REST API.
    Delegates to the centralised supabase_client.
    """
    return fetch_learner_data_rest(learner_id, course_id=course_id)


def aggregate_learner_context(learner_id: str, course_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Processes and aggregates raw user telemetry records into a structured context dict.
    """
    raw_data = fetch_learner_data(learner_id, course_id=course_id)
    
    # 1. Current Course Progress
    module_progress = raw_data.get("module_progress", [])
    if module_progress:
        avg_progress = sum(item.get("completed_percentage", 0.0) for item in module_progress) / len(module_progress)
        current_course_progress = {
            "average_completed_percentage": round(avg_progress, 2),
            "modules_tracked": len(module_progress),
            "statuses": [item.get("status") for item in module_progress]
        }
    else:
        current_course_progress = {
            "average_completed_percentage": 0.0,
            "modules_tracked": 0,
            "statuses": []
        }

    # 2. Active Topic
    topic_progress = raw_data.get("topic_progress", [])
    active_topic = None
    if topic_progress:
        incomplete_topics = [t for t in topic_progress if not t.get("completed")]
        if incomplete_topics:
            active_topic = incomplete_topics[0].get("topic_id")
        else:
            active_topic = topic_progress[-1].get("topic_id")

    # 3. Quiz Performance Summary
    quiz_attempts = raw_data.get("quiz_attempts", [])
    if quiz_attempts:
        total_quizzes = len(quiz_attempts)
        passed_quizzes = sum(1 for q in quiz_attempts if q.get("passed"))
        avg_score = sum(q.get("score", 0.0) for q in quiz_attempts) / total_quizzes
        quiz_performance_summary = {
            "total_attempts": total_quizzes,
            "pass_rate": round(passed_quizzes / total_quizzes, 2),
            "average_score": round(avg_score, 2)
        }
    else:
        quiz_performance_summary = {
            "total_attempts": 0,
            "pass_rate": 0.0,
            "average_score": 0.0
        }

    # 4. Learner Persona
    persona_profiles = raw_data.get("learner_persona_profiles", [])
    if persona_profiles:
        learner_persona = {
            "type": persona_profiles[0].get("persona_type"),
            "profile_details": persona_profiles[0].get("profile_data")
        }
    else:
        learner_persona = {
            "type": "standard",
            "profile_details": {}
        }

    # 5. Recent AI Chat Summaries
    chat_messages = raw_data.get("cp_rag_chat_messages", [])
    recent_ai_chat_summaries = []
    for msg in chat_messages:
        role = msg.get("role")
        content = msg.get("content", "")
        snippet = content[:60] + "..." if len(content) > 60 else content
        recent_ai_chat_summaries.append({
            "session_id": msg.get("session_id"),
            "role": role,
            "message_snippet": snippet
        })

    # 6. Login activities
    from app.services.login_tracking import get_login_history
    login_info = get_login_history(learner_id)
    login_activity = {
        "days_since_last_login": login_info.get("days_since_last_login"),
        "total_sessions": login_info.get("total_sessions", 0),
        "average_session_duration_seconds": login_info.get("average_session_duration_seconds", 0)
    }

    # 7. Engagement details
    from app.services.engagement_tracker import get_engagement_history
    snapshots = get_engagement_history(learner_id, course_id=course_id, limit=5)
    engagement_details = {
        "latest_score": snapshots[0].get("engagement_score", 100.0) if snapshots else 100.0,
        "inactivity_stage": snapshots[0].get("inactivity_stage", 0) if snapshots else 0,
        "recent_scores": [s.get("engagement_score") for s in snapshots if s.get("engagement_score") is not None]
    }

    return {
        "current_course_progress": current_course_progress,
        "active_topic": active_topic,
        "quiz_performance_summary": quiz_performance_summary,
        "learner_persona": learner_persona,
        "recent_ai_chat_summaries": recent_ai_chat_summaries,
        "login_activity": login_activity,
        "engagement_details": engagement_details
    }
