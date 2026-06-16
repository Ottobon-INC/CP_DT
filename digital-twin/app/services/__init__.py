# app.services package
from app.services.email_service import EmailService, EmailResult
from app.services.inactivity_email_workflow import InactivityEmailWorkflow, InactivityEmailInput
from app.services.email_escalation_handler import (
    EmailEscalationHandler,
    AbstractEmailEscalationHandler,
    EmailEscalationState,
    EmailEscalationResult,
    LearnerIdentity,
    LearnerProgressContext,
    InactivityLevel,
    TRIGGER_LEVEL,
)

__all__ = [
    "EmailService",
    "EmailResult",
    "InactivityEmailWorkflow",
    "InactivityEmailInput",
    "EmailEscalationHandler",
    "AbstractEmailEscalationHandler",
    "EmailEscalationState",
    "EmailEscalationResult",
    "LearnerIdentity",
    "LearnerProgressContext",
    "InactivityLevel",
    "TRIGGER_LEVEL",
]

