"""Validation tests for EmailEscalationHandler integration contract."""
from unittest.mock import MagicMock
from app.services.email_escalation_handler import (
    EmailEscalationHandler,
    EmailEscalationState,
    LearnerIdentity,
    LearnerProgressContext,
    TRIGGER_LEVEL,
)
from app.services.email_service import EmailResult

IDENTITY = LearnerIdentity(
    student_name="Jane Doe",
    student_email="jane@example.com",
    course_name="AI Foundations",
)
CONTEXT = LearnerProgressContext(
    current_course_progress={
        "modules_tracked": 10,
        "average_completed_percentage": 30.0,
        "statuses": ["completed", "completed", "completed", "in_progress",
                     "locked", "locked", "locked", "locked", "locked", "locked"],
    },
    active_topic="topic_4",
    quiz_performance_summary={"total_attempts": 3, "pass_rate": 0.67, "average_score": 72.0},
    learner_persona={"type": "visual_learner", "profile_details": {}},
    recent_ai_chat_summaries=[],
    last_active_date="2026-06-10",
)

# Test 1: Non-trigger level skips workflow entirely
mock_wf = MagicMock()
handler = EmailEscalationHandler(workflow=mock_wf)
result = handler.handle(EmailEscalationState(
    learner_id="learner-001", inactivity_level="ACTIVE",
    learner_context=CONTEXT, learner_identity=IDENTITY,
))
assert result["triggered"] is False, f"Test 1 fail: {result}"
assert result["delivery"] is None,   f"Test 1 fail: {result}"
assert result["learner_id"] == "learner-001"
mock_wf.execute.assert_not_called()
print("Test 1 PASSED: ACTIVE level skipped, workflow not called")

# Test 2: EMAIL_ESCALATED triggers workflow and returns delivery result
mock_wf2 = MagicMock()
mock_wf2.execute.return_value = EmailResult(success=True, status="sent", recipient="jane@example.com")
handler2 = EmailEscalationHandler(workflow=mock_wf2)
result2 = handler2.handle(EmailEscalationState(
    learner_id="learner-001", inactivity_level="EMAIL_ESCALATED",
    learner_context=CONTEXT, learner_identity=IDENTITY,
))
assert result2["triggered"] is True,                            f"Test 2 fail: {result2}"
assert result2["delivery"]["success"] is True,                 f"Test 2 fail: {result2}"
assert result2["delivery"]["status"] == "sent",                f"Test 2 fail: {result2}"
assert result2["delivery"]["recipient"] == "jane@example.com", f"Test 2 fail: {result2}"
mock_wf2.execute.assert_called_once()
print("Test 2 PASSED: EMAIL_ESCALATED triggered workflow correctly")
print("  delivery:", dict(result2["delivery"]))

# Test 3: Field mapping — correct InactivityEmailInput constructed
args = mock_wf2.execute.call_args[0][0]
assert args["student_name"]      == "Jane Doe",         f"Test 3 fail name: {args}"
assert args["student_email"]     == "jane@example.com", f"Test 3 fail email: {args}"
assert args["course_name"]       == "AI Foundations",   f"Test 3 fail course: {args}"
assert args["modules_completed"] == 3,                  f"Test 3 fail modules: {args}"
assert args["total_modules"]     == 10,                 f"Test 3 fail total: {args}"
assert args["last_active_date"]  == "2026-06-10",       f"Test 3 fail date: {args}"
print("Test 3 PASSED: Field mapping correct")
print("  InactivityEmailInput:", dict(args))

# Test 4: All other levels are skipped
mock_wf3 = MagicMock()
handler3 = EmailEscalationHandler(workflow=mock_wf3)
for level in ["INACTIVE_1", "INACTIVE_2", "INACTIVE_3", "ATTENTION_DRIFT", "CONTENT_FRICTION"]:
    r = handler3.handle(EmailEscalationState(
        learner_id="x", inactivity_level=level,
        learner_context=CONTEXT, learner_identity=IDENTITY,
    ))
    assert r["triggered"] is False, f"Test 4 fail — {level} should not trigger: {r}"
mock_wf3.execute.assert_not_called()
print("Test 4 PASSED: Only EMAIL_ESCALATED triggers (5 other levels all skipped)")

print()
print("All contract tests passed.")
print(f'TRIGGER_LEVEL confirmed = "{TRIGGER_LEVEL}"')
