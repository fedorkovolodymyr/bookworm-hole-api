from uuid import uuid4

import pytest

from app.core.errors import UnauthorizedError
from app.core.security import create_email_verification_token
from app.models.user import User
from app.services.email_verification_service import EmailVerificationService


class FakeUserRepository:
    def __init__(self, user: User | None = None):
        self.user = user
        self.marked_verified_ids: list[object] = []

    async def mark_email_verified(self, user_id):
        self.marked_verified_ids.append(user_id)
        if self.user is None or self.user.id != user_id:
            return None
        self.user.email_verified_at = "verified"
        return self.user


class FakeMailer:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    async def send_verification_email(self, to_email: str, token: str) -> None:
        self.sent.append((to_email, token))


class TestRequestVerification:
    async def test_sends_token_to_users_email(self):
        user = User(email="reader@example.com", username="reader", display_name="R")
        mailer = FakeMailer()
        service = EmailVerificationService(FakeUserRepository(user), mailer)

        await service.request_verification(user)

        assert len(mailer.sent) == 1
        assert mailer.sent[0][0] == "reader@example.com"
        assert mailer.sent[0][1]


class TestConfirmVerification:
    async def test_marks_user_verified_for_valid_token(self):
        user = User(email="reader@example.com", username="reader", display_name="R")
        token = create_email_verification_token(user.id)
        repository = FakeUserRepository(user)
        service = EmailVerificationService(repository, FakeMailer())

        result = await service.confirm_verification(token)

        assert result is user
        assert repository.marked_verified_ids == [user.id]

    async def test_rejects_malformed_token(self):
        service = EmailVerificationService(FakeUserRepository(), FakeMailer())

        with pytest.raises(UnauthorizedError):
            await service.confirm_verification("not-a-real-token")

    async def test_rejects_token_for_unknown_user(self):
        token = create_email_verification_token(uuid4())
        service = EmailVerificationService(FakeUserRepository(user=None), FakeMailer())

        with pytest.raises(UnauthorizedError):
            await service.confirm_verification(token)
