from typing import Dict, Any
from app.graphs.state import TwinState
from app.services.messaging import send_message_to_conversation
from app.services.email_service import send_engagement_email

def deliver_response(state: TwinState) -> Dict[str, Any]:
    """
    DeliverResponse node: Reads conversation_id, tutor_id, learner_id, and 
    generated_response from state, triggers the messaging service to record the 
    message as tutor-originated, and clears or retains the generated_response parameter.
    
    If should_email is True, also dispatches an escalation email to the learner.
    
    Returns a dictionary of state updates.
    """
    conversation_id = state.get("conversation_id")
    tutor_id = state.get("tutor_id")
    learner_id = state.get("learner_id")
    course_id = state.get("course_id")
    generated_response = state.get("generated_response")
    should_email = state.get("should_email", False)
    
    if not generated_response:
        # Nothing to deliver
        return {}

    # Deliver message to learner's conversation
    success = send_message_to_conversation(
        conversation_id=conversation_id or "default_conv",
        sender_id=tutor_id or "default_tutor",
        recipient_id=learner_id or "default_learner",
        content=generated_response
    )
    
    # If email escalation is triggered, send the email
    if should_email and learner_id:
        send_engagement_email(
            learner_id=learner_id,
            course_id=course_id,
            email_type="inactivity_escalation",
        )
    
    # Standard LangGraph state update pattern: if successfully delivered, 
    # clear the generated_response so it isn't processed twice.
    return {"generated_response": None if success else generated_response}

