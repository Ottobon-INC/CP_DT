from app.graphs import TwinState

def test_twin_state_fields():
    """
    Test that the TwinState TypedDict contains all expected keys.
    """
    annotations = TwinState.__annotations__
    expected_keys = [
        "learner_id",
        "tutor_id",
        "conversation_id",
        "learner_context",
        "tutor_context",
        "latest_event",
        "latest_message",
        "inactivity_level",
        "response_mode",
        "generated_response",
        "should_email"
    ]
    for key in expected_keys:
        assert key in annotations


def test_settings_database_url_override():
    """
    Asserts custom DATABASE_URL values override defaults and adapt protocols safely.
    """
    from app.config.settings import Settings
    
    # Test conversion when 'postgres://' is provided
    s = Settings(DATABASE_URL="postgres://user:pass@host:5432/db")
    assert s.database_url == "postgresql://user:pass@host:5432/db"
    assert s.database_url_async == "postgresql+asyncpg://user:pass@host:5432/db"

    # Test conversion when 'postgresql://' is provided
    s2 = Settings(DATABASE_URL="postgresql://user:pass@host:5432/db")
    assert s2.database_url == "postgresql://user:pass@host:5432/db"
    assert s2.database_url_async == "postgresql+asyncpg://user:pass@host:5432/db"

