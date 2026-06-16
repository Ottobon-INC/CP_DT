"""
EmailEscalationHandler: Integration contract for receiving LangGraph state
and invoking the InactivityEmailWorkflow.

─── Architecture position ───────────────────────────────────────────────────

    LangGraph Graph (future)
        └── DetermineLearnerState node  →  sets inactivity_level = "EMAIL_ESCALATED"
        └── EmailEscalationNode (future) →  calls EmailEscalationHandler.handle()
                                                │
                                         EmailEscalationHandler          ← THIS FILE
                                                │
                                         InactivityEmailWorkflow
                                                │
                                    EmailTemplateBuilder + EmailService

─── What is defined here ────────────────────────────────────────────────────

    1. LearnerIdentity        — identity fields (name, email) not held in TwinState today.
    2. LearnerProgressContext — structured view of the computed learner_context dict
                               that TwinState.learner_context already produces.
    3. EmailEscalationState   — the full expected LangGraph state payload this handler
                               will consume when wired into the graph.
    4. EmailEscalationResult  — structured handler return value.
    5. AbstractEmailEscalationHandler — ABC defining the integration contract.
    6. EmailEscalationHandler — concrete implementation: maps state → workflow input
                               and invokes InactivityEmailWorkflow.

─── What is NOT defined here ────────────────────────────────────────────────

    - LangGraph nodes (no @node decorators, no StateGraph wiring).
    - Database queries (learner identity is expected from the state, not fetched here).
    - SMTP configuration (owned by EmailService).
    - Template content (owned by EmailTemplateBuilder).

─── Open integration points (to be resolved when LangGraph node is built) ──

    See: AbstractEmailEscalationHandler._OPEN_INTEGRATION_POINTS
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional, TypedDict

from app.services.email_service import EmailResult
from app.services.inactivity_email_workflow import InactivityEmailInput, InactivityEmailWorkflow

logger = logging.getLogger(__name__)


# ─── Inactivity Level Literals ────────────────────────────────────────
# Mirrors the string states produced by DetermineLearnerState node.
# Only EMAIL_ESCALATED triggers this handler; all others are passed through.

InactivityLevel = Literal[
    "ACTIVE",
    "ATTENTION_DRIFT",
    "CONTENT_FRICTION",
    "INACTIVE_1",
    "INACTIVE_2",
    "INACTIVE_3",
    "EMAIL_ESCALATED",
]

TRIGGER_LEVEL: InactivityLevel = "EMAIL_ESCALATED"


# ─── Sub-schemas within EmailEscalationState ─────────────────────────

class LearnerIdentity(TypedDict):
    """
    Identity fields for the learner that are NOT produced by aggregate_learner_context()
    and must be carried explicitly in the LangGraph state.

    Integration note:
        The retrieve_learner_context node (or a dedicated identity-fetch node) must
        populate these fields before the email escalation node is reached in the graph.

    Fields:
        student_name:  Full display name of the learner (e.g. "Jane Doe").
        student_email: Email address used for re-engagement delivery.
        course_name:   Human-readable name of the enrolled course.
    """
    student_name: str
    student_email: str
    course_name: str


class LearnerProgressContext(TypedDict):
    """
    Structured view of the aggregated learner context produced by
    aggregate_learner_context() and stored in TwinState.learner_context.

    These fields are computed by the retrieve_learner_context node.

    Fields:
        current_course_progress:  Dict containing 'modules_tracked' (int) and
                                  'average_completed_percentage' (float).
        active_topic:             ID of the current incomplete topic, or None.
        quiz_performance_summary: Dict with 'total_attempts', 'pass_rate', 'average_score'.
        learner_persona:          Dict with 'type' and 'profile_details'.
        recent_ai_chat_summaries: List of recent message snippet dicts.
        last_active_date:         ISO date string of the learner's most recent activity
                                  (e.g. "2026-06-15"). Derived from latest_event.created_at.
    """
    current_course_progress: Dict[str, Any]
    active_topic: Optional[str]
    quiz_performance_summary: Dict[str, Any]
    learner_persona: Dict[str, Any]
    recent_ai_chat_summaries: List[Dict[str, Any]]
    last_active_date: str          # Populated from TwinState.latest_event.created_at


class EmailEscalationState(TypedDict):
    """
    The expected LangGraph state payload consumed by EmailEscalationHandler.

    This is the integration contract between the LangGraph graph and this handler.
    When the DetermineLearnerState node sets inactivity_level = "EMAIL_ESCALATED",
    the graph routes to an EmailEscalationNode which calls handler.handle(state).

    Relationship to TwinState (app/graphs/state.py):
        learner_id        ← TwinState.learner_id
        inactivity_level  ← TwinState.latest_event["learner_state"]  (string form)
        learner_context   ← TwinState.learner_context  +  identity fields below

    Fields:
        learner_id:        Unique identifier of the learner.
        inactivity_level:  Current learner state label (must be "EMAIL_ESCALATED"
                           for this handler to send an email).
        learner_context:   Aggregated learner progress data (from retrieve_learner_context).
        learner_identity:  Identity fields not yet in TwinState — to be resolved when
                           the identity-fetch node is added to the graph.

    Example:
        {
            "learner_id":       "a1b2c3d4-...",
            "inactivity_level": "EMAIL_ESCALATED",
            "learner_context": {
                "current_course_progress": {"modules_tracked": 10, ...},
                "last_active_date": "2026-06-15",
                ...
            },
            "learner_identity": {
                "student_name":  "Jane Doe",
                "student_email": "jane@example.com",
                "course_name":   "AI Foundations",
            }
        }
    """
    learner_id: str
    inactivity_level: InactivityLevel
    learner_context: LearnerProgressContext
    learner_identity: LearnerIdentity


# ─── Handler Result ───────────────────────────────────────────────────

class EmailEscalationResult(TypedDict):
    """
    Structured return value from EmailEscalationHandler.handle().

    Fields:
        triggered:  True if inactivity_level was EMAIL_ESCALATED and the
                    workflow was invoked; False if the handler skipped the state.
        delivery:   The EmailResult from InactivityEmailWorkflow.execute(),
                    or None if the handler did not trigger.
        learner_id: The learner_id from the input state, for traceability.
    """
    triggered: bool
    delivery: Optional[EmailResult]
    learner_id: str


# ─── Abstract Interface ───────────────────────────────────────────────

class AbstractEmailEscalationHandler(ABC):
    """
    Defines the integration contract between the LangGraph graph and the
    InactivityEmailWorkflow.

    Implementors must override:
        handle(state)      — entry point called by the LangGraph node.
        _map_to_input(state) — translates state fields to InactivityEmailInput.

    Open integration points (tracked here until LangGraph node is built):
    """

    # Items that need to be resolved when the actual LangGraph node is created.
    _OPEN_INTEGRATION_POINTS = [
        "1. learner_identity must be populated by a preceding LangGraph node "
           "(e.g. retrieve_learner_identity) that fetches student_name and "
           "student_email from the users table.",

        "2. last_active_date must be copied from TwinState.latest_event['created_at'] "
           "into LearnerProgressContext.last_active_date by the retrieve_learner_context "
           "node before the escalation node is reached.",

        "3. inactivity_level in EmailEscalationState is the string form of the learner "
           "state (e.g. 'EMAIL_ESCALATED'), whereas TwinState.inactivity_level is an int "
           "(0–4). The graph node must convert: {4: 'EMAIL_ESCALATED', 3: 'INACTIVE_3', ...}.",

        "4. The LangGraph node that calls this handler should be conditional: only route "
           "to EmailEscalationNode when TwinState.should_email is True.",
    ]

    @abstractmethod
    def handle(self, state: EmailEscalationState) -> EmailEscalationResult:
        """
        Entry point called by the LangGraph EmailEscalationNode.

        Implementations must:
            1. Guard: return a non-triggered result if inactivity_level != EMAIL_ESCALATED.
            2. Map: translate EmailEscalationState → InactivityEmailInput.
            3. Invoke: call InactivityEmailWorkflow.execute().
            4. Return: an EmailEscalationResult reflecting the outcome.

        Args:
            state: Full LangGraph escalation state as defined by EmailEscalationState.

        Returns:
            EmailEscalationResult — never raises.
        """

    @abstractmethod
    def _map_to_input(self, state: EmailEscalationState) -> InactivityEmailInput:
        """
        Maps an EmailEscalationState to InactivityEmailInput.

        This is the field-level translation contract between LangGraph state
        and the workflow layer.

        Mapping:
            state.learner_identity.student_name        → input.student_name
            state.learner_identity.student_email       → input.student_email
            state.learner_identity.course_name         → input.course_name
            state.learner_context.current_course_progress
                ["modules_tracked"]                    → input.modules_completed (approximation)
            state.learner_context.current_course_progress
                ["modules_tracked"]                    → input.total_modules
            state.learner_context.last_active_date     → input.last_active_date

        Note:
            modules_completed vs total_modules: TwinState.learner_context only
            holds 'modules_tracked' (total tracked modules). A dedicated progress
            field for completed vs total will be needed from the data layer.
            Until then, the concrete implementation uses a reasonable approximation.

        Args:
            state: EmailEscalationState to translate.

        Returns:
            InactivityEmailInput ready for InactivityEmailWorkflow.execute().
        """


# ─── Concrete Implementation ──────────────────────────────────────────

class EmailEscalationHandler(AbstractEmailEscalationHandler):
    """
    Concrete handler that maps LangGraph inactivity state to the
    InactivityEmailWorkflow and returns a structured result.

    This class is ready to be called from a LangGraph node:

        from app.services.email_escalation_handler import (
            EmailEscalationHandler,
            EmailEscalationState,
        )

        handler = EmailEscalationHandler()

        def email_escalation_node(state: TwinState) -> dict:
            escalation_state = _adapt_twin_state(state)       # future adapter
            result = handler.handle(escalation_state)
            return {"generated_response": result["delivery"]["status"]}

    Dependency injection:
        Pass a pre-constructed InactivityEmailWorkflow to the constructor
        to override SMTP or template behaviour in tests.
    """

    def __init__(
        self,
        workflow: Optional[InactivityEmailWorkflow] = None,
    ) -> None:
        """
        Args:
            workflow: Optional pre-constructed InactivityEmailWorkflow.
                      Defaults to a new instance if not provided.
        """
        self._workflow: InactivityEmailWorkflow = workflow or InactivityEmailWorkflow()

    # ── Public API ───────────────────────────────────────────────────

    def handle(self, state: EmailEscalationState) -> EmailEscalationResult:
        """
        Guards on inactivity_level, maps state to workflow input, and
        invokes InactivityEmailWorkflow.execute().

        Returns:
            EmailEscalationResult — triggered=False if level != EMAIL_ESCALATED,
            triggered=True with delivery result otherwise.
        """
        learner_id = state.get("learner_id", "unknown")
        inactivity_level = state.get("inactivity_level", "")

        # ── Guard: only act on EMAIL_ESCALATED ────────────────────────
        if inactivity_level != TRIGGER_LEVEL:
            logger.info(
                "EmailEscalationHandler: Skipping — learner '%s' is at level '%s' "
                "(not %s).",
                learner_id,
                inactivity_level,
                TRIGGER_LEVEL,
            )
            return EmailEscalationResult(
                triggered=False,
                delivery=None,
                learner_id=learner_id,
            )

        logger.info(
            "EmailEscalationHandler: Triggered for learner '%s' at level '%s'.",
            learner_id,
            inactivity_level,
        )

        # ── Map state → workflow input ────────────────────────────────
        try:
            workflow_input = self._map_to_input(state)
        except (KeyError, TypeError, ValueError) as exc:
            logger.error(
                "EmailEscalationHandler: State mapping failed for learner '%s': %s",
                learner_id,
                exc,
            )
            return EmailEscalationResult(
                triggered=True,
                delivery=EmailResult(
                    success=False,
                    status=f"mapping_error: {exc}",
                    recipient="",
                ),
                learner_id=learner_id,
            )

        # ── Invoke workflow ───────────────────────────────────────────
        delivery = self._workflow.execute(workflow_input)

        logger.info(
            "EmailEscalationHandler: Workflow result for learner '%s' — "
            "success=%s, status='%s', recipient='%s'.",
            learner_id,
            delivery["success"],
            delivery["status"],
            delivery["recipient"],
        )

        return EmailEscalationResult(
            triggered=True,
            delivery=delivery,
            learner_id=learner_id,
        )

    # ── Field Mapping ─────────────────────────────────────────────────

    def _map_to_input(self, state: EmailEscalationState) -> InactivityEmailInput:
        """
        Translates EmailEscalationState to InactivityEmailInput.

        Field mapping contract:
            identity.student_name           → student_name
            identity.student_email          → student_email
            identity.course_name            → course_name
            context.last_active_date        → last_active_date
            context.current_course_progress → modules_completed / total_modules
                ["modules_tracked"]           (see NOTE below)

        NOTE — modules_completed vs total_modules:
            LearnerProgressContext only tracks 'modules_tracked' (total count).
            'modules_completed' is approximated here as the count of modules
            whose status is 'completed'. This approximation holds until the data
            layer exposes an explicit completed_count field alongside modules_tracked.
        """
        identity: LearnerIdentity = state["learner_identity"]
        context: LearnerProgressContext = state["learner_context"]
        progress: Dict[str, Any] = context.get("current_course_progress", {})

        # Derive modules_completed from status list (approximation)
        statuses: List[str] = progress.get("statuses", [])
        modules_completed: int = sum(1 for s in statuses if s == "completed")
        total_modules: int = progress.get("modules_tracked", len(statuses))

        return InactivityEmailInput(
            student_name=identity["student_name"],
            student_email=identity["student_email"],
            course_name=identity["course_name"],
            modules_completed=modules_completed,
            total_modules=total_modules,
            last_active_date=context.get("last_active_date", ""),
        )
