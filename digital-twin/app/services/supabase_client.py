"""
Supabase REST API client for all database operations.
Replaces direct Postgres (SessionLocal) with HTTP calls to the PostgREST API.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ─── Supabase REST Configuration ───────────────────────────────────

_BASE_URL = f"{settings.SUPABASE_URL}/rest/v1" if settings.SUPABASE_URL else None
_HEADERS = {
    "apikey": settings.SUPABASE_ANON_KEY or "",
    "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY or ''}",
    "Content-Type": "application/json",
}


# ─── Low-Level HTTP Helpers ─────────────────────────────────────────

def _get(table: str, params: Dict[str, str]) -> List[Dict[str, Any]]:
    """GET rows from a Supabase table. Returns [] on failure."""
    if not _BASE_URL:
        logger.warning("SUPABASE_URL is not configured.")
        return []
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{_BASE_URL}/{table}", headers=_HEADERS, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Supabase GET '{table}' failed: {e}")
        return []


def _post(table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """INSERT a row into a Supabase table. Returns the created row or None."""
    if not _BASE_URL:
        logger.warning("SUPABASE_URL is not configured.")
        return None
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{_BASE_URL}/{table}",
                headers={**_HEADERS, "Prefer": "return=representation"},
                json=data,
            )
            resp.raise_for_status()
            rows = resp.json()
            return rows[0] if rows else data
    except Exception as e:
        logger.warning(f"Supabase POST '{table}' failed: {e}")
        return None


def _patch(table: str, params: Dict[str, str], data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """UPDATE rows in a Supabase table matching params. Returns updated row or None."""
    if not _BASE_URL:
        logger.warning("SUPABASE_URL is not configured.")
        return None
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.patch(
                f"{_BASE_URL}/{table}",
                headers={**_HEADERS, "Prefer": "return=representation"},
                params=params,
                json=data,
            )
            resp.raise_for_status()
            rows = resp.json()
            return rows[0] if rows else data
    except Exception as e:
        logger.warning(f"Supabase PATCH '{table}' failed: {e}")
        return None


def _upsert(table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """INSERT or UPDATE (upsert) a row. Requires primary key in data."""
    if not _BASE_URL:
        logger.warning("SUPABASE_URL is not configured.")
        return None
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{_BASE_URL}/{table}",
                headers={
                    **_HEADERS,
                    "Prefer": "return=representation,resolution=merge-duplicates",
                },
                json=data,
            )
            resp.raise_for_status()
            rows = resp.json()
            return rows[0] if rows else data
    except Exception as e:
        logger.warning(f"Supabase UPSERT '{table}' failed: {e}")
        return None


# ─── Learner Data Functions ─────────────────────────────────────────

def fetch_learner_data_rest(learner_id: str, course_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetches raw learner data from Supabase via REST API."""
    data: Dict[str, Any] = {
        "topic_progress": [],
        "module_progress": [],
        "quiz_attempts": [],
        "cp_rag_chat_messages": [],
        "learner_persona_profiles": [],
    }

    try:
        uuid.UUID(learner_id)
    except (ValueError, TypeError):
        return data

    # 1. Topic Progress
    topic_params = {
        "select": "*",
        "user_id": f"eq.{learner_id}",
        "order": "updated_at.desc",
    }
    if course_id:
        topics = _get("topics", {"select": "topic_id", "course_id": f"eq.{course_id}"})
        topic_ids = [t.get("topic_id") for t in topics if t.get("topic_id")]
        if topic_ids:
            topic_params["topic_id"] = f"in.({','.join(topic_ids)})"
        else:
            topic_params["topic_id"] = "in.(none)"

    rows = _get("topic_progress", topic_params)
    data["topic_progress"] = [
        {"topic_id": r.get("topic_id"), "completed": r.get("is_completed", False), "score": r.get("last_position_s")}
        for r in rows
    ]

    # 2. Module Progress
    module_params = {
        "select": "*",
        "user_id": f"eq.{learner_id}",
        "order": "updated_at.desc",
    }
    if course_id:
        module_params["course_id"] = f"eq.{course_id}"

    rows = _get("module_progress", module_params)
    data["module_progress"] = [
        {"module_id": f"{r.get('course_id')}/m{r.get('module_no')}", "completed_percentage": _calc_module_pct(r), "status": _module_status(r)}
        for r in rows
    ]

    # 3. Quiz Attempts
    quiz_params = {
        "select": "*",
        "user_id": f"eq.{learner_id}",
        "order": "created_at.desc",
    }
    if course_id:
        quiz_params["course_id"] = f"eq.{course_id}"

    rows = _get("quiz_attempts", quiz_params)
    data["quiz_attempts"] = [
        {"quiz_id": r.get("assessment_id") or r.get("attempt_id"), "score": float(r.get("score", 0)), "passed": r.get("status") == "passed"}
        for r in rows
    ]

    # 4. Chat Messages
    chat_params = {
        "select": "message_id,session_id,role,content,created_at",
        "user_id": f"eq.{learner_id}",
        "order": "created_at.desc",
        "limit": "5",
    }
    if course_id:
        chat_sessions = _get("cp_rag_chat_sessions", {
            "select": "session_id",
            "user_id": f"eq.{learner_id}",
            "course_id": f"eq.{course_id}",
        })
        session_ids = [s.get("session_id") for s in chat_sessions if s.get("session_id")]
        if session_ids:
            chat_params["session_id"] = f"in.({','.join(session_ids)})"
        else:
            chat_params["session_id"] = "in.(none)"

    rows = _get("cp_rag_chat_messages", chat_params)
    data["cp_rag_chat_messages"] = [
        {"session_id": r.get("session_id"), "role": r.get("role"), "content": r.get("content", "")}
        for r in rows
    ]

    # 5. Persona Profiles
    persona_params = {
        "select": "*",
        "user_id": f"eq.{learner_id}",
    }
    if course_id:
        persona_params["course_id"] = f"eq.{course_id}"

    rows = _get("learner_persona_profiles", persona_params)
    data["learner_persona_profiles"] = [
        {"persona_type": r.get("persona_key"), "profile_data": r.get("analysis_summary")}
        for r in rows
    ]

    return data


def get_latest_learner_event_rest(learner_id: str, course_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the latest telemetry event for a learner via Supabase REST."""
    params = {
        "select": "event_type,derived_status,created_at",
        "user_id": f"eq.{learner_id}",
        "order": "created_at.desc",
        "limit": "1",
    }
    if course_id:
        params["course_id"] = f"eq.{course_id}"

    rows = _get("learner_activity_events", params)
    if rows:
        r = rows[0]
        return {"event_type": r.get("event_type"), "derived_status": r.get("derived_status"), "created_at": r.get("created_at")}
    return None


def fetch_learner_courses_data_rest(learner_id: str, course_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetches raw learner data and progress from Supabase via REST API,
    segmented for each course the learner is enrolled in.
    """
    try:
        uuid.UUID(learner_id)
    except (ValueError, TypeError):
        return []

    # 1. Get all enrollments for the learner
    enrollment_rows = _get("enrollments", {
        "select": "course_id",
        "user_id": f"eq.{learner_id}",
    })
    course_ids = list({r.get("course_id") for r in enrollment_rows if r.get("course_id")})
    
    if course_id:
        course_ids = [c for c in course_ids if c == course_id]
    
    if not course_ids:
        return []

    courses_data = []

    for course_id in course_ids:
        # 2. Get course name
        course_rows = _get("courses", {
            "select": "course_name",
            "course_id": f"eq.{course_id}",
            "limit": "1",
        })
        course_name = course_rows[0].get("course_name", "Unknown Course") if course_rows else "Unknown Course"

        # 3. Get topics for this course (to filter topic_progress)
        topics = _get("topics", {
            "select": "topic_id",
            "course_id": f"eq.{course_id}",
        })
        topic_ids = [t.get("topic_id") for t in topics if t.get("topic_id")]

        # Filter topic_progress
        topic_progress_list = []
        if topic_ids:
            topic_filter = ",".join(topic_ids)
            tp_rows = _get("topic_progress", {
                "select": "*",
                "user_id": f"eq.{learner_id}",
                "topic_id": f"in.({topic_filter})",
                "order": "updated_at.desc",
            })
            topic_progress_list = [
                {"topic_id": r.get("topic_id"), "completed": r.get("is_completed", False), "score": r.get("last_position_s")}
                for r in tp_rows
            ]

        # 4. Get module_progress for this course
        mp_rows = _get("module_progress", {
            "select": "*",
            "user_id": f"eq.{learner_id}",
            "course_id": f"eq.{course_id}",
            "order": "updated_at.desc",
        })
        module_progress_list = [
            {"module_id": f"{r.get('course_id')}/m{r.get('module_no')}", "completed_percentage": _calc_module_pct(r), "status": _module_status(r)}
            for r in mp_rows
        ]

        # 5. Get quiz attempts for this course
        qa_rows = _get("quiz_attempts", {
            "select": "*",
            "user_id": f"eq.{learner_id}",
            "course_id": f"eq.{course_id}",
            "order": "created_at.desc",
        })
        quiz_attempts_list = [
            {"quiz_id": r.get("assessment_id") or r.get("attempt_id"), "score": float(r.get("score", 0)), "passed": r.get("status") == "passed"}
            for r in qa_rows
        ]

        # 6. Get chat messages for this course (via cp_rag_chat_sessions)
        chat_sessions = _get("cp_rag_chat_sessions", {
            "select": "session_id",
            "user_id": f"eq.{learner_id}",
            "course_id": f"eq.{course_id}",
        })
        session_ids = [s.get("session_id") for s in chat_sessions if s.get("session_id")]
        
        chat_messages_list = []
        if session_ids:
            session_filter = ",".join(session_ids)
            msg_rows = _get("cp_rag_chat_messages", {
                "select": "message_id,session_id,role,content,created_at",
                "session_id": f"in.({session_filter})",
                "order": "created_at.desc",
                "limit": "5",
            })
            chat_messages_list = [
                {"session_id": r.get("session_id"), "role": r.get("role"), "content": r.get("content", "")}
                for r in msg_rows
            ]

        # 7. Get persona profiles for this course
        pp_rows = _get("learner_persona_profiles", {
            "select": "*",
            "user_id": f"eq.{learner_id}",
            "course_id": f"eq.{course_id}",
        })
        persona_profiles_list = [
            {"persona_type": r.get("persona_key"), "profile_data": r.get("analysis_summary")}
            for r in pp_rows
        ]

        # 8. Get latest activity event for this course
        la_rows = _get("learner_activity_events", {
            "select": "event_type,derived_status,created_at",
            "user_id": f"eq.{learner_id}",
            "course_id": f"eq.{course_id}",
            "order": "created_at.desc",
            "limit": "1",
        })
        latest_event = None
        if la_rows:
            r = la_rows[0]
            latest_event = {"event_type": r.get("event_type"), "derived_status": r.get("derived_status"), "created_at": r.get("created_at")}

        courses_data.append({
            "course_id": course_id,
            "course_name": course_name,
            "topic_progress": topic_progress_list,
            "module_progress": module_progress_list,
            "quiz_attempts": quiz_attempts_list,
            "cp_rag_chat_messages": chat_messages_list,
            "learner_persona_profiles": persona_profiles_list,
            "latest_activity_event": latest_event,
        })

    return courses_data


# ─── Tutor Data Functions ───────────────────────────────────────────

def fetch_tutor_data_rest(tutor_id: str, course_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetches tutor profile and course association records via Supabase REST."""
    data: Dict[str, Any] = {
        "tutor_profile": None,
        "courses_taught": [],
        "prompt_suggestions": [],
        "submissions_info": [],
        "topics_data": [],
    }

    try:
        uuid.UUID(tutor_id)
    except (ValueError, TypeError):
        data["tutor_profile"] = {"display_name": "AI Assistant", "bio": "Tutor (AI Assistant)"}
        return data

    # 1. Tutor Profile — from users table (tutor_profiles doesn't exist)
    rows = _get("users", {
        "select": "full_name,role",
        "user_id": f"eq.{tutor_id}",
        "limit": "1",
    })
    if rows:
        r = rows[0]
        data["tutor_profile"] = {"display_name": r.get("full_name", "AI Assistant"), "bio": f"Tutor ({r.get('role', 'tutor')})"}

    # 2. Courses taught — via course_tutors join
    ct_rows = _get("course_tutors", {
        "select": "course_id",
        "tutor_id": f"eq.{tutor_id}",
        "is_active": "eq.true",
    })
    course_ids = [r.get("course_id") for r in ct_rows if r.get("course_id")]
    
    if course_id:
        course_ids = [c for c in course_ids if c == course_id]

    if course_ids:
        # Fetch course names for those course_ids
        course_filter = ",".join(course_ids)
        course_rows = _get("courses", {
            "select": "course_id,course_name",
            "course_id": f"in.({course_filter})",
        })
        data["courses_taught"] = [{"course_id": r.get("course_id"), "title": r.get("course_name")} for r in course_rows]

        # 3. Prompt suggestions for those courses
        suggestion_rows = _get("topic_prompt_suggestions", {
            "select": "topic_id,prompt_text,answer",
            "course_id": f"in.({course_filter})",
            "is_active": "eq.true",
        })
        data["prompt_suggestions"] = [
            {"topic_id": r.get("topic_id"), "suggestion": r.get("prompt_text"), "guidance": r.get("answer")}
            for r in suggestion_rows
        ]

        # 4. Topics data for those courses
        topic_rows = _get("topics", {
            "select": "topic_id,topic_name,text_content,course_id",
            "course_id": f"in.({course_filter})",
        })
        data["topics_data"] = [
            {"topic_id": r.get("topic_id"), "title": r.get("topic_name"), "content": r.get("text_content")}
            for r in topic_rows
        ]

    # 5. Course submissions by this tutor
    sub_rows = _get("course_submissions", {
        "select": "submission_id,status,course_name",
        "tutor_id": f"eq.{tutor_id}",
    })
    data["submissions_info"] = [
        {"submission_id": r.get("submission_id"), "status": r.get("status"), "grade": None}
        for r in sub_rows
    ]

    return data


# ─── Inactivity Tracking Functions ──────────────────────────────────

def load_inactivity_state(learner_id: str) -> Optional[Dict[str, Any]]:
    """Load inactivity state for a learner from twin_inactivity_state table."""
    try:
        uuid.UUID(learner_id)
    except (ValueError, TypeError):
        return None

    rows = _get("twin_inactivity_state", {
        "select": "*",
        "learner_id": f"eq.{learner_id}",
        "limit": "1",
    })
    return rows[0] if rows else None


def save_inactivity_state(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Upsert inactivity state for a learner."""
    learner_id = record.get("learner_id")
    try:
        uuid.UUID(learner_id)
    except (ValueError, TypeError):
        return None

    return _upsert("twin_inactivity_state", record)


# ─── Messaging Functions ───────────────────────────────────────────

def insert_message(conversation_id: str, sender_id: str, content: str) -> bool:
    """Insert a message into cp_messages via Supabase REST."""
    now = datetime.now(timezone.utc).isoformat()
    row = _post("cp_messages", {
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "content": content,
        "type": "text",
        "is_pinned": False,
        "is_edited": False,
        "is_deleted": False,
        "created_at": now,
        "updated_at": now,
    })
    return row is not None


# ─── Enrollment / Scheduler Functions ───────────────────────────────

def get_enrolled_user_ids() -> List[str]:
    """Get distinct enrolled user IDs from the enrollments table."""
    rows = _get("enrollments", {
        "select": "user_id",
        "status": "eq.active",
    })
    if not rows:
        # Fallback: get distinct user_ids from activity events
        rows = _get("learner_activity_events", {
            "select": "user_id",
            "limit": "200",
        })
    user_ids = list({r.get("user_id") for r in rows if r.get("user_id")})
    return user_ids if user_ids else ["demo_learner"]


def resolve_tutor_id_for_learner(learner_id: str, course_id: Optional[str] = None) -> str:
    """
    Finds the tutor_id assigned to the course that the learner is enrolled in.
    Falls back to a default tutor UUID if none found.
    """
    try:
        uuid.UUID(learner_id)
    except (ValueError, TypeError):
        return "118c9345-a7e5-4d0f-91f3-fbe2e16d4c60"

    resolved_course_id = course_id

    # 1. If course_id is not provided, get active enrollment for the learner
    if not resolved_course_id:
        enrollment_rows = _get("enrollments", {
            "select": "course_id",
            "user_id": f"eq.{learner_id}",
            "status": "eq.active",
            "limit": "1",
        })
        if not enrollment_rows:
            enrollment_rows = _get("enrollments", {
                "select": "course_id",
                "user_id": f"eq.{learner_id}",
                "limit": "1",
            })
            
        if enrollment_rows and enrollment_rows[0].get("course_id"):
            resolved_course_id = enrollment_rows[0].get("course_id")

    if resolved_course_id:
        # 2. Get the course_tutors details to find tutor_id
        course_rows = _get("course_tutors", {
            "select": "tutor_id",
            "course_id": f"eq.{resolved_course_id}",
            "is_active": "eq.true",
            "limit": "1",
        })
        if not course_rows:
            # Fallback to the course table just in case
            course_rows = _get("courses", {
                "select": "tutor_id",
                "course_id": f"eq.{resolved_course_id}",
                "limit": "1",
            })
            
        if course_rows and course_rows[0].get("tutor_id"):
            tutor_id = course_rows[0].get("tutor_id")
            try:
                uuid.UUID(tutor_id)
                return tutor_id
            except (ValueError, TypeError):
                pass
            
    # Fallback to the first tutor in the users table
    tutor_rows = _get("users", {
        "select": "user_id",
        "role": "eq.tutor",
        "limit": "1",
    })
    if tutor_rows:
        return tutor_rows[0].get("user_id")
        
    return "118c9345-a7e5-4d0f-91f3-fbe2e16d4c60"


def resolve_conversation_id(learner_id: str, tutor_id: str) -> str:
    """
    Finds or creates a conversation UUID between the learner and the tutor.
    """
    try:
        uuid.UUID(learner_id)
        uuid.UUID(tutor_id)
    except (ValueError, TypeError):
        return "00000000-0000-0000-0000-000000000000"

    # 1. Search if a conversation already exists where learner is a member
    members = _get("cp_conversation_members", {
        "select": "conversation_id",
        "user_id": f"eq.{learner_id}",
        "limit": "10",
    })
    if members:
        return members[0].get("conversation_id")
        
    # 2. If no conversation exists, create a new one!
    conv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Create the conversation record
    _post("cp_conversations", {
        "id": conv_id,
        "type": "peer_tutor",
        "title": f"Tutor Conversation for Learner {learner_id[:8]}",
        "created_at": now,
        "updated_at": now,
    })
    
    # Add the learner as a member
    _post("cp_conversation_members", {
        "conversation_id": conv_id,
        "user_id": learner_id,
        "joined_at": now,
    })
    
    # Add the tutor as a member
    _post("cp_conversation_members", {
        "conversation_id": conv_id,
        "user_id": tutor_id,
        "joined_at": now,
    })
    
    return conv_id


# ─── Helpers ────────────────────────────────────────────────────────

def _calc_module_pct(row: Dict[str, Any]) -> float:
    """Estimate module completion percentage from available columns."""
    if row.get("module_completed"):
        return 100.0
    videos = row.get("videos_completed", 0) or 0
    quiz = 1 if row.get("quiz_passed") else 0
    assign = 1 if row.get("assignments_complete") else 0
    total_parts = 7
    done = videos + quiz + assign
    return round(min(done / total_parts * 100, 100), 1)


def _module_status(row: Dict[str, Any]) -> str:
    """Derive a status string from module_progress columns."""
    if row.get("module_completed"):
        return "completed"
    if row.get("is_unlocked"):
        return "in_progress"
    return "locked"
