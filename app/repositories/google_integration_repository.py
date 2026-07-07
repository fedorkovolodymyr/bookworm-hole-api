from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.google_integration import GoogleIntegration


class GoogleIntegrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: UUID) -> GoogleIntegration | None:
        result = await self.session.execute(
            select(GoogleIntegration).where(col(GoogleIntegration.user_id) == user_id)
        )
        return result.scalars().first()

    async def upsert(
        self,
        user_id: UUID,
        access_token_encrypted: str,
        refresh_token_encrypted: str,
        expires_at: datetime,
        scopes: list[str],
        connected_at: datetime,
    ) -> GoogleIntegration:
        integration = await self.get_by_user_id(user_id)
        if integration is None:
            integration = GoogleIntegration(
                user_id=user_id,
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                expires_at=expires_at,
                scopes=scopes,
                connected_at=connected_at,
            )
        else:
            integration.access_token_encrypted = access_token_encrypted
            integration.refresh_token_encrypted = refresh_token_encrypted
            integration.expires_at = expires_at
            integration.scopes = scopes
            integration.connected_at = connected_at

        self.session.add(integration)
        await self.session.commit()
        await self.session.refresh(integration)
        return integration

    async def update_tokens(
        self,
        integration: GoogleIntegration,
        access_token_encrypted: str,
        expires_at: datetime,
    ) -> GoogleIntegration:
        integration.access_token_encrypted = access_token_encrypted
        integration.expires_at = expires_at
        self.session.add(integration)
        await self.session.commit()
        await self.session.refresh(integration)
        return integration

    async def delete(self, integration: GoogleIntegration) -> None:
        await self.session.delete(integration)
        await self.session.commit()
