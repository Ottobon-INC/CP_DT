from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from app.services.inactivity import track_learner_inactivity

def test_track_learner_inactivity_new_activity():
    """
    Asserts track_learner_inactivity resets stage progression and timestamps when new activity is detected.
    """
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    record = {
        "learner_id": "learner_123",
        "last_activity_at": past_time.isoformat(),
        "inactivity_stage": 2,
        "first_message_sent_at": past_time.isoformat(),
        "second_message_sent_at": past_time.isoformat(),
        "is_active": False,
        "updated_at": past_time.isoformat()
    }
    
    # Student returns and creates a new activity 5 minutes ago
    new_activity_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    mock_load = MagicMock(return_value=record)
    mock_save = MagicMock()
    
    with patch("app.services.inactivity.load_inactivity_state", mock_load), \
         patch("app.services.inactivity.save_inactivity_state", mock_save):
        outcome = track_learner_inactivity(
            learner_id="learner_123",
            latest_activity_time=new_activity_time,
            derived_status="engaged"
        )
        
        # Inactivity resets back to stage 0
        assert outcome["inactivity_level"] == 0
        assert outcome["learner_state"] == "ACTIVE"
        mock_save.assert_called()


def test_track_learner_inactivity_transition_stage_1():
    """
    Asserts transitioning from stage 0 to stage 1 occurs when inactivity exceeds 10 minutes.
    """
    activity_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    record = {
        "learner_id": "learner_123",
        "last_activity_at": activity_time.isoformat(),
        "inactivity_stage": 0,
        "is_active": True,
        "updated_at": activity_time.isoformat()
    }
    
    mock_load = MagicMock(return_value=record)
    mock_save = MagicMock()
    
    with patch("app.services.inactivity.load_inactivity_state", mock_load), \
         patch("app.services.inactivity.save_inactivity_state", mock_save):
        outcome = track_learner_inactivity(
            learner_id="learner_123",
            latest_activity_time=activity_time,
            derived_status="engaged"
        )
        
        assert outcome["inactivity_level"] == 1
        assert outcome["learner_state"] == "INACTIVE_1"
        mock_save.assert_called()


def test_track_learner_inactivity_no_transition():
    """
    Asserts no new transition triggers if inactivity is within boundaries of current stage.
    """
    activity_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    record = {
        "learner_id": "learner_123",
        "last_activity_at": activity_time.isoformat(),
        "inactivity_stage": 1,
        "is_active": False,
        "first_message_sent_at": (activity_time + timedelta(minutes=10)).isoformat(),
        "updated_at": activity_time.isoformat()
    }
    
    mock_load = MagicMock(return_value=record)
    mock_save = MagicMock()
    
    with patch("app.services.inactivity.load_inactivity_state", mock_load), \
         patch("app.services.inactivity.save_inactivity_state", mock_save):
        outcome = track_learner_inactivity(
            learner_id="learner_123",
            latest_activity_time=activity_time,
            derived_status="engaged"
        )
        
        # Stage remains 1, learner_state is None to indicate no dispatch
        assert outcome["inactivity_level"] == 1
        assert outcome["learner_state"] is None
        mock_save.assert_not_called()


def test_track_learner_inactivity_transition_email_escalation():
    """
    Asserts transitioning from stage 3 to stage 4 triggers email escalation when inactivity exceeds 40 minutes.
    """
    activity_time = datetime.now(timezone.utc) - timedelta(minutes=45)
    record = {
        "learner_id": "learner_123",
        "last_activity_at": activity_time.isoformat(),
        "inactivity_stage": 3,
        "is_active": False,
        "updated_at": activity_time.isoformat()
    }
    
    mock_load = MagicMock(return_value=record)
    mock_save = MagicMock()
    
    with patch("app.services.inactivity.load_inactivity_state", mock_load), \
         patch("app.services.inactivity.save_inactivity_state", mock_save):
        outcome = track_learner_inactivity(
            learner_id="learner_123",
            latest_activity_time=activity_time,
            derived_status="engaged"
        )
        
        assert outcome["inactivity_level"] == 4
        assert outcome["should_email"] is True
        assert outcome["learner_state"] == "EMAIL_ESCALATED"
        mock_save.assert_called()
