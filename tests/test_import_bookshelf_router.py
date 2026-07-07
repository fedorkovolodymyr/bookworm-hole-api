import io

from fastapi import status
from httpx import AsyncClient

from app.models.user import User


def _login_as(user: User) -> dict[str, str]:
    from app.services.security import encode_jwt

    token = encode_jwt({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


class TestImportBookshelfRouter:
    async def test_import_requires_auth(self, async_client: AsyncClient):
        csv_content = b"title,author,isbn,status,date_added\nTest,Author,,owned,"
        files = {"file": ("test.csv", io.BytesIO(csv_content))}
        response = await async_client.post(
            "/api/v1/users/me/import/bookshelf", files=files
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_import_empty_csv(self, admin_client: AsyncClient):
        csv_content = b"title,author,isbn,status,date_added\n"
        files = {"file": ("test.csv", io.BytesIO(csv_content))}

        response = await admin_client.post(
            "/api/v1/users/me/import/bookshelf", files=files
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
