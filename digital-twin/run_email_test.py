"""
run_email_test.py — Standalone test runner for the inactivity email workflow.

Runs the full pipeline end-to-end without LangGraph or FastAPI:

    MockLearnerData
        ↓  get_mock_learner()
    InactivityEmailWorkflow
        ↓  EmailTemplateBuilder  →  renders subject + HTML body
        ↓  EmailService          →  sends via SMTP
    Print delivery result

Usage:
    python run_email_test.py

Requirements:
    .env must contain:
        TEST_RECIPIENT_EMAIL  — inbox that receives the test email
        SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SENDER_EMAIL
"""

import io
import logging
import sys
from pathlib import Path

# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Bootstrap: load .env before importing any app modules ────────────
# Must run before any app import so pydantic Settings() picks up the
# values. Uses __file__-relative path so the script works from any cwd.
# override=True ensures .env values are applied even if a same-named
# system environment variable already exists.
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=True)
    print(f"[INFO] Loaded environment from '{_env_path}'.")
else:
    print(
        f"[WARN] No .env file found at '{_env_path}'. "
        "Ensure environment variables are set manually."
    )

# ── Logging setup ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("run_email_test")

# ── App imports (after .env is loaded) ───────────────────────────────
from tests.mock_learner_data import MockLearnerData                      # noqa: E402
from app.services.inactivity_email_workflow import InactivityEmailWorkflow  # noqa: E402


# ─── Runner ───────────────────────────────────────────────────────────

def run() -> None:
    _print_banner()

    # ── Step 1: Load mock learner data ────────────────────────────────
    logger.info("Step 1 — Loading mock learner data...")
    try:
        provider = MockLearnerData()
        payload  = provider.get_mock_learner()
    except RuntimeError as exc:
        logger.error("Failed to load mock learner data: %s", exc)
        sys.exit(1)

    _print_payload(payload)

    # ── Step 2 & 3: Generate email + Send (via InactivityEmailWorkflow) ─
    logger.info("Step 2 — Generating email content via EmailTemplateBuilder...")
    logger.info("Step 3 — Sending email via EmailService (SMTP)...")
    workflow = InactivityEmailWorkflow()
    result   = workflow.execute(payload)

    # ── Step 4: Print delivery result ─────────────────────────────────
    logger.info("Step 4 — Workflow complete.")
    _print_result(result)

    # Exit with a non-zero code on failure so CI can catch it
    if not result["success"]:
        sys.exit(1)


# ─── Display Helpers ──────────────────────────────────────────────────

def _print_banner() -> None:
    print()
    print("=" * 60)
    print("  Digital Twin — Inactivity Email Workflow Test Runner")
    print("=" * 60)
    print()


def _print_payload(payload: dict) -> None:
    print()
    print("  +-- Learner Payload " + "-" * 40)
    for key, value in payload.items():
        label = key.replace("_", " ").title().ljust(22)
        print(f"  |  {label}: {value}")
    print("  +" + "-" * 59)
    print()


def _print_result(result: dict) -> None:
    success   = result.get("success", False)
    status    = result.get("status", "unknown")
    recipient = result.get("recipient", "-")

    icon  = "[OK]" if success else "[FAIL]"
    label = "SUCCESS" if success else "FAILED"

    print()
    print("  +-- Delivery Result " + "-" * 40)
    print(f"  |  Outcome   :  {icon} {label}")
    print(f"  |  Status    :  {status}")
    print(f"  |  Recipient :  {recipient}")
    print("  +" + "-" * 59)
    print()

    if success:
        logger.info(
            "Email delivered successfully to '%s'.",
            recipient,
        )
    else:
        logger.error(
            "Email delivery failed — status='%s', recipient='%s'.",
            status,
            recipient,
        )


# ─── Entry Point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    run()
