import logging
import time
from typing import Dict, Any, Optional
from app.graphs.state import TwinState
from app.nodes import (
    observe_learner,
    retrieve_learner_context,
    retrieve_tutor_context,
    determine_learner_state,
    generate_response,
    deliver_response
)

logger = logging.getLogger(__name__)

def run_digital_twin(learner_id: str, course_id: Optional[str] = None) -> TwinState:
    """
    Executes the Digital Twin pipeline nodes sequentially for a given learner.
    Returns the resulting TwinState dict.
    """
    start_time = time.time()
    logger.info(f"Starting Digital Twin execution loop for learner: {learner_id}, course: {course_id}")
    
    from app.services.supabase_client import resolve_tutor_id_for_learner, resolve_conversation_id
    
    resolved_tutor_id = resolve_tutor_id_for_learner(learner_id, course_id=course_id)
    resolved_conv_id = resolve_conversation_id(learner_id, resolved_tutor_id)

    # 1. State initialization
    state: TwinState = {
        "learner_id": learner_id,
        "course_id": course_id,
        "tutor_id": resolved_tutor_id,
        "conversation_id": resolved_conv_id,
        "learner_context": None,
        "tutor_context": None,
        "latest_event": None,
        "latest_message": None,
        "inactivity_level": 0,
        "response_mode": None,
        "generated_response": None,
        "should_email": False
    }
    
    try:
        # 2. Telemetry checking
        updates = observe_learner(state)
        state.update(updates)
        
        # 3. Context aggregations
        updates = retrieve_learner_context(state)
        state.update(updates)
        
        updates = retrieve_tutor_context(state)
        state.update(updates)
        
        # 4. Inactivity state transitions
        updates = determine_learner_state(state)
        state.update(updates)
        
        # 5. Check if re-engagement message generation is triggered
        learner_state = (state.get("latest_event") or {}).get("learner_state")
        
        if learner_state in ["INACTIVE_1", "INACTIVE_2", "INACTIVE_3", "EMAIL_ESCALATED", "ATTENTION_DRIFT", "CONTENT_FRICTION"]:
            logger.info(f"Learner {learner_id} is in trigger state '{learner_state}'. Generating response.")
            
            # Response generation
            updates = generate_response(state)
            state.update(updates)
            
            # Message delivery
            updates = deliver_response(state)
            state.update(updates)
        else:
            logger.info(f"Learner {learner_id} is active/engaged (Stage {state.get('inactivity_level')}). No response dispatch triggered.")
            
        elapsed_time = time.time() - start_time
        logger.info(f"Completed Digital Twin loop for learner {learner_id} in {elapsed_time:.2f} seconds.")
        return state
        
    except Exception as e:
        logger.error(f"Error in Digital Twin execution loop for learner {learner_id}: {e}", exc_info=True)
        raise e

