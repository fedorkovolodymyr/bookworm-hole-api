from __future__ import annotations

import asyncio
import io
from typing import TYPE_CHECKING

import googleapiclient.discovery
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from app.core.errors import ErrorMessages, ExternalServiceError

if TYPE_CHECKING:
    # googleapiclient._apis is a type-stub-only namespace (no runtime module),
    # provided by the google-api-python-client-stubs dev dependency.
    from googleapiclient._apis.drive.v3 import DriveResource

_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
_JSON_MIME_TYPE = "application/json"


def _build_drive_service(access_token: str) -> DriveResource:
    """Isolates googleapiclient.discovery.build's untyped overload set behind
    a signature pinned to the Drive v3 resource we actually use."""
    return googleapiclient.discovery.build(
        "drive",
        "v3",
        credentials=Credentials(token=access_token),
        cache_discovery=False,
    )


class GoogleDriveAdapter:
    """Thin adapter around google-api-python-client's Drive v3 API.

    Access tokens are used only transiently in-memory to build per-call
    credentials; never persisted or logged. googleapiclient is sync, so
    calls run in a worker thread to avoid blocking the event loop.
    """

    async def find_or_create_folder(self, access_token: str, folder_name: str) -> str:
        return await asyncio.to_thread(
            self._find_or_create_folder_sync, access_token, folder_name
        )

    async def upload_file(
        self, access_token: str, folder_id: str, filename: str, content: bytes
    ) -> str:
        return await asyncio.to_thread(
            self._upload_file_sync, access_token, folder_id, filename, content
        )

    def _find_or_create_folder_sync(self, access_token: str, folder_name: str) -> str:
        service = _build_drive_service(access_token)
        escaped_name = folder_name.replace("\\", "\\\\").replace("'", "\\'")
        query = (
            f"name = '{escaped_name}' and mimeType = '{_FOLDER_MIME_TYPE}' "
            "and trashed = false"
        )
        try:
            response = (
                service.files()
                .list(q=query, spaces="drive", fields="files(id)")
                .execute()
            )
            existing = response.get("files", [])
            if existing:
                folder_id = existing[0].get("id")
                if folder_id:
                    return folder_id

            folder = (
                service.files()
                .create(
                    body={"name": folder_name, "mimeType": _FOLDER_MIME_TYPE},
                    fields="id",
                )
                .execute()
            )
        except HttpError as exc:
            raise ExternalServiceError(
                ErrorMessages.GOOGLE_DRIVE_REQUEST_FAILED
            ) from exc

        folder_id = folder.get("id")
        if not folder_id:
            raise ExternalServiceError(ErrorMessages.GOOGLE_DRIVE_REQUEST_FAILED)
        return folder_id

    def _upload_file_sync(
        self, access_token: str, folder_id: str, filename: str, content: bytes
    ) -> str:
        service = _build_drive_service(access_token)
        media = MediaIoBaseUpload(
            io.BytesIO(content), mimetype=_JSON_MIME_TYPE, resumable=True
        )
        try:
            file = (
                service.files()
                .create(
                    body={"name": filename, "parents": [folder_id]},
                    media_body=media,
                    fields="id",
                )
                .execute()
            )
        except HttpError as exc:
            raise ExternalServiceError(
                ErrorMessages.GOOGLE_DRIVE_REQUEST_FAILED
            ) from exc

        file_id = file.get("id")
        if not file_id:
            raise ExternalServiceError(ErrorMessages.GOOGLE_DRIVE_REQUEST_FAILED)
        return file_id
