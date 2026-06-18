from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """
    Test that the health check endpoint returns 200 and {"status": "healthy"}.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_health_db_check_connected():
    """
    Test that the database health check returns 200 and {"database": "connected"} when healthy.
    """
    with patch("app.api.router.check_db_connectivity", return_value=True):
        response = client.get("/health/db")
        assert response.status_code == 200
        assert response.json() == {"database": "connected"}

def test_health_db_check_disconnected():
    """
    Test that the database health check returns 503 when the database is unreachable.
    """
    with patch("app.api.router.check_db_connectivity", return_value=False):
        response = client.get("/health/db")
        assert response.status_code == 503
        assert "Database connection failure" in response.json()["detail"]

def test_trigger_digital_twin_endpoint_success():
    """
    Test that the manual trigger endpoint successfully runs the orchestrator pipeline.
    """
    mock_state = {"learner_id": "test_learner", "status": "success"}
    with patch("app.api.router.run_digital_twin", return_value=mock_state) as mock_run:
        response = client.post("/twin/run/test_learner")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "executed successfully" in data["message"]
        assert data["state"] == mock_state
        mock_run.assert_called_once_with("test_learner", course_id=None)

def test_trigger_digital_twin_endpoint_failure():
    """
    Test that the manual trigger endpoint returns 500 when the pipeline execution fails.
    """
    with patch("app.api.router.run_digital_twin", side_effect=ValueError("Pipeline error")):
        response = client.post("/twin/run/test_learner")
        assert response.status_code == 500
        assert "Pipeline error" in response.json()["detail"]
