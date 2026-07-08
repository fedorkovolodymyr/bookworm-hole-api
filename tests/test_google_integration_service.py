from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.core.encryption import decrypt, encrypt
from app.core.errors import ExternalServiceError, NotFoundError, UnauthorizedError
from app.core.security import create_oauth_state
from app.models.google_integration import GoogleIntegration
from app.services.external.google_oauth import GoogleOAuthTokens
from app.services.google_integration_service import GoogleIntegrationService

_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class FakeRepository:
    def __init__(self) -> None:
        self.by_user: dict[UUID, GoogleIntegration] = {}

    async def get_by_user_id(self, user_id: UUID) -> GoogleIntegration | None:
        return self.by_user.get(user_id)

    async def upsert(
        self,
        user_id: UUID,
        access_token_encrypted: str,
        refresh_token_encrypted: str,
        expires_at: datetime,
        scopes: list[str],
        connected_at: datetime,
    ) -> GoogleIntegration:
        integration = GoogleIntegration(
            user_id=user_id,
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            expires_at=expires_at,
            scopes=scopes,
            connected_at=connected_at,
        )
        self.by_user[user_id] = integration
        return integration

    async def update_tokens(
        self,
        integration: GoogleIntegration,
        access_token_encrypted: str,
        expires_at: datetime,
    ) -> GoogleIntegration:
        integration.access_token_encrypted = access_token_encrypted
        integration.expires_at = expires_at
        return integration

    async def delete(self, integration: GoogleIntegration) -> None:
        self.by_user.pop(integration.user_id, None)


class FakeAdapter:
    def __init__(self) -> None:
        self.revoked: list[str] = []
        self.refresh_calls: list[str] = []
        self.fail_revoke = False
        self.fail_exchange = False

    def build_authorization_url(self, state: str) -> str:
        return f"https://accounts.google.com/o/oauth2/v2/auth?state={state}"

    async def exchange_code(self, code: str) -> GoogleOAuthTokens:
        if self.fail_exchange:
            raise ExternalServiceError("exchange failed")
        return GoogleOAuthTokens(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            scopes=_SCOPES,
        )

    async def refresh(self, refresh_token: str) -> GoogleOAuthTokens:
        self.refresh_calls.append(refresh_token)
        return GoogleOAuthTokens(
            access_token="refreshed-access-token",
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            scopes=_SCOPES,
        )

    async def revoke(self, token: str) -> None:
        self.revoked.append(token)
        if self.fail_revoke:
            raise ExternalServiceError("revoke failed")


@pytest.fixture
def repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def adapter() -> FakeAdapter:
    return FakeAdapter()


@pytest.fixture
def service(
    repository: FakeRepository, adapter: FakeAdapter
) -> GoogleIntegrationService:
    return GoogleIntegrationService(repository, adapter)


class TestGetAuthorizationUrl:
    def test_returns_url_with_signed_state(self, service: GoogleIntegrationService):
        user_id = uuid4()

        url = service.get_authorization_url(user_id)

        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?state=")


class TestHandleCallback:
    async def test_denied_raises_unauthorized(self, service: GoogleIntegrationService):
        with pytest.raises(UnauthorizedError):
            await service.handle_callback(code=None, state=None, error="access_denied")

    async def test_missing_code_raises_unauthorized(
        self, service: GoogleIntegrationService
    ):
        with pytest.raises(UnauthorizedError):
            await service.handle_callback(code=None, state="some-state", error=None)

    async def test_missing_state_raises_unauthorized(
        self, service: GoogleIntegrationService
    ):
        with pytest.raises(UnauthorizedError):
            await service.handle_callback(code="some-code", state=None, error=None)

    async def test_garbage_state_raises_unauthorized(
        self, service: GoogleIntegrationService
    ):
        with pytest.raises(UnauthorizedError):
            await service.handle_callback(code="some-code", state="garbage", error=None)

    async def test_valid_state_stores_encrypted_tokens(
        self,
        service: GoogleIntegrationService,
        repository: FakeRepository,
    ):
        user_id = uuid4()
        state = create_oauth_state(user_id)

        integration = await service.handle_callback(
            code="auth-code", state=state, error=None
        )

        assert integration.user_id == user_id
        assert integration.access_token_encrypted != "new-access-token"
        assert decrypt(integration.access_token_encrypted) == "new-access-token"
        assert decrypt(integration.refresh_token_encrypted) == "new-refresh-token"
        assert repository.by_user[user_id] is integration

    async def test_exchange_failure_propagates(
        self, service: GoogleIntegrationService, adapter: FakeAdapter
    ):
        adapter.fail_exchange = True
        state = create_oauth_state(uuid4())

        with pytest.raises(ExternalServiceError):
            await service.handle_callback(code="auth-code", state=state, error=None)


class TestGetValidAccessToken:
    async def test_not_found_raises(self, service: GoogleIntegrationService):
        with pytest.raises(NotFoundError):
            await service.get_valid_access_token(uuid4())

    async def test_returns_decrypted_token_when_not_expired(
        self, service: GoogleIntegrationService, repository: FakeRepository
    ):
        user_id = uuid4()
        await repository.upsert(
            user_id=user_id,
            access_token_encrypted=encrypt("still-valid-token"),
            refresh_token_encrypted=encrypt("refresh-token"),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            scopes=_SCOPES,
            connected_at=datetime.now(UTC),
        )

        token = await service.get_valid_access_token(user_id)

        assert token == "still-valid-token"

    async def test_refreshes_when_expired(
        self,
        service: GoogleIntegrationService,
        repository: FakeRepository,
        adapter: FakeAdapter,
    ):
        user_id = uuid4()
        await repository.upsert(
            user_id=user_id,
            access_token_encrypted=encrypt("expired-token"),
            refresh_token_encrypted=encrypt("stored-refresh-token"),
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
            scopes=_SCOPES,
            connected_at=datetime.now(UTC),
        )

        token = await service.get_valid_access_token(user_id)

        assert token == "refreshed-access-token"
        assert adapter.refresh_calls == ["stored-refresh-token"]


class TestRevokeAndDelete:
    async def test_not_found_raises(self, service: GoogleIntegrationService):
        with pytest.raises(NotFoundError):
            await service.revoke_and_delete(uuid4())

    async def test_revokes_and_deletes(
        self,
        service: GoogleIntegrationService,
        repository: FakeRepository,
        adapter: FakeAdapter,
    ):
        user_id = uuid4()
        await repository.upsert(
            user_id=user_id,
            access_token_encrypted=encrypt("access-token"),
            refresh_token_encrypted=encrypt("refresh-token"),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            scopes=_SCOPES,
            connected_at=datetime.now(UTC),
        )

        await service.revoke_and_delete(user_id)

        assert adapter.revoked == ["access-token"]
        assert user_id not in repository.by_user

    async def test_deletes_even_when_revoke_fails(
        self,
        service: GoogleIntegrationService,
        repository: FakeRepository,
        adapter: FakeAdapter,
    ):
        adapter.fail_revoke = True
        user_id = uuid4()
        await repository.upsert(
            user_id=user_id,
            access_token_encrypted=encrypt("access-token"),
            refresh_token_encrypted=encrypt("refresh-token"),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            scopes=_SCOPES,
            connected_at=datetime.now(UTC),
        )

        await service.revoke_and_delete(user_id)

        assert user_id not in repository.by_user
