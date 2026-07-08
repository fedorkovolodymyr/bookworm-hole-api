from datetime import UTC, datetime
from uuid import UUID

import jwt
from loguru import logger

from app.core.encryption import decrypt, encrypt
from app.core.errors import (
    ErrorMessages,
    ExternalServiceError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.security import create_oauth_state, decode_oauth_state
from app.models.google_integration import GoogleIntegration
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.services.external.google_oauth import GoogleOAuthAdapter


class GoogleIntegrationService:
    def __init__(
        self,
        repository: GoogleIntegrationRepository,
        adapter: GoogleOAuthAdapter | None = None,
    ) -> None:
        self.repository = repository
        self.adapter = adapter or GoogleOAuthAdapter()

    def get_authorization_url(self, user_id: UUID) -> str:
        state = create_oauth_state(user_id)
        return self.adapter.build_authorization_url(state)

    async def handle_callback(
        self, code: str | None, state: str | None, error: str | None
    ) -> GoogleIntegration:
        if error is not None:
            raise UnauthorizedError(ErrorMessages.GOOGLE_OAUTH_DENIED)
        if not code or not state:
            raise UnauthorizedError(ErrorMessages.INVALID_OAUTH_STATE)

        try:
            user_id = decode_oauth_state(state)
        except (jwt.PyJWTError, KeyError, ValueError) as exc:
            raise UnauthorizedError(ErrorMessages.INVALID_OAUTH_STATE) from exc

        tokens = await self.adapter.exchange_code(code)

        return await self.repository.upsert(
            user_id=user_id,
            access_token_encrypted=encrypt(tokens.access_token),
            refresh_token_encrypted=encrypt(tokens.refresh_token),
            expires_at=tokens.expires_at,
            scopes=tokens.scopes,
            connected_at=datetime.now(UTC),
        )

    async def get_valid_access_token(self, user_id: UUID) -> str:
        """Returns a usable access token, transparently refreshing it first if
        it has expired. Never logs the decrypted token."""
        integration = await self.repository.get_by_user_id(user_id)
        if integration is None:
            raise NotFoundError(ErrorMessages.GOOGLE_INTEGRATION_NOT_FOUND)

        if integration.expires_at > datetime.now(UTC):
            return decrypt(integration.access_token_encrypted)

        refresh_token = decrypt(integration.refresh_token_encrypted)
        tokens = await self.adapter.refresh(refresh_token)
        integration = await self.repository.update_tokens(
            integration,
            access_token_encrypted=encrypt(tokens.access_token),
            expires_at=tokens.expires_at,
        )
        return decrypt(integration.access_token_encrypted)

    async def revoke_and_delete(self, user_id: UUID) -> None:
        integration = await self.repository.get_by_user_id(user_id)
        if integration is None:
            raise NotFoundError(ErrorMessages.GOOGLE_INTEGRATION_NOT_FOUND)

        access_token = decrypt(integration.access_token_encrypted)
        try:
            await self.adapter.revoke(access_token)
        except ExternalServiceError:
            logger.warning(
                "Google token revocation failed; clearing local tokens anyway"
            )

        await self.repository.delete(integration)
