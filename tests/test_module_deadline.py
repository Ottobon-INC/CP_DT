from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from app.services.module_deadline import sync_module_start_dates, check_module_deadlines

def test_sync_module_start_dates_new_progress():
    """
    Test that starting a module (progress > 0) creates a deadline state record.
    """
    mock_module_progress = [
        {
            "course_id": "course_123",
            "module_no": 1,
            "module_completed": False,
            "videos_completed": 1,  # Estimating >0% completion
            "quiz_passed": False,
            "assignments_complete": False,
        }
    ]
    
    with patch("app.services.module_deadline._get", return_value=mock_module_progress) as mock_get:
        with patch("app.services.module_deadline.get_module_deadline_state", return_value=None) as mock_get_state:
            with patch("app.services.module_deadline.upsert_module_deadline_state") as mock_upsert:
                sync_module_start_dates("learner_abc", "course_123")
                
                assert mock_upsert.called
                args = mock_upsert.call_args[0][0]
                assert args["learner_id"] == "learner_abc"
                assert args["course_id"] == "course_123"
                assert args["module_no"] == 1
                assert args["is_completed"] is False
                assert "started_at" in args
                assert "deadline_at" in args

def test_check_module_deadlines_sends_friendly_email():
    """
    Test that an overdue module triggers a friendly email check-in and updates email_sent_at.
    """
    past_date = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    mock_states = [
        {
            "id": "deadline_row_id",
            "learner_id": "learner_abc",
            "course_id": "course_123",
            "module_no": 1,
            "started_at": past_date,
            "deadline_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "is_completed": False,
            "email_sent_at": None,
        }
    ]
    
    with patch("app.services.module_deadline.sync_module_start_dates"):
        with patch("app.services.module_deadline.get_module_deadline_states", return_value=mock_states):
            with patch("app.services.email_service.send_engagement_email", return_value=True) as mock_send:
                with patch("app.services.module_deadline.upsert_module_deadline_state") as mock_upsert:
                    result = check_module_deadlines("learner_abc", "course_123")
                    
                    assert mock_send.called
                    mock_send.assert_called_once_with(
                        learner_id="learner_abc",
                        course_id="course_123",
                        email_type="module_deadline_friendly",
                        module_no=1
                    )
                    assert mock_upsert.called
                    assert result["emails_sent"] == [1]
                    assert mock_upsert.call_args[0][0]["email_sent_at"] is not None
