import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.services.supabase_client import load_inactivity_state, save_inactivity_state

logger = logging.getLogger(__name__)


def track_learner_inactivity(
    learner_id: str,
    latest_activity_time: Optional[datetime],
    derived_status: str
) -> Dict[str, Any]:
    """
    Evaluates learner inactivity against persistence state and triggers
    stage transitions or resets accordingly.
    Uses Supabase REST API for read/write operations on twin_inactivity_state.
    """
    try:
        current_time = datetime.now(timezone.utc)

        # Load or create persistence state
        record = load_inactivity_state(learner_id)

        if not record:
            # First time tracking this learner — create initial state
            new_record = {
                "learner_id": learner_id,
                "last_activity_at": (latest_activity_time or current_time).isoformat(),
                "inactivity_stage": 0,
                "is_active": True,
                "updated_at": current_time.isoformat(),
                "first_message_sent_at": None,
                "second_message_sent_at": None,
                "third_message_sent_at": None,
                "email_sent_at": None,
            }
            save_inactivity_state(new_record)
            record = new_record

        # Check for new activity
        has_new_activity = False
        if latest_activity_time:
            if latest_activity_time.tzinfo is None:
                latest_activity_time = latest_activity_time.replace(tzinfo=timezone.utc)

            saved_activity_str = record.get("last_activity_at")
            if saved_activity_str:
                if isinstance(saved_activity_str, str):
                    # Parse ISO timestamp, handling timezone
                    saved_activity_str = saved_activity_str.replace("+00:00", "+00:00")
                    try:
                        saved_activity = datetime.fromisoformat(saved_activity_str)
                    except ValueError:
                        saved_activity = current_time
                else:
                    saved_activity = saved_activity_str

                if saved_activity.tzinfo is None:
                    saved_activity = saved_activity.replace(tzinfo=timezone.utc)

                if latest_activity_time > saved_activity:
                    has_new_activity = True

        if has_new_activity:
            logger.info(f"New activity detected for learner {learner_id}. Resetting inactivity stages.")
            update = {
                "learner_id": learner_id,
                "inactivity_stage": 0,
                "last_activity_at": latest_activity_time.isoformat(),
                "first_message_sent_at": None,
                "second_message_sent_at": None,
                "third_message_sent_at": None,
                "email_sent_at": None,
                "is_active": True,
                "updated_at": current_time.isoformat(),
            }
            save_inactivity_state(update)

            if derived_status == "attention_drift":
                learner_state = "ATTENTION_DRIFT"
            elif derived_status == "content_friction":
                learner_state = "CONTENT_FRICTION"
            else:
                learner_state = "ACTIVE"

            return {"inactivity_level": 0, "should_email": False, "learner_state": learner_state}

        # No new activity — calculate duration since last activity
        last_activity_str = record.get("last_activity_at")
        if isinstance(last_activity_str, str):
            try:
                last_activity = datetime.fromisoformat(last_activity_str)
            except ValueError:
                last_activity = current_time
        else:
            last_activity = last_activity_str or current_time

        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)

        duration_minutes = (current_time - last_activity).total_seconds() / 60.0
        current_stage = record.get("inactivity_stage", 0)

        logger.info(f"Learner {learner_id} inactive for {duration_minutes:.2f} minutes (Stage {current_stage}).")

        # Evaluate transition rules
        inactivity_level = current_stage
        should_email = False
        learner_state = None

        update_needed = False
        update_data = {
            "learner_id": learner_id,
            "updated_at": current_time.isoformat(),
        }

        if duration_minutes >= 40.0 and current_stage == 3:
            update_data.update({"inactivity_stage": 4, "email_sent_at": current_time.isoformat(), "is_active": False})
            inactivity_level = 4
            should_email = True
            learner_state = "EMAIL_ESCALATED"
            update_needed = True
            logger.info(f"Learner {learner_id} reached Stage 4: EMAIL_ESCALATED triggered.")
            logger.info(f"[TRIGGER SKL_EMAIL_NOTIFICATION] Sending escalation email to student {learner_id}...")
            print(f"[TRIGGER SKL_EMAIL_NOTIFICATION] Outgoing escalation email sent to student {learner_id}.")

        elif duration_minutes >= 30.0 and current_stage == 2:
            update_data.update({"inactivity_stage": 3, "third_message_sent_at": current_time.isoformat(), "is_active": False})
            inactivity_level = 3
            learner_state = "INACTIVE_3"
            update_needed = True
            logger.info(f"Learner {learner_id} reached Stage 3: INACTIVE_3 triggered.")

        elif duration_minutes >= 20.0 and current_stage == 1:
            update_data.update({"inactivity_stage": 2, "second_message_sent_at": current_time.isoformat(), "is_active": False})
            inactivity_level = 2
            learner_state = "INACTIVE_2"
            update_needed = True
            logger.info(f"Learner {learner_id} reached Stage 2: INACTIVE_2 triggered.")

        elif duration_minutes >= 10.0 and current_stage == 0:
            update_data.update({"inactivity_stage": 1, "first_message_sent_at": current_time.isoformat(), "is_active": False})
            inactivity_level = 1
            learner_state = "INACTIVE_1"
            update_needed = True
            logger.info(f"Learner {learner_id} reached Stage 1: INACTIVE_1 triggered.")

        if update_needed:
            save_inactivity_state(update_data)

        return {
            "inactivity_level": inactivity_level,
            "should_email": should_email,
            "learner_state": learner_state
        }

    except Exception as e:
        logger.error(f"Error in track_learner_inactivity workflow: {e}")
        return {"inactivity_level": 0, "should_email": False, "learner_state": "ACTIVE"}
