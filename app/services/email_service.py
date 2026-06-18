import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from app.config.settings import settings
from app.services.supabase_client import _get

logger = logging.getLogger(__name__)


def _fetch_learner_email_info(learner_id: str) -> Dict[str, Any]:
    """Fetches learner name and email from the users table."""
    rows = _get("users", {
        "select": "full_name,email",
        "user_id": f"eq.{learner_id}",
        "limit": "1",
    })
    if rows:
        return {
            "name": rows[0].get("full_name", "Student"),
            "email": rows[0].get("email"),
        }
    return {"name": "Student", "email": None}


def _fetch_course_name(course_id: str) -> str:
    """Fetches the course name from the courses table."""
    if not course_id:
        return "your course"
    rows = _get("courses", {
        "select": "course_name",
        "course_id": f"eq.{course_id}",
        "limit": "1",
    })
    if rows:
        return rows[0].get("course_name", "your course")
    return "your course"


def _build_inactivity_email(student_name: str, course_name: str) -> tuple:
    """Builds subject and HTML body for an inactivity escalation email."""
    subject = f"We miss you, {student_name}! Come back to {course_name}"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2563eb;">Hey {student_name} 👋</h2>
            <p>We noticed you haven't been active on <strong>{course_name}</strong> for a while.</p>
            <p>Your tutor and the learning platform miss you! Here's a quick reminder of why coming back matters:</p>
            <ul>
                <li>📚 Your progress is saved — pick up right where you left off</li>
                <li>🎯 Staying consistent is the #1 predictor of course completion</li>
                <li>💬 Your tutor is ready to help with any questions</li>
            </ul>
            <p style="margin-top: 20px;">
                <a href="#" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Resume Learning →
                </a>
            </p>
            <p style="margin-top: 30px; font-size: 12px; color: #888;">
                This is an automated message from the Ottobon Learning Platform.
            </p>
        </div>
    </body>
    </html>
    """
    return subject, body


def _build_friendly_deadline_email(student_name: str, course_name: str, module_no: int) -> tuple:
    """Builds subject and HTML body for a friendly module completion reminder email."""
    subject = f"Friendly check-in: {course_name} Module {module_no}"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2563eb;">Friendly Reminder 👋</h2>
            <p>Hi {student_name},</p>
            <p>We noticed you started <strong>Module {module_no}</strong> in <strong>{course_name}</strong> a week ago but haven't finished it yet.</p>
            <p>No rush! We just wanted to check in and see if you need any help. You can reply to this email or chat directly with your AI tutor on the platform.</p>
            <p style="margin-top: 20px;">
                <a href="#" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Continue Learning →
                </a>
            </p>
            <p style="margin-top: 30px; font-size: 12px; color: #888;">
                This is a friendly check-in from the Ottobon Learning Platform.
            </p>
        </div>
    </body>
    </html>
    """
    return subject, body


def _send_smtp_email(to_email: str, subject: str, html_body: str) -> bool:
    """Sends an email via SMTP. Returns True on success, False on failure."""
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning(
            f"[EMAIL SKIPPED] SMTP credentials not configured. "
            f"Would have sent email to {to_email}: {subject}"
        )
        print(f"[EMAIL SKIPPED] To: {to_email} | Subject: {subject}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"[EMAIL SENT] Successfully sent email to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"[EMAIL ERROR] Failed to send email to {to_email}: {e}")
        print(f"[EMAIL ERROR] To: {to_email} | Subject: {subject} | Error: {e}")
        return False


def send_engagement_email(
    learner_id: str,
    course_id: Optional[str] = None,
    email_type: str = "inactivity_escalation",
    module_no: Optional[int] = None,
) -> bool:
    """
    Main entry point for sending engagement emails.
    Fetches learner info from DB, builds the appropriate template, and dispatches.
    
    email_type: "inactivity_escalation" | "module_deadline_friendly"
    """
    info = _fetch_learner_email_info(learner_id)
    student_name = info["name"]
    student_email = info.get("email")

    if not student_email:
        logger.warning(f"[EMAIL SKIPPED] No email address found for learner {learner_id}")
        return False

    course_name = _fetch_course_name(course_id)

    if email_type == "inactivity_escalation":
        subject, body = _build_inactivity_email(student_name, course_name)
    elif email_type == "module_deadline_friendly":
        val_mod = module_no if module_no is not None else 1
        subject, body = _build_friendly_deadline_email(student_name, course_name, val_mod)
    else:
        logger.warning(f"[EMAIL SKIPPED] Unknown email_type: {email_type}")
        return False

    return _send_smtp_email(student_email, subject, body)
