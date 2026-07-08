from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def get_by_jti(self, jti: str) -> PasswordResetToken | None:
        result = await self.session.execute(
            select(PasswordResetToken).where(col(PasswordResetToken.jti) == jti)
        )
        return result.scalars().first()

    async def mark_used(self, jti: str) -> PasswordResetToken | None:
        token = await self.get_by_jti(jti)
        if not token:
            return None
        token.used_at = datetime.now()
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token
