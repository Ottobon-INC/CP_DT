from typing import Dict, Any
from app.graphs.state import TwinState
from app.services.messaging import send_message_to_conversation

def deliver_response(state: TwinState) -> Dict[str, Any]:
    """
    DeliverResponse node: Reads conversation_id, tutor_id, learner_id, and 
    generated_response from state, triggers the messaging service to record the 
    message as tutor-originated, and clears or retains the generated_response parameter.
    
    Returns a dictionary of state updates.
    """
    conversation_id = state.get("conversation_id")
    tutor_id = state.get("tutor_id")
    learner_id = state.get("learner_id")
    generated_response = state.get("generated_response")
    
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
    
    # Standard LangGraph state update pattern: if successfully delivered, 
    # clear the generated_response so it isn't processed twice.
    return {"generated_response": None if success else generated_response}
