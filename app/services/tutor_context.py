import logging
from typing import Optional, Dict, Any, List
from app.services.supabase_client import fetch_tutor_data_rest

logger = logging.getLogger(__name__)


def fetch_tutor_data(tutor_id: str, course_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches raw tutor profile and course association records via Supabase REST API.
    """
    return fetch_tutor_data_rest(tutor_id, course_id=course_id)


def aggregate_tutor_context(tutor_id: str, course_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Processes and aggregates raw tutor context variables into a structured dictionary.
    """
    raw_data = fetch_tutor_data(tutor_id, course_id=course_id)
    
    profile = raw_data.get("tutor_profile") or {}
    tutor_display_name = profile.get("display_name", "AI Assistant")
    tutor_bio = profile.get("bio", "Default tutoring assistant profile.")
    
    courses_taught = [c.get("title") for c in raw_data.get("courses_taught", [])]
    
    suggestions = raw_data.get("prompt_suggestions", [])
    tutor_prompt_guidance = [
        {
            "topic_id": s.get("topic_id"),
            "guidance": s.get("guidance") or s.get("suggestion")
        }
        for s in suggestions
    ]
    
    topics = raw_data.get("topics_data", [])
    submissions = raw_data.get("submissions_info", [])
    relevant_course_knowledge = {
        "topics": [{"topic_id": t.get("topic_id"), "title": t.get("title"), "snippet": (t.get("content") or "")[:100]} for t in topics],
        "recent_submissions_summary": {
            "total_reviewed": len(submissions),
            "pending_reviews": sum(1 for s in submissions if s.get("status") == "pending")
        }
    }
    
    return {
        "tutor_display_name": tutor_display_name,
        "tutor_bio": tutor_bio,
        "courses_taught": courses_taught,
        "tutor_prompt_guidance": tutor_prompt_guidance,
        "relevant_course_knowledge": relevant_course_knowledge
    }
