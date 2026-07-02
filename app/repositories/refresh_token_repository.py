from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, token: RefreshToken) -> RefreshToken:
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(col(RefreshToken.jti) == jti)
        )
        return result.scalars().first()

    async def revoke(self, jti: str) -> None:
        token = await self.get_by_jti(jti)
        if token is None:
            return
        token.revoked_at = datetime.now(UTC)
        self.session.add(token)
        await self.session.commit()
