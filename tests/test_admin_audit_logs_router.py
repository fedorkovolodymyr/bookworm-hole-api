from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog, AuditTargetType
from app.models.user import User


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        email="admin@example.com",
        username="admin",
        display_name="Admin User",
        is_admin=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def reader_user(db_session: AsyncSession) -> User:
    user = User(
        email="reader@example.com",
        username="reader",
        display_name="Reader User",
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def audit_logs(db_session: AsyncSession, admin_user: User) -> list[AuditLog]:
    logs = [
        AuditLog(
            actor_id=admin_user.id,
            action=AuditAction.approve_contribution,
            target_type=AuditTargetType.contribution,
            target_id=uuid4(),
            audit_metadata={"old_status": "under_review", "new_status": "approved"},
            ip_address="192.168.1.1",
        ),
        AuditLog(
            actor_id=admin_user.id,
            action=AuditAction.reject_contribution,
            target_type=AuditTargetType.contribution,
            target_id=uuid4(),
            audit_metadata={"reason": "Invalid data"},
            ip_address="192.168.1.2",
        ),
        AuditLog(
            actor_id=admin_user.id,
            action=AuditAction.promote_user,
            target_type=AuditTargetType.user,
            target_id=uuid4(),
            audit_metadata={"old_is_admin": False, "new_is_admin": True},
            ip_address="192.168.1.3",
        ),
    ]
    for log in logs:
        db_session.add(log)
    await db_session.flush()
    return logs


class TestListAuditLogs:
    async def test_list_audit_logs_requires_authentication(
        self,
        async_client: AsyncClient,
    ):
        response = await async_client.get("/api/v1/admin/audit-logs/")
        assert response.status_code == 401

    async def test_list_audit_logs_requires_admin(
        self,
        reader_client: AsyncClient,
    ):
        response = await reader_client.get("/api/v1/admin/audit-logs/")
        assert response.status_code == 403

    async def test_list_audit_logs_success(
        self,
        admin_client: AsyncClient,
        audit_logs: list[AuditLog],
    ):
        response = await admin_client.get("/api/v1/admin/audit-logs/")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        assert len(data["items"]) == 3
        assert data["total"] == 3
        assert data["limit"] == 10
        assert data["offset"] == 0

    async def test_list_audit_logs_pagination(
        self,
        admin_client: AsyncClient,
        audit_logs: list[AuditLog],
    ):
        response = await admin_client.get("/api/v1/admin/audit-logs/?skip=1&limit=2")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3
        assert data["limit"] == 2
        assert data["offset"] == 1

    async def test_list_audit_logs_filter_by_action(
        self,
        admin_client: AsyncClient,
        audit_logs: list[AuditLog],
    ):
        response = await admin_client.get(
            f"/api/v1/admin/audit-logs/?action={AuditAction.approve_contribution.value}"
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["action"] == AuditAction.approve_contribution.value
        assert data["total"] == 1

    async def test_list_audit_logs_filter_by_target_type(
        self,
        admin_client: AsyncClient,
        audit_logs: list[AuditLog],
    ):
        response = await admin_client.get(
            f"/api/v1/admin/audit-logs/?target_type={AuditTargetType.user.value}"
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["target_type"] == AuditTargetType.user.value
        assert data["total"] == 1

    async def test_list_audit_logs_filter_by_actor_id(
        self,
        admin_client: AsyncClient,
        audit_logs: list[AuditLog],
        admin_user: User,
    ):
        response = await admin_client.get(
            f"/api/v1/admin/audit-logs/?actor_id={admin_user.id}"
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 3
        assert all(item["actor_id"] == str(admin_user.id) for item in data["items"])

    async def test_list_audit_logs_empty(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get("/api/v1/admin/audit-logs/")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 0
        assert data["total"] == 0
        assert data["limit"] == 10
        assert data["offset"] == 0

    async def test_list_audit_logs_multiple_filters(
        self,
        admin_client: AsyncClient,
        audit_logs: list[AuditLog],
    ):
        response = await admin_client.get(
            f"/api/v1/admin/audit-logs/?action={AuditAction.approve_contribution.value}&target_type={AuditTargetType.contribution.value}"
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["action"] == AuditAction.approve_contribution.value
        assert data["items"][0]["target_type"] == AuditTargetType.contribution.value
        assert data["total"] == 1
