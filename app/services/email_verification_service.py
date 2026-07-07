from itsdangerous import BadSignature

from app.core.errors import UnauthorizedError
from app.core.security import (
    create_email_verification_token,
    decode_email_verification_token,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.mailer import Mailer


class EmailVerificationService:
    def __init__(self, user_repository: UserRepository, mailer: Mailer) -> None:
        self.user_repository = user_repository
        self.mailer = mailer

    async def request_verification(self, user: User) -> None:
        token = create_email_verification_token(user.id)
        await self.mailer.send_verification_email(user.email, token)

    async def confirm_verification(self, token: str) -> User:
        try:
            user_id = decode_email_verification_token(token)
        except (BadSignature, ValueError) as exc:
            raise UnauthorizedError("Invalid or expired verification token") from exc

        user = await self.user_repository.mark_email_verified(user_id)
        if not user:
            raise UnauthorizedError("Invalid or expired verification token")
        return user
