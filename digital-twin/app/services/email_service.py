"""
EmailService: Reusable SMTP email delivery service.

Responsibilities:
  - Send HTML emails via SMTP using configured environment variables.
  - Support both STARTTLS (port 587) and implicit SSL (port 465).
  - Return a structured result dict for every send attempt.

Explicitly out of scope:
  - Business logic (inactivity rules, re-engagement decisions, etc.)
  - Learner-specific context (learner IDs, course data, persona, etc.)
  - Template rendering (see EmailTemplateBuilder in app/prompts/)
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TypedDict

from app.config.settings import settings

logger = logging.getLogger(__name__)


# ─── Result Type ─────────────────────────────────────────────────────

class EmailResult(TypedDict):
    """Structured return value from EmailService.send()."""
    success: bool
    status: str
    recipient: str


# ─── Service ─────────────────────────────────────────────────────────

class EmailService:
    """
    Thin SMTP wrapper that sends a single HTML email and returns a
    structured result. All configuration is read from the application
    settings (populated via environment variables).

    TLS mode selection:
        SMTP_USE_SSL=true  → smtplib.SMTP_SSL  (implicit SSL, typically port 465)
        SMTP_USE_TLS=true  → smtplib.SMTP + starttls() (STARTTLS, typically port 587)
        Both false         → smtplib.SMTP plain (no encryption — dev/local only)

    Usage:
        service = EmailService()
        result = service.send(
            recipient="student@example.com",
            subject="Re-engagement Notice",
            html_body="<p>Hello!</p>",
        )
        # result == {"success": True, "status": "sent", "recipient": "student@example.com"}
    """

    def __init__(self) -> None:
        self._host: str = settings.SMTP_HOST or ""
        self._port: int = settings.SMTP_PORT
        self._user: str = settings.SMTP_USER or ""
        self._password: str = settings.SMTP_PASSWORD or ""
        self._use_tls: bool = settings.SMTP_USE_TLS
        self._use_ssl: bool = settings.SMTP_USE_SSL
        self._sender: str = settings.SENDER_EMAIL or self._user

    # ── Public API ───────────────────────────────────────────────────

    def send(
        self,
        recipient: str,
        subject: str,
        html_body: str,
    ) -> EmailResult:
        """
        Sends an HTML email to a single recipient.

        Args:
            recipient:  Destination email address.
            subject:    Email subject line.
            html_body:  Full HTML content for the email body.

        Returns:
            EmailResult with keys 'success', 'status', and 'recipient'.
        """
        if not self._is_configured():
            logger.warning(
                "EmailService: SMTP is not configured. "
                "Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and SENDER_EMAIL."
            )
            return EmailResult(
                success=False,
                status="not_configured",
                recipient=recipient,
            )

        message = self._build_message(recipient, subject, html_body)

        try:
            if self._use_ssl:
                result = self._send_via_ssl(message, recipient)
            else:
                result = self._send_via_starttls(message, recipient)
            return result

        except smtplib.SMTPAuthenticationError as exc:
            logger.error(
                "EmailService: SMTP authentication failed for user '%s': %s",
                self._user,
                exc,
            )
            return EmailResult(success=False, status="auth_error", recipient=recipient)

        except smtplib.SMTPRecipientsRefused as exc:
            logger.error(
                "EmailService: Recipient '%s' was refused by the server: %s",
                recipient,
                exc,
            )
            return EmailResult(success=False, status="recipient_refused", recipient=recipient)

        except smtplib.SMTPConnectError as exc:
            logger.error(
                "EmailService: Could not connect to SMTP server %s:%s — %s",
                self._host,
                self._port,
                exc,
            )
            return EmailResult(success=False, status="connection_error", recipient=recipient)

        except smtplib.SMTPException as exc:
            logger.error(
                "EmailService: SMTP error while sending to '%s': %s",
                recipient,
                exc,
            )
            return EmailResult(success=False, status="smtp_error", recipient=recipient)

        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "EmailService: Unexpected error while sending to '%s': %s",
                recipient,
                exc,
            )
            return EmailResult(success=False, status="unexpected_error", recipient=recipient)

    # ── Private helpers ──────────────────────────────────────────────

    def _is_configured(self) -> bool:
        """Returns True only when the minimum required SMTP fields are present."""
        return bool(self._host and self._user and self._password and self._sender)

    def _build_message(
        self,
        recipient: str,
        subject: str,
        html_body: str,
    ) -> MIMEMultipart:
        """Constructs a MIME multipart email with an HTML alternative part."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._sender
        msg["To"] = recipient
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        return msg

    def _send_via_ssl(self, message: MIMEMultipart, recipient: str) -> EmailResult:
        """Sends using implicit SSL (smtplib.SMTP_SSL — typically port 465)."""
        logger.info(
            "EmailService: Connecting via SSL to %s:%s", self._host, self._port
        )
        with smtplib.SMTP_SSL(self._host, self._port) as server:
            server.login(self._user, self._password)
            server.sendmail(self._sender, recipient, message.as_string())

        logger.info("EmailService: Email delivered to '%s' via SSL.", recipient)
        return EmailResult(success=True, status="sent", recipient=recipient)

    def _send_via_starttls(self, message: MIMEMultipart, recipient: str) -> EmailResult:
        """
        Sends using STARTTLS if SMTP_USE_TLS is True, or plain SMTP otherwise.
        Plain SMTP is only suitable for local/dev environments.
        """
        logger.info(
            "EmailService: Connecting to %s:%s (TLS=%s)",
            self._host,
            self._port,
            self._use_tls,
        )
        with smtplib.SMTP(self._host, self._port) as server:
            server.ehlo()
            if self._use_tls:
                server.starttls()
                server.ehlo()
            server.login(self._user, self._password)
            server.sendmail(self._sender, recipient, message.as_string())

        logger.info(
            "EmailService: Email delivered to '%s' via %s.",
            recipient,
            "STARTTLS" if self._use_tls else "plain SMTP",
        )
        return EmailResult(success=True, status="sent", recipient=recipient)
