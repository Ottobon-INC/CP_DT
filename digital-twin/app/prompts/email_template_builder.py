"""
EmailTemplateBuilder: Generates inactivity re-engagement email content.

Responsible solely for building the email subject and HTML body from
learner context data. Contains no sending logic — callers are expected
to pass the output to a dedicated email delivery service.
"""

from dataclasses import dataclass
from typing import TypedDict


# ─── Input / Output Types ────────────────────────────────────────────

class EmailTemplateInput(TypedDict):
    """Typed input schema expected by EmailTemplateBuilder."""
    student_name: str
    course_name: str
    modules_completed: int
    total_modules: int
    last_active_date: str
    platform_name: str


class EmailTemplateOutput(TypedDict):
    """Typed output schema returned by EmailTemplateBuilder."""
    subject: str
    html_body: str


# ─── Builder ─────────────────────────────────────────────────────────

@dataclass
class EmailTemplateBuilder:
    """
    Builds a structured inactivity re-engagement email from learner context.

    Separates template rendering from email delivery so that the output dict
    can be passed directly to any email provider (SMTP, SendGrid, SES, etc.).

    Usage:
        builder = EmailTemplateBuilder()
        result = builder.build({
            "student_name": "Jane Doe",
            "course_name": "Introduction to Python",
            "modules_completed": 3,
            "total_modules": 10,
            "last_active_date": "2026-06-10",
            "platform_name": "CoursePlatform",
        })
        # result["subject"]  -> str
        # result["html_body"] -> str (valid HTML document)
    """

    # ── Subject template ─────────────────────────────────────────────

    _SUBJECT_TEMPLATE: str = (
        "We Miss You, {student_name} – Continue Your Journey in {course_name}"
    )

    # ── Plain-text body (single source of truth for content) ─────────

    _BODY_TEMPLATE: str = """Dear {student_name},

We hope you are doing well.

Our records indicate that there has been no recent activity in your enrolled course, {course_name}. We wanted to reach out and encourage you to continue your learning journey and make progress toward your course completion goals.

Current Progress:

  Course: {course_name}
  Modules Completed: {modules_completed} of {total_modules}
  Last Active Date: {last_active_date}

Consistent engagement is an important part of successfully completing the course and gaining the full benefit of the learning experience.

If you are experiencing any difficulties accessing course materials, managing your schedule, or progressing through the content, please let us know.

Kind regards,
Student Success Team
{platform_name}"""

    # ── HTML skeleton ────────────────────────────────────────────────

    _HTML_TEMPLATE: str = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Course Re-engagement – {course_name}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #f4f6f8;
      font-family: Arial, Helvetica, sans-serif;
      color: #333333;
    }}
    .wrapper {{
      max-width: 600px;
      margin: 40px auto;
      background-color: #ffffff;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }}
    .header {{
      background-color: #1a237e;
      padding: 28px 32px;
    }}
    .header h1 {{
      margin: 0;
      font-size: 20px;
      color: #ffffff;
      font-weight: 600;
      letter-spacing: 0.3px;
    }}
    .body {{
      padding: 32px;
    }}
    .body p {{
      margin: 0 0 16px 0;
      font-size: 15px;
      line-height: 1.7;
      color: #444444;
    }}
    .progress-card {{
      background-color: #f0f4ff;
      border-left: 4px solid #1a237e;
      border-radius: 4px;
      padding: 20px 24px;
      margin: 24px 0;
    }}
    .progress-card h2 {{
      margin: 0 0 14px 0;
      font-size: 14px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: #1a237e;
    }}
    .progress-card table {{
      width: 100%;
      border-collapse: collapse;
    }}
    .progress-card td {{
      padding: 6px 0;
      font-size: 14px;
      color: #333333;
      vertical-align: top;
    }}
    .progress-card td.label {{
      font-weight: 600;
      width: 48%;
      color: #555555;
    }}
    .footer {{
      background-color: #f4f6f8;
      padding: 20px 32px;
      font-size: 13px;
      color: #888888;
      border-top: 1px solid #e0e0e0;
    }}
    .footer strong {{
      color: #555555;
    }}
  </style>
</head>
<body>
  <div class="wrapper">

    <!-- Header -->
    <div class="header">
      <h1>{platform_name} – Student Success Team</h1>
    </div>

    <!-- Body -->
    <div class="body">
      <p>Dear <strong>{student_name}</strong>,</p>

      <p>We hope you are doing well.</p>

      <p>
        Our records indicate that there has been no recent activity in your enrolled course,
        <strong>{course_name}</strong>. We wanted to reach out and encourage you to continue
        your learning journey and make progress toward your course completion goals.
      </p>

      <!-- Progress card -->
      <div class="progress-card">
        <h2>Current Progress</h2>
        <table>
          <tr>
            <td class="label">Course</td>
            <td>{course_name}</td>
          </tr>
          <tr>
            <td class="label">Modules Completed</td>
            <td>{modules_completed} of {total_modules}</td>
          </tr>
          <tr>
            <td class="label">Last Active Date</td>
            <td>{last_active_date}</td>
          </tr>
        </table>
      </div>

      <p>
        Consistent engagement is an important part of successfully completing the course
        and gaining the full benefit of the learning experience.
      </p>

      <p>
        If you are experiencing any difficulties accessing course materials, managing your
        schedule, or progressing through the content, please let us know.
      </p>

      <p>
        Kind regards,<br />
        <strong>Student Success Team</strong><br />
        {platform_name}
      </p>
    </div>

    <!-- Footer -->
    <div class="footer">
      You are receiving this message because you are enrolled in a course on
      <strong>{platform_name}</strong>. If you have questions, please contact
      your course support team.
    </div>

  </div>
</body>
</html>"""

    # ── Public API ───────────────────────────────────────────────────

    def build(self, data: EmailTemplateInput) -> EmailTemplateOutput:
        """
        Renders the email subject and HTML body from the provided learner data.

        Args:
            data: EmailTemplateInput dict containing student and course fields.

        Returns:
            EmailTemplateOutput dict with 'subject' and 'html_body' keys.

        Raises:
            KeyError: If a required field is missing from ``data``.
            ValueError: If ``modules_completed`` or ``total_modules`` are negative,
                        or if ``modules_completed`` exceeds ``total_modules``.
        """
        self._validate(data)

        subject = self._SUBJECT_TEMPLATE.format(
            student_name=data["student_name"],
            course_name=data["course_name"],
        )

        html_body = self._HTML_TEMPLATE.format(
            student_name=data["student_name"],
            course_name=data["course_name"],
            modules_completed=data["modules_completed"],
            total_modules=data["total_modules"],
            last_active_date=data["last_active_date"],
            platform_name=data["platform_name"],
        )

        return EmailTemplateOutput(subject=subject, html_body=html_body)

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _validate(data: EmailTemplateInput) -> None:
        """Validates required fields and numeric constraints."""
        required_fields = (
            "student_name",
            "course_name",
            "modules_completed",
            "total_modules",
            "last_active_date",
            "platform_name",
        )
        for field in required_fields:
            if field not in data or data[field] is None:  # type: ignore[literal-required]
                raise KeyError(f"Missing required field: '{field}'")

        if data["modules_completed"] < 0 or data["total_modules"] < 0:
            raise ValueError("'modules_completed' and 'total_modules' must be non-negative.")

        if data["modules_completed"] > data["total_modules"]:
            raise ValueError(
                f"'modules_completed' ({data['modules_completed']}) cannot exceed "
                f"'total_modules' ({data['total_modules']})."
            )
