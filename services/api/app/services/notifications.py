import smtplib
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Any, Dict

from sqlalchemy.orm import Session

from app import config
from app.models import Notification


class Notifier(ABC):
    @abstractmethod
    def send(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        ...


class InAppNotifier(Notifier):
    def __init__(self, db: Session):
        self.db = db

    def send(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        return {"success": True, "channel": "in_app", "message": "Stored in app inbox"}


class SMTPNotifier(Notifier):
    def send(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        if not config.SMTP_HOST:
            return {"success": False, "channel": "smtp", "message": "SMTP host not configured"}
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = config.SMTP_FROM
            msg["To"] = recipient

            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as server:
                if config.SMTP_USER and config.SMTP_PASSWORD:
                    server.starttls()
                    server.login(config.SMTP_USER, config.SMTP_PASSWORD)
                server.sendmail(config.SMTP_FROM, [recipient], msg.as_string())
            return {"success": True, "channel": "smtp", "message": "Email sent"}
        except Exception as exc:
            return {"success": False, "channel": "smtp", "message": str(exc)}


def create_notification(
    db: Session,
    project_id: str,
    job_id: str | None,
    channel: str,
    recipient: str,
    subject: str,
    body: str,
) -> Notification:
    n = Notification(
        project_id=project_id,
        job_id=job_id,
        channel=channel,
        recipient=recipient,
        subject=subject,
        body=body,
        status="PENDING",
        created_at=datetime.now(timezone.utc),
    )
    db.add(n)
    db.commit()
    db.refresh(n)

    if channel == "smtp":
        result = SMTPNotifier().send(recipient, subject, body)
    else:
        result = InAppNotifier(db).send(recipient, subject, body)

    n.status = "SENT" if result.get("success") else "FAILED"
    db.commit()
    db.refresh(n)
    return n


def notify_render_complete(db: Session, project_id: str, job_id: str, outputs: list, recipients: list[str] | None = None) -> None:
    subject = "Render complete"
    body = f"Job {job_id} completed. Outputs: {outputs}"
    recipients = recipients or [config.SMTP_FROM]
    for channel in config.NOTIFICATION_CHANNELS:
        channel = channel.strip()
        if channel == "in_app":
            create_notification(db, project_id, job_id, channel, "", subject, body)
        elif channel == "smtp":
            for recipient in recipients:
                if recipient:
                    create_notification(db, project_id, job_id, channel, recipient, subject, body)
