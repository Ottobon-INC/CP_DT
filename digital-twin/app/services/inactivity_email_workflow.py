"""
InactivityEmailWorkflow: Orchestrates template rendering and email delivery
for learner inactivity re-engagement notifications.

Architecture:
    InactivityEmailWorkflow
        └── EmailTemplateBuilder   (app/prompts/)   renders subject + HTML body
        └── EmailService           (app/services/)  sends via SMTP

Responsibilities of this class:
    - Accept learner inactivity context as input.
    - Coordinate EmailTemplateBuilder → EmailService in sequence.
    - Enrich template input with platform_name from application settings.
    - Return a single structured delivery result.

Explicitly out of scope:
    - Inactivity thresholds or stage-transition logic (see inactivity.py).
    - SMTP configuration (owned by EmailService).
    - HTML/subject content (owned by EmailTemplateBuilder).
"""

import logging
from typing import TypedDict

from app.config.settings import settings
from app.prompts.email_template_builder import EmailTemplateBuilder, EmailTemplateInput
from app.services.email_service import EmailResult, EmailService

logger = logging.getLogger(__name__)


# ─── Input Type ──────────────────────────────────────────────────────

class InactivityEmailInput(TypedDict):
    """
    Learner inactivity context required to generate and send a
    re-engagement email.

    Fields:
        student_name:      Display name of the learner.
        student_email:     Destination email address for delivery.
        course_name:       Human-readable name of the enrolled course.
        modules_completed: Number of modules the learner has completed.
        total_modules:     Total number of modules in the course.
        last_active_date:  ISO-formatted date of the learner's last activity
                           (e.g. "2026-06-10").
    """
    student_name: str
    student_email: str
    course_name: str
    modules_completed: int
    total_modules: int
    last_active_date: str


# ─── Workflow ─────────────────────────────────────────────────────────

class InactivityEmailWorkflow:
    """
    Composes EmailTemplateBuilder and EmailService to send a single
    inactivity re-engagement email for a learner.

    Dependencies are injected via the constructor so they can be
    replaced with mocks or alternative implementations in tests.

    Usage:
        workflow = InactivityEmailWorkflow()
        result = workflow.execute({
            "student_name":      "Jane Doe",
            "student_email":     "jane@example.com",
            "course_name":       "Introduction to Python",
            "modules_completed": 3,
            "total_modules":     10,
            "last_active_date":  "2026-06-10",
        })
        # result == {
        #     "success":   True,
        #     "status":    "sent",
        #     "recipient": "jane@example.com",
        # }
    """

    def __init__(
        self,
        template_builder: EmailTemplateBuilder | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        """
        Args:
            template_builder: Optional pre-constructed EmailTemplateBuilder.
                              Defaults to a new instance if not provided.
            email_service:    Optional pre-constructed EmailService.
                              Defaults to a new instance if not provided.
        """
        self._builder: EmailTemplateBuilder = template_builder or EmailTemplateBuilder()
        self._mailer: EmailService = email_service or EmailService()

    # ── Public API ───────────────────────────────────────────────────

    def execute(self, data: InactivityEmailInput) -> EmailResult:
        """
        Runs the full inactivity email workflow:
            1. Validate and enrich input data.
            2. Render subject and HTML body via EmailTemplateBuilder.
            3. Deliver the email via EmailService.
            4. Return the delivery result.

        Args:
            data: InactivityEmailInput containing learner and course context.

        Returns:
            EmailResult with keys 'success', 'status', and 'recipient'.
            Never raises — all exceptions are caught and reflected in the result.
        """
        recipient = data.get("student_email", "")

        logger.info(
            "InactivityEmailWorkflow: Starting workflow for recipient='%s', course='%s'.",
            recipient,
            data.get("course_name", ""),
        )

        # ── Step 1: Validate input ────────────────────────────────────
        validation_error = self._validate(data)
        if validation_error:
            logger.error(
                "InactivityEmailWorkflow: Input validation failed — %s", validation_error
            )
            return EmailResult(
                success=False,
                status=f"validation_error: {validation_error}",
                recipient=recipient,
            )

        # ── Step 2: Build template input (inject platform_name) ───────
        template_input = EmailTemplateInput(
            student_name=data["student_name"],
            course_name=data["course_name"],
            modules_completed=data["modules_completed"],
            total_modules=data["total_modules"],
            last_active_date=data["last_active_date"],
            platform_name=settings.APP_NAME,
        )

        # ── Step 3: Render subject + HTML body ────────────────────────
        try:
            rendered = self._builder.build(template_input)
        except (KeyError, ValueError) as exc:
            logger.error(
                "InactivityEmailWorkflow: Template rendering failed for '%s': %s",
                recipient,
                exc,
            )
            return EmailResult(
                success=False,
                status=f"template_error: {exc}",
                recipient=recipient,
            )

        logger.debug(
            "InactivityEmailWorkflow: Template rendered — subject='%s'.", rendered["subject"]
        )

        # ── Step 4: Send email ────────────────────────────────────────
        result = self._mailer.send(
            recipient=recipient,
            subject=rendered["subject"],
            html_body=rendered["html_body"],
        )

        # ── Step 5: Log outcome and return ───────────────────────────
        if result["success"]:
            logger.info(
                "InactivityEmailWorkflow: Email delivered successfully to '%s'.", recipient
            )
        else:
            logger.warning(
                "InactivityEmailWorkflow: Email delivery failed for '%s' — status='%s'.",
                recipient,
                result["status"],
            )

        return result

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _validate(data: InactivityEmailInput) -> str:
        """
        Validates required string and numeric fields.

        Returns:
            An empty string if valid, or a human-readable error message.
        """
        required_str_fields = (
            "student_name",
            "student_email",
            "course_name",
            "last_active_date",
        )
        for field in required_str_fields:
            value = data.get(field)  # type: ignore[literal-required]
            if not value or not str(value).strip():
                return f"'{field}' is required and must not be empty."

        modules_completed = data.get("modules_completed")
        total_modules = data.get("total_modules")

        if modules_completed is None or not isinstance(modules_completed, int):
            return "'modules_completed' must be a non-negative integer."

        if total_modules is None or not isinstance(total_modules, int):
            return "'total_modules' must be a non-negative integer."

        if modules_completed < 0 or total_modules < 0:
            return "'modules_completed' and 'total_modules' must be non-negative."

        if modules_completed > total_modules:
            return (
                f"'modules_completed' ({modules_completed}) cannot exceed "
                f"'total_modules' ({total_modules})."
            )

        return ""
