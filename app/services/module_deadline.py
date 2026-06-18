import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from app.services.supabase_client import (
    _get,
    _calc_module_pct,
    upsert_module_deadline_state,
    get_module_deadline_states,
    get_module_deadline_state,
)

logger = logging.getLogger(__name__)


def sync_module_start_dates(learner_id: str, course_id: str) -> None:
    """
    Syncs the learner's module_progress with the module_deadline_state table.
    If a module has >0% progress, we begin tracking its deadline (started_at).
    """
    try:
        mp_rows = _get("module_progress", {
            "select": "*",
            "user_id": f"eq.{learner_id}",
            "course_id": f"eq.{course_id}"
        })
        
        for r in mp_rows:
            module_no = r.get("module_no")
            if module_no is None:
                continue
                
            is_completed = bool(r.get("module_completed"))
            pct = _calc_module_pct(r)
            
            # Start tracking if progress is greater than 0%
            if pct > 0:
                existing = get_module_deadline_state(learner_id, course_id, module_no)
                now = datetime.now(timezone.utc)
                
                if not existing:
                    deadline_at = now + timedelta(days=7)
                    upsert_module_deadline_state({
                        "learner_id": learner_id,
                        "course_id": course_id,
                        "module_no": module_no,
                        "started_at": now.isoformat(),
                        "deadline_at": deadline_at.isoformat(),
                        "is_completed": is_completed,
                        "completed_at": now.isoformat() if is_completed else None,
                        "updated_at": now.isoformat(),
                    })
                    logger.info(f"Started tracking module {module_no} for learner {learner_id}")
                else:
                    # Update status to completed if completed now
                    if is_completed and not existing.get("is_completed"):
                        existing["is_completed"] = True
                        existing["completed_at"] = now.isoformat()
                        existing["updated_at"] = now.isoformat()
                        upsert_module_deadline_state(existing)
                        logger.info(f"Marked module {module_no} completed for learner {learner_id}")
                        
    except Exception as e:
        logger.error(f"Error syncing module start dates for learner {learner_id}: {e}")


def check_module_deadlines(learner_id: str, course_id: str) -> Dict[str, Any]:
    """
    Evaluates whether a learner has any overdue modules (>7 days from start) and
    sends a single friendly re-engagement check-in email if overdue and unsent.
    """
    # Sync first to ensure we have recent start times and completion states
    sync_module_start_dates(learner_id, course_id)
    
    emails_sent = []
    try:
        states = get_module_deadline_states(learner_id, course_id)
        now = datetime.now(timezone.utc)
        
        for state in states:
            if state.get("is_completed"):
                continue
                
            deadline_str = state.get("deadline_at")
            if not deadline_str:
                continue
                
            try:
                deadline = datetime.fromisoformat(str(deadline_str).replace("Z", "+00:00"))
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
            except Exception:
                continue
                
            # If the current time has passed the deadline and we haven't sent the email
            if now > deadline and not state.get("email_sent_at"):
                from app.services.email_service import send_engagement_email
                
                module_no = state.get("module_no")
                logger.info(f"Module {module_no} is overdue for learner {learner_id}. Sending friendly email.")
                
                success = send_engagement_email(
                    learner_id=learner_id,
                    course_id=course_id,
                    email_type="module_deadline_friendly",
                    module_no=module_no
                )
                
                if success:
                    state["email_sent_at"] = now.isoformat()
                    state["updated_at"] = now.isoformat()
                    upsert_module_deadline_state(state)
                    emails_sent.append(module_no)
                    
    except Exception as e:
        logger.error(f"Error checking module deadlines for learner {learner_id}: {e}")
        
    return {
        "learner_id": learner_id,
        "course_id": course_id,
        "emails_sent": emails_sent
    }
