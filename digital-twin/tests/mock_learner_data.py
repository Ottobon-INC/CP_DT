"""
MockLearnerData: Provides a static learner inactivity payload for testing
the InactivityEmailWorkflow before real LangGraph learner context is wired.

Usage:
    from tests.mock_learner_data import MockLearnerData

    provider = MockLearnerData()
    payload  = provider.get_mock_learner()

    # Pass directly to InactivityEmailWorkflow
    from app.services.inactivity_email_workflow import InactivityEmailWorkflow
    result = InactivityEmailWorkflow().execute(payload)

Configuration:
    Set TEST_RECIPIENT_EMAIL in your .env file (or as an environment variable)
    before using this provider. A RuntimeError is raised immediately if the
    variable is absent or empty, so misconfiguration is caught early.

Lifecycle:
    This provider is a temporary stand-in until the Digital Twin LangGraph
    pipeline exposes a real learner context object. Once that is available,
    replace calls to get_mock_learner() with the live context adapter.
"""

import logging
import os
from typing import Final

from app.services.inactivity_email_workflow import InactivityEmailInput

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────

_ENV_VAR: Final[str] = "TEST_RECIPIENT_EMAIL"

_DEFAULT_STUDENT_NAME: Final[str]   = "Test Learner"
_DEFAULT_COURSE_NAME: Final[str]    = "AI Foundations"
_DEFAULT_MODULES_COMPLETED: Final[int] = 3
_DEFAULT_TOTAL_MODULES: Final[int]  = 10
_DEFAULT_LAST_ACTIVE_DATE: Final[str] = "2026-06-15"


# ─── Provider ─────────────────────────────────────────────────────────

class MockLearnerData:
    """
    Returns a fixed inactivity payload for end-to-end workflow testing.

    The recipient email is sourced from the TEST_RECIPIENT_EMAIL environment
    variable so real delivery can be verified against a controlled inbox
    without hardcoding any address in source code.

    All other fields are static defaults suitable for smoke-testing the
    full EmailTemplateBuilder → EmailService pipeline.
    """

    def __init__(self) -> None:
        self._recipient_email: str = self._resolve_recipient_email()
        logger.debug(
            "MockLearnerData: Initialised — recipient='%s'.", self._recipient_email
        )

    # ── Public API ───────────────────────────────────────────────────

    def get_mock_learner(self) -> InactivityEmailInput:
        """
        Returns a static InactivityEmailInput payload ready to pass to
        InactivityEmailWorkflow.execute().

        Returns:
            InactivityEmailInput dict with all required fields populated.

        Example output::

            {
                "student_name":      "Test Learner",
                "student_email":     "you@example.com",   # from TEST_RECIPIENT_EMAIL
                "course_name":       "AI Foundations",
                "modules_completed": 3,
                "total_modules":     10,
                "last_active_date":  "2026-06-15",
            }
        """
        payload = InactivityEmailInput(
            student_name=_DEFAULT_STUDENT_NAME,
            student_email=self._recipient_email,
            course_name=_DEFAULT_COURSE_NAME,
            modules_completed=_DEFAULT_MODULES_COMPLETED,
            total_modules=_DEFAULT_TOTAL_MODULES,
            last_active_date=_DEFAULT_LAST_ACTIVE_DATE,
        )

        logger.info(
            "MockLearnerData.get_mock_learner: Returning payload — "
            "student='%s', course='%s', progress=%d/%d, last_active='%s', recipient='%s'.",
            payload["student_name"],
            payload["course_name"],
            payload["modules_completed"],
            payload["total_modules"],
            payload["last_active_date"],
            payload["student_email"],
        )

        return payload

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _resolve_recipient_email() -> str:
        """
        Reads TEST_RECIPIENT_EMAIL from the environment.

        Raises:
            RuntimeError: If the variable is not set or is an empty string,
                          with an actionable message explaining what to set.
        """
        value = os.getenv(_ENV_VAR, "").strip()
        if not value:
            raise RuntimeError(
                f"MockLearnerData requires the '{_ENV_VAR}' environment variable to be set. "
                f"Add '{_ENV_VAR}=your@email.com' to your .env file and restart the process."
            )
        return value
