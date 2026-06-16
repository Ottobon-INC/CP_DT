from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from app.graphs.state import TwinState
from app.prompts.response_generator import SYSTEM_PROMPT_TEMPLATE
from app.utils.llm import get_chat_model

def generate_response(state: TwinState) -> Dict[str, Any]:
    """
    GenerateResponse node: Combines learner and tutor context, formats the prompt
    system guidelines based on the learner's state, invokes the LLM, and populates
    TwinState.generated_response.
    
    Returns a dictionary of state updates.
    """
    learner_context = state.get("learner_context") or {}
    tutor_context = state.get("tutor_context") or {}
    latest_event = state.get("latest_event") or {}
    
    learner_state = latest_event.get("learner_state", "ACTIVE")
    latest_message = state.get("latest_message") or "Hello!"

    # 1. Format prompt strings for templates
    tutor_name = tutor_context.get("tutor_display_name", "AI Assistant")
    tutor_bio = tutor_context.get("tutor_bio", "Default tutoring assistant profile.")
    courses_taught = ", ".join(tutor_context.get("courses_taught") or ["general tutoring"])
    
    course_progress = str(learner_context.get("current_course_progress", {}))
    active_topic = str(learner_context.get("active_topic") or "None")
    quiz_performance = str(learner_context.get("quiz_performance_summary", {}))
    learner_persona = str(learner_context.get("learner_persona", {}))
    
    chat_history_list = learner_context.get("recent_ai_chat_summaries") or []
    chat_history = "\n".join([f"- {m.get('role')}: {m.get('message_snippet')}" for m in chat_history_list]) or "No recent chat history."
    
    guidance_list = tutor_context.get("tutor_prompt_guidance") or []
    tutor_guidance = "\n".join([f"- {g.get('topic_id')}: {g.get('guidance')}" for g in guidance_list]) or "No specific guidance suggestions."
    
    knowledge_topics = (tutor_context.get("relevant_course_knowledge") or {}).get("topics") or []
    course_knowledge = "\n".join([f"- Topic {t.get('topic_id')} ({t.get('title')}): {t.get('snippet')}" for t in knowledge_topics]) or "No relevant knowledge items."

    # 2. Format system prompt
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        tutor_name=tutor_name,
        tutor_bio=tutor_bio,
        courses_taught=courses_taught,
        course_progress=course_progress,
        active_topic=active_topic,
        quiz_performance=quiz_performance,
        learner_persona=learner_persona,
        chat_history=chat_history,
        learner_state=learner_state,
        tutor_guidance=tutor_guidance,
        course_knowledge=course_knowledge
    )

    # 3. Call Chat Model
    try:
        model = get_chat_model()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Latest message or event trigger. Student message: '{latest_message}'")
        ]
        response = model.invoke(messages)
        generated_response = response.content
    except Exception as e:
        # Fallback response on failure
        generated_response = "Hello! As your tutor, I'm here to support you. Let's work through the topic together!"

    return {"generated_response": generated_response}
