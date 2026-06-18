import logging
from langchain_core.language_models.chat_models import BaseChatModel
from app.config.settings import settings

logger = logging.getLogger(__name__)

def get_chat_model() -> BaseChatModel:
    """
    Initializes and returns the appropriate BaseChatModel based on configured API keys.
    If no key is configured, returns a FakeListChatModel for local testing/fallback.
    """
    if settings.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-4o")
        except Exception as e:
            logger.error(f"Failed to initialize ChatOpenAI: {e}")
            
    if settings.GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(api_key=settings.GEMINI_API_KEY, model="gemini-1.5-flash")
        except Exception as e:
            logger.error(f"Failed to initialize ChatGoogleGenerativeAI: {e}")

    try:
        try:
            from langchain_core.language_models.fake_chat_models import FakeListChatModel
        except ImportError:
            try:
                from langchain_core.language_models import FakeListChatModel
            except ImportError:
                try:
                    from langchain_core.language_models.fake import FakeListChatModel
                except ImportError:
                    from langchain_community.chat_models.fake import FakeListChatModel
        
        return FakeListChatModel(responses=[
            "Hello! I noticed you are working on recursion. Remember, a recursive function always needs a base case to stop executing. Keep up the great work!"
        ])
    except Exception as e:
        logger.error(f"Failed to initialize FakeListChatModel: {e}")
        raise RuntimeError("No chat model could be initialized.")
