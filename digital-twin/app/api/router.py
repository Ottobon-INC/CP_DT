from fastapi import APIRouter, HTTPException, status
from app.database.session import check_db_connectivity
from app.services.twin_orchestrator import run_digital_twin
from app.api.schemas import (
    LearnerDetailsResponse,
    LearnerRawDataResponse,
    AggregatedContextResponse,
    InactivityStateResponse,
    LatestActivityEvent,
    CourseSpecificDetails,
)

api_router = APIRouter()


# ─── Health ──────────────────────────────────────────────────────────

@api_router.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify service startup and readiness.
    """
    return {"status": "healthy"}

@api_router.get("/health/db", tags=["Health"])
async def health_db_check():
    """
    Health check endpoint to verify connection to the database.
    """
    if check_db_connectivity():
        return {"database": "connected"}
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database connection failure"
    )


# ─── Twin Pipeline ──────────────────────────────────────────────────

from typing import Optional

@api_router.post("/twin/run/{learner_id}", tags=["Twin Pipeline"])
async def trigger_digital_twin(learner_id: str, course_id: Optional[str] = None):
    """
    Manually triggers the Digital Twin workflow for a specific learner.
    Runs the pipeline nodes sequentially and returns the final TwinState.
    """
    try:
        state = run_digital_twin(learner_id, course_id=course_id)
        return {
            "status": "success",
            "message": f"Digital Twin pipeline executed successfully for learner {learner_id}.",
            "state": state
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Digital Twin pipeline execution failed: {str(e)}"
        )

@api_router.get("/twin/inactivity/{learner_id}", tags=["Twin Pipeline"])
async def get_learner_inactivity_state(learner_id: str):
    """
    Retrieves the persistent inactivity tracking state and details for a specific learner.
    """
    from app.services.supabase_client import load_inactivity_state
    record = load_inactivity_state(learner_id)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inactivity tracking state not found for learner {learner_id}"
        )
        
    return {
        "learner_id": record.get("learner_id"),
        "last_activity_at": record.get("last_activity_at"),
        "inactivity_stage": record.get("inactivity_stage"),
        "first_message_sent_at": record.get("first_message_sent_at"),
        "second_message_sent_at": record.get("second_message_sent_at"),
        "third_message_sent_at": record.get("third_message_sent_at"),
        "email_sent_at": record.get("email_sent_at"),
        "is_active": record.get("is_active"),
        "updated_at": record.get("updated_at")
    }


# ─── Learner Details ────────────────────────────────────────────────

@api_router.get(
    "/learner/{learner_id}/details",
    response_model=LearnerDetailsResponse,
    tags=["Learner"],
    summary="Get complete learner details",
    description=(
        "Returns a comprehensive profile for the given **learner_id**, comprising:\n\n"
        "- **Segmented raw data per course** – topic progress, module progress, quiz attempts, "
        "chat messages, persona profiles, and the latest telemetry event grouped by course.\n"
        "- **Segmented aggregated context per course** – computed course progress, quiz performance "
        "summary, active topic, persona classification, and recent AI chat snippets per course.\n"
        "- **Inactivity state** – persistent inactivity tracking record "
        "(null if the learner has no inactivity history)."
    ),
)
async def get_learner_details(learner_id: str, course_id: Optional[str] = None):
    """
    Fetches all available data for a learner from Supabase REST API
    and returns it in a single, structured response.
    """
    import logging
    from app.services.supabase_client import fetch_learner_courses_data_rest
    log = logging.getLogger(__name__)

    # 1. Fetch segmented course data via Supabase REST API
    courses_raw_data = fetch_learner_courses_data_rest(learner_id, course_id=course_id)

    courses_list = []
    for c_data in courses_raw_data:
        course_id = c_data["course_id"]
        course_name = c_data["course_name"]

        # Parse latest activity event
        latest_event = c_data.get("latest_activity_event")
        latest_event_obj = None
        if latest_event:
            latest_event_obj = LatestActivityEvent(**latest_event)

        # Build raw data response
        raw_response = LearnerRawDataResponse(
            topic_progress=c_data.get("topic_progress", []),
            module_progress=c_data.get("module_progress", []),
            quiz_attempts=c_data.get("quiz_attempts", []),
            cp_rag_chat_messages=c_data.get("cp_rag_chat_messages", []),
            learner_persona_profiles=c_data.get("learner_persona_profiles", []),
            latest_activity_event=latest_event_obj,
        )

        # Aggregated / computed context (specific to this course)
        aggregated = _aggregate_from_raw(c_data)
        aggregated_response = AggregatedContextResponse(**aggregated)

        # Build course specific details
        course_detail = CourseSpecificDetails(
            course_id=course_id,
            course_name=course_name,
            raw_data=raw_response,
            aggregated_context=aggregated_response,
        )
        courses_list.append(course_detail)

    # 2. Inactivity tracking state (global – via Supabase REST)
    inactivity_response = None
    try:
        from app.services.supabase_client import load_inactivity_state
        r = load_inactivity_state(learner_id)
        if r:
            inactivity_response = InactivityStateResponse(
                learner_id=r.get("learner_id", learner_id),
                last_activity_at=r.get("last_activity_at"),
                inactivity_stage=r.get("inactivity_stage", 0),
                first_message_sent_at=r.get("first_message_sent_at"),
                second_message_sent_at=r.get("second_message_sent_at"),
                third_message_sent_at=r.get("third_message_sent_at"),
                email_sent_at=r.get("email_sent_at"),
                is_active=r.get("is_active", True),
                updated_at=r.get("updated_at"),
            )
    except Exception as e:
        log.warning(f"Could not fetch inactivity state for learner {learner_id}: {e}")

    return LearnerDetailsResponse(
        learner_id=learner_id,
        courses=courses_list,
        inactivity_state=inactivity_response,
    )


def _aggregate_from_raw(raw_data: dict) -> dict:
    """
    Inline aggregation logic — mirrors aggregate_learner_context()
    but works directly on the raw_data dict without a second DB call.
    """
    # Course progress
    module_progress = raw_data.get("module_progress", [])
    if module_progress:
        avg_pct = sum(m.get("completed_percentage", 0) for m in module_progress) / len(module_progress)
        course_progress = {
            "average_completed_percentage": round(avg_pct, 2),
            "modules_tracked": len(module_progress),
            "statuses": [m.get("status") for m in module_progress],
        }
    else:
        course_progress = {"average_completed_percentage": 0.0, "modules_tracked": 0, "statuses": []}

    # Active topic
    topics = raw_data.get("topic_progress", [])
    active_topic = None
    if topics:
        incomplete = [t for t in topics if not t.get("completed")]
        active_topic = (incomplete[0] if incomplete else topics[-1]).get("topic_id")

    # Quiz performance
    quizzes = raw_data.get("quiz_attempts", [])
    if quizzes:
        total = len(quizzes)
        passed = sum(1 for q in quizzes if q.get("passed"))
        avg_score = sum(q.get("score", 0) for q in quizzes) / total
        quiz_summary = {"total_attempts": total, "pass_rate": round(passed / total, 2), "average_score": round(avg_score, 2)}
    else:
        quiz_summary = {"total_attempts": 0, "pass_rate": 0.0, "average_score": 0.0}

    # Persona
    profiles = raw_data.get("learner_persona_profiles", [])
    if profiles:
        persona = {"type": profiles[0].get("persona_type", "standard"), "profile_details": profiles[0].get("profile_data")}
    else:
        persona = {"type": "standard", "profile_details": {}}

    # Chat snippets
    msgs = raw_data.get("cp_rag_chat_messages", [])
    snippets = []
    for m in msgs:
        content = m.get("content", "")
        snippets.append({
            "session_id": m.get("session_id"),
            "role": m.get("role"),
            "message_snippet": content[:60] + "..." if len(content) > 60 else content,
        })

    return {
        "current_course_progress": course_progress,
        "active_topic": active_topic,
        "quiz_performance_summary": quiz_summary,
        "learner_persona": persona,
        "recent_ai_chat_summaries": snippets,
    }

