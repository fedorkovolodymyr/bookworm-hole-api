from abc import ABC, abstractmethod

from loguru import logger

from app.core.config import Settings


class Mailer(ABC):
    @abstractmethod
    async def send_verification_email(self, to_email: str, token: str) -> None: ...


class ConsoleMailer(Mailer):
    """Dev mailer: logs the token instead of sending an email."""

    async def send_verification_email(self, to_email: str, token: str) -> None:
        logger.info("Email verification token for {}: {}", to_email, token)


class SMTPMailer(Mailer):
    def __init__(
        self,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        from_email: str,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email

    async def send_verification_email(self, to_email: str, token: str) -> None:
        raise NotImplementedError("SMTP sending is not yet implemented")


def build_mailer(settings: Settings) -> Mailer:
    """Config-driven mailer selection.

    Never falls back to ConsoleMailer for a misconfigured "smtp" backend —
    Settings raises at startup instead, so a broken SMTP config can't
    silently leak verification tokens via console/dev logs in production.
    """
    mailer_settings = settings.mailer_settings
    if mailer_settings.backend == "smtp":
        return SMTPMailer(
            host=mailer_settings.smtp_host or "",
            port=mailer_settings.smtp_port,
            username=mailer_settings.smtp_username,
            password=mailer_settings.smtp_password,
            from_email=mailer_settings.smtp_from_email,
        )
    return ConsoleMailer()
