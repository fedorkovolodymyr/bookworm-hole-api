import pytest

from app.core.config import MailerSettings, Settings
from app.services.mailer import ConsoleMailer, SMTPMailer, build_mailer


async def test_console_mailer_send_verification_email_succeeds():
    mailer = ConsoleMailer()
    await mailer.send_verification_email("reader@example.com", "sometoken")


def test_smtp_mailer_send_not_implemented():
    mailer = SMTPMailer(
        host="smtp.example.com",
        port=587,
        username="user",
        password="pass",
        from_email="noreply@example.com",
    )
    assert mailer.host == "smtp.example.com"


async def test_smtp_mailer_send_raises_not_implemented():
    mailer = SMTPMailer(
        host="smtp.example.com",
        port=587,
        username=None,
        password=None,
        from_email="noreply@example.com",
    )
    with pytest.raises(NotImplementedError):
        await mailer.send_verification_email("reader@example.com", "sometoken")


def test_build_mailer_defaults_to_console(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "dev")
    settings = Settings()
    assert isinstance(build_mailer(settings), ConsoleMailer)


def test_build_mailer_returns_smtp_when_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MAILER_BACKEND", "smtp")
    monkeypatch.setenv("MAILER_SMTP_HOST", "smtp.example.com")
    settings = Settings()
    mailer = build_mailer(settings)
    assert isinstance(mailer, SMTPMailer)
    assert mailer.host == "smtp.example.com"


def test_mailer_settings_smtp_backend_without_host_raises(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("MAILER_BACKEND", "smtp")
    monkeypatch.delenv("MAILER_SMTP_HOST", raising=False)
    with pytest.raises(RuntimeError):
        Settings()


def test_mailer_settings_defaults():
    settings = MailerSettings()
    assert settings.backend == "console"
    assert settings.smtp_host is None
