from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from app.nodes import observe_learner, retrieve_learner_context, retrieve_tutor_context, determine_learner_state, generate_response, deliver_response
from app.graphs import TwinState

def test_observe_learner_no_id():
    """
    Asserts observe_learner returns a fallback dictionary when learner_id is None.
    """
    state: TwinState = {
        "learner_id": None,
        "tutor_id": "tutor_1",
        "conversation_id": "conv_1",
        "learner_context": None,
        "tutor_context": None,
        "latest_event": None,
        "latest_message": None,
        "inactivity_level": None,
        "response_mode": None,
        "generated_response": None,
        "should_email": None
    }
    
    update = observe_learner(state)
    assert "latest_event" in update
    assert update["latest_event"]["event_type"] == "unknown"
    assert update["latest_event"]["status"] == "engaged"

def test_observe_learner_no_event():
    """
    Asserts observe_learner returns a default dictionary when database queries find no event.
    """
    state: TwinState = {
        "learner_id": "learner_123",
        "tutor_id": "tutor_1",
        "conversation_id": "conv_1",
        "learner_context": None,
        "tutor_context": None,
        "latest_event": None,
        "latest_message": None,
        "inactivity_level": None,
        "response_mode": None,
        "generated_response": None,
        "should_email": None
    }
    
    with patch("app.nodes.observe_learner.get_latest_learner_event", return_value=None):
        update = observe_learner(state)
        assert "latest_event" in update
        assert update["latest_event"]["event_type"] == "none"
        assert update["latest_event"]["status"] == "engaged"

def test_observe_learner_with_event():
    """
    Asserts observe_learner updates state details using database telemetry.
    """
    state: TwinState = {
        "learner_id": "learner_123",
        "tutor_id": "tutor_1",
        "conversation_id": "conv_1",
        "learner_context": None,
        "tutor_context": None,
        "latest_event": None,
        "latest_message": None,
        "inactivity_level": None,
        "response_mode": None,
        "generated_response": None,
        "should_email": None
    }
    
    mock_event = {
        "event_type": "quiz_submitted",
        "derived_status": "content_friction",
        "created_at": "2026-06-15T10:00:00Z"
    }
    
    with patch("app.nodes.observe_learner.get_latest_learner_event", return_value=mock_event):
        update = observe_learner(state)
        assert "latest_event" in update
        assert update["latest_event"]["event_type"] == "quiz_submitted"
        assert update["latest_event"]["derived_status"] == "content_friction"
        assert update["latest_event"]["status"] == "content_friction"

def test_retrieve_learner_context_no_id():
    """
    Asserts retrieve_learner_context returns empty defaults when learner_id is None.
    """
    state: TwinState = {
        "learner_id": None,
        "tutor_id": "tutor_1",
        "conversation_id": "conv_1",
        "learner_context": None,
        "tutor_context": None,
        "latest_event": None,
        "latest_message": None,
        "inactivity_level": None,
        "response_mode": None,
        "generated_response": None,
        "should_email": None
    }
    
    update = retrieve_learner_context(state)
    assert "learner_context" in update
    assert update["learner_context"]["current_course_progress"]["average_completed_percentage"] == 0.0
    assert update["learner_context"]["active_topic"] is None

def test_retrieve_learner_context_with_data():
    """
    Asserts retrieve_learner_context aggregates and formats raw telemetry data correctly.
    """
    state: TwinState = {
        "learner_id": "learner_123",
        "tutor_id": "tutor_1",
        "conversation_id": "conv_1",
        "learner_context": None,
        "tutor_context": None,
        "latest_event": None,
        "latest_message": None,
        "inactivity_level": None,
        "response_mode": None,
        "generated_response": None,
        "should_email": None
    }
    
    mock_raw_data = {
        "topic_progress": [{"topic_id": "topic_a", "completed": False, "score": 80}],
        "module_progress": [{"module_id": "module_x", "completed_percentage": 50.0, "status": "in_progress"}],
        "quiz_attempts": [{"quiz_id": "quiz_1", "score": 90.0, "passed": True}],
        "cp_rag_chat_messages": [{"session_id": "sess_1", "role": "user", "content": "How do I code this?"}],
        "learner_persona_profiles": [{"persona_type": "visual_learner", "profile_data": {"pref": "diagrams"}}]
    }
    
    with patch("app.services.learner_context.fetch_learner_data", return_value=mock_raw_data):
        update = retrieve_learner_context(state)
        assert "learner_context" in update
        ctx = update["learner_context"]
        assert ctx["current_course_progress"]["average_completed_percentage"] == 50.0
        assert ctx["current_course_progress"]["modules_tracked"] == 1
        assert ctx["active_topic"] == "topic_a"
        assert ctx["quiz_performance_summary"]["average_score"] == 90.0
        assert ctx["learner_persona"]["type"] == "visual_learner"
        assert ctx["recent_ai_chat_summaries"][0]["message_snippet"] == "How do I code this?"

def test_retrieve_tutor_context_no_id():
    """
    Asserts retrieve_tutor_context returns empty defaults when tutor_id is None.
    """
    state: TwinState = {
        "learner_id": "learner_123",
        "tutor_id": None,
        "conversation_id": "conv_1",
        "learner_context": None,
        "tutor_context": None,
        "latest_event": None,
        "latest_message": None,
        "inactivity_level": None,
        "response_mode": None,
        "generated_response": None,
        "should_email": None
    }
    
    update = retrieve_tutor_context(state)
    assert "tutor_context" in update
    assert update["tutor_context"]["tutor_display_name"] == "AI Assistant"
    assert len(update["tutor_context"]["courses_taught"]) == 0

def test_retrieve_tutor_context_with_data():
    """
    Asserts retrieve_tutor_context aggregates and formats raw tutor records correctly.
    """
    state: TwinState = {
        "learner_id": "learner_123",
        "tutor_id": "tutor_456",
        "conversation_id": "conv_1",
        "learner_context": None,
        "tutor_context": None,
        "latest_event": None,
        "latest_message": None,
        "inactivity_level": None,
        "response_mode": None,
        "generated_response": None,
        "should_email": None
    }
    
    mock_raw_data = {
        "tutor_profile": {"display_name": "Dr. Sarah", "bio": "Senior Computer Science Instructor"},
        "courses_taught": [{"course_id": "cs101", "title": "Intro to CS"}],
        "prompt_suggestions": [{"topic_id": "recursion", "suggestion": "Explain call stacks", "guidance": "Draw diagrams"}],
        "submissions_info": [{"submission_id": "sub_1", "status": "pending", "grade": None}],
        "topics_data": [{"topic_id": "recursion", "title": "Recursion", "content": "Recursion is a process..."}]
    }
    
    with patch("app.services.tutor_context.fetch_tutor_data", return_value=mock_raw_data):
        update = retrieve_tutor_context(state)
        assert "tutor_context" in update
        ctx = update["tutor_context"]
        assert ctx["tutor_display_name"] == "Dr. Sarah"
        assert ctx["tutor_bio"] == "Senior Computer Science Instructor"
        assert "Intro to CS" in ctx["courses_taught"]
        assert ctx["tutor_prompt_guidance"][0]["topic_id"] == "recursion"
        assert ctx["tutor_prompt_guidance"][0]["guidance"] == "Draw diagrams"
        assert ctx["relevant_course_knowledge"]["recent_submissions_summary"]["total_reviewed"] == 1
        assert ctx["relevant_course_knowledge"]["recent_submissions_summary"]["pending_reviews"] == 1
        assert ctx["relevant_course_knowledge"]["topics"][0]["title"] == "Recursion"

def test_determine_learner_state_active():
    """
    Asserts determine_learner_state sets inactivity_level 0 and ACTIVE status under 10 minutes.
    """
    state: TwinState = {
        "learner_id": "learner_123",
        "tutor_id": "tutor_1",
        "conversation_id": "conv_1",
        "learner_context": None,
        "tutor_context": None,
        "latest_event": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "derived_status": "engaged"
        },
        "latest_message": None,
        "inactivity_level": None,
        "response_mode": None,
        "generated_response": None,
        "should_email": None
    }
    
    mock_outcome = {"inactivity_level": 0, "should_email": False, "learner_state": "ACTIVE"}
    with patch("app.nodes.determine_learner_state.track_learner_inactivity", return_value=mock_outcome):
        update = determine_learner_state(state)
        assert update["inactivity_level"] == 0
        assert update["should_email"] is False
        assert update["latest_event"]["learner_state"] == "ACTIVE"


def test_determine_learner_state_attention_drift():
    """
    Asserts determine_learner_state sets ATTENTION_DRIFT based on derived_status when active.
    """
    state: TwinState = {
        "learner_id": "learner_123",
        "tutor_id": "tutor_1",
        "conversation_id": "conv_1",
        "learner_context": None,
        "tutor_context": None,
        "latest_event": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "derived_status": "attention_drift"
        },
        "latest_message": None,
        "inactivity_level": None,
        "response_mode": None,
        "generated_response": None,
        "should_email": None
    }
    
    mock_outcome = {"inactivity_level": 0, "should_email": False, "learner_state": "ATTENTION_DRIFT"}
    with patch("app.nodes.determine_learner_state.track_learner_inactivity", return_value=mock_outcome):
        update = determine_learner_state(state)
        assert update["inactivity_level"] == 0
        assert update["should_email"] is False
        assert update["latest_event"]["learner_state"] == "ATTENTION_DRIFT"


def test_determine_learner_state_inactive_1():
    """
    Asserts determine_learner_state triggers INACTIVE_1 status and level 1 when inactive > 10m.
    """
    event_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    state: TwinState = {
        "learner_id": "learner_123",
        "tutor_id": "tutor_1",
        "conversation_id": "conv_1",
        "learner_context": None,
        "tutor_context": None,
        "latest_event": {
            "created_at": event_time.isoformat(),
            "derived_status": "engaged"
        },
        "latest_message": None,
        "inactivity_level": None,
        "response_mode": None,
        "generated_response": None,
        "should_email": None
    }
    
    mock_outcome = {"inactivity_level": 1, "should_email": False, "learner_state": "INACTIVE_1"}
    with patch("app.nodes.determine_learner_state.track_learner_inactivity", return_value=mock_outcome):
        update = determine_learner_state(state)
        assert update["inactivity_level"] == 1
        assert update["should_email"] is False
        assert update["latest_event"]["learner_state"] == "INACTIVE_1"


def test_determine_learner_state_email_escalated():
    """
    Asserts determine_learner_state activates should_email and level 4 when inactive > 40m.
    """
    event_time = datetime.now(timezone.utc) - timedelta(minutes=45)
    state: TwinState = {
        "learner_id": "learner_123",
        "tutor_id": "tutor_1",
        "conversation_id": "conv_1",
        "learner_context": None,
        "tutor_context": None,
        "latest_event": {
            "created_at": event_time.isoformat(),
            "derived_status": "engaged"
        },
        "latest_message": None,
        "inactivity_level": None,
        "response_mode": None,
        "generated_response": None,
        "should_email": None
    }
    
    mock_outcome = {"inactivity_level": 4, "should_email": True, "learner_state": "EMAIL_ESCALATED"}
    with patch("app.nodes.determine_learner_state.track_learner_inactivity", return_value=mock_outcome):
        update = determine_learner_state(state)
        assert update["inactivity_level"] == 4
        assert update["should_email"] is True
        assert update["latest_event"]["learner_state"] == "EMAIL_ESCALATED"


def test_generate_response():
    """
    Asserts generate_response returns a response string from the initialized chat model.
    """
    state: TwinState = {
        "learner_id": "learner_123",
        "tutor_id": "tutor_456",
        "conversation_id": "conv_1",
        "learner_context": {
            "current_course_progress": {"average_completed_percentage": 60.0},
            "active_topic": "recursion",
            "quiz_performance_summary": {},
            "learner_persona": {"type": "visual"},
            "recent_ai_chat_summaries": []
        },
        "tutor_context": {
            "tutor_display_name": "Dr. Sarah",
            "tutor_bio": "CS professor",
            "courses_taught": ["Intro CS"],
            "tutor_prompt_guidance": [],
            "relevant_course_knowledge": {}
        },
        "latest_event": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "derived_status": "engaged",
            "learner_state": "ACTIVE"
        },
        "latest_message": "Can you explain recursion?",
        "inactivity_level": 0,
        "response_mode": None,
        "generated_response": None,
        "should_email": False
    }
    
    update = generate_response(state)
    assert "generated_response" in update
    assert isinstance(update["generated_response"], str)
    assert len(update["generated_response"]) > 0

def test_deliver_response_empty():
    """
    Asserts deliver_response returns an empty dict when there is no response to send.
    """
    state: TwinState = {
        "learner_id": "learner_123",
        "tutor_id": "tutor_456",
        "conversation_id": "conv_1",
        "learner_context": {},
        "tutor_context": {},
        "latest_event": {},
        "latest_message": None,
        "inactivity_level": 0,
        "response_mode": None,
        "generated_response": None,
        "should_email": False
    }
    
    update = deliver_response(state)
    assert update == {}

def test_deliver_response_success():
    """
    Asserts deliver_response clears generated_response upon successful messaging delivery.
    """
    state: TwinState = {
        "learner_id": "learner_123",
        "tutor_id": "tutor_456",
        "conversation_id": "conv_1",
        "learner_context": {},
        "tutor_context": {},
        "latest_event": {},
        "latest_message": None,
        "inactivity_level": 0,
        "response_mode": None,
        "generated_response": "Hello, student!",
        "should_email": False
    }
    
    with patch("app.nodes.deliver_response.send_message_to_conversation", return_value=True) as mock_send:
        update = deliver_response(state)
        mock_send.assert_called_once_with(
            conversation_id="conv_1",
            sender_id="tutor_456",
            recipient_id="learner_123",
            content="Hello, student!"
        )
        assert "generated_response" in update
        assert update["generated_response"] is None





