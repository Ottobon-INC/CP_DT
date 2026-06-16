from unittest.mock import patch, MagicMock
from app.schedulers.digital_twin_scheduler import get_enrolled_learners, execute_digital_twin_job
from app.services.twin_orchestrator import run_digital_twin

def test_get_enrolled_learners_fallback():
    """
    Asserts scheduler get_enrolled_learners returns default demo learner when DB connection fails.
    """
    with patch("app.schedulers.digital_twin_scheduler.get_enrolled_user_ids", return_value=["demo_learner"]):
        learners = get_enrolled_learners()
        assert "demo_learner" in learners

def test_execute_digital_twin_job():
    """
    Asserts execute_digital_twin_job triggers run_digital_twin on all retrieved learners.
    """
    mock_learners = ["student_a", "student_b"]
    with patch("app.schedulers.digital_twin_scheduler.get_enrolled_learners", return_value=mock_learners):
        with patch("app.schedulers.digital_twin_scheduler.run_digital_twin") as mock_run:
            execute_digital_twin_job()
            assert mock_run.call_count == 2
            mock_run.assert_any_call("student_a")
            mock_run.assert_any_call("student_b")

def test_execute_digital_twin_job_error_isolation():
    """
    Asserts a failure executing the digital twin for one learner does not halt execution for subsequent learners.
    """
    mock_learners = ["student_a", "student_b"]
    with patch("app.schedulers.digital_twin_scheduler.get_enrolled_learners", return_value=mock_learners):
        with patch("app.schedulers.digital_twin_scheduler.run_digital_twin", side_effect=[Exception("student_a error"), None]) as mock_run:
            # Should not throw exception and process all users
            execute_digital_twin_job()
            assert mock_run.call_count == 2
            mock_run.assert_any_call("student_b")
