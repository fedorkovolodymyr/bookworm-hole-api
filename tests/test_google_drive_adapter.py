import httplib2
import pytest
from googleapiclient.errors import HttpError

from app.core.errors import ExternalServiceError
from app.services.external import google_drive


class FakeExecutable:
    def __init__(
        self, result: dict | None = None, exc: Exception | None = None
    ) -> None:
        self._result = result
        self._exc = exc

    def execute(self) -> dict:
        if self._exc is not None:
            raise self._exc
        assert self._result is not None
        return self._result


class FakeFilesResource:
    def __init__(
        self,
        existing_folders: list[dict] | None = None,
        create_result: dict | None = None,
        list_exc: Exception | None = None,
        create_exc: Exception | None = None,
        media_content: bytes | None = None,
        get_media_exc: Exception | None = None,
    ) -> None:
        self.existing_folders = existing_folders or []
        self.create_result = (
            create_result if create_result is not None else {"id": "new-id"}
        )
        self.list_exc = list_exc
        self.create_exc = create_exc
        self.media_content = media_content
        self.get_media_exc = get_media_exc
        self.list_calls: list[dict] = []
        self.create_calls: list[dict] = []
        self.get_media_calls: list[dict] = []

    def list(self, **kwargs) -> FakeExecutable:
        self.list_calls.append(kwargs)
        if self.list_exc is not None:
            return FakeExecutable(exc=self.list_exc)
        return FakeExecutable({"files": self.existing_folders})

    def create(self, **kwargs) -> FakeExecutable:
        self.create_calls.append(kwargs)
        if self.create_exc is not None:
            return FakeExecutable(exc=self.create_exc)
        return FakeExecutable(self.create_result)

    def get_media(self, **kwargs) -> FakeExecutable:
        self.get_media_calls.append(kwargs)
        if self.get_media_exc is not None:
            return FakeExecutable(exc=self.get_media_exc)
        return FakeExecutable(self.media_content)


class FakeDriveService:
    def __init__(self, files_resource: FakeFilesResource) -> None:
        self._files = files_resource

    def files(self) -> FakeFilesResource:
        return self._files


def _http_error() -> HttpError:
    return HttpError(resp=httplib2.Response({"status": 500}), content=b"boom")


class TestFindOrCreateFolder:
    async def test_returns_existing_folder_id_without_creating(self, monkeypatch):
        files = FakeFilesResource(existing_folders=[{"id": "existing-id"}])
        monkeypatch.setattr(
            google_drive.googleapiclient.discovery,
            "build",
            lambda *a, **kw: FakeDriveService(files),
        )
        adapter = google_drive.GoogleDriveAdapter()

        folder_id = await adapter.find_or_create_folder("token", "HomeLibraryBackups")

        assert folder_id == "existing-id"
        assert len(files.create_calls) == 0

    async def test_creates_folder_when_missing(self, monkeypatch):
        files = FakeFilesResource(
            existing_folders=[], create_result={"id": "created-id"}
        )
        monkeypatch.setattr(
            google_drive.googleapiclient.discovery,
            "build",
            lambda *a, **kw: FakeDriveService(files),
        )
        adapter = google_drive.GoogleDriveAdapter()

        folder_id = await adapter.find_or_create_folder("token", "HomeLibraryBackups")

        assert folder_id == "created-id"
        assert len(files.create_calls) == 1

    async def test_raises_external_service_error_on_list_failure(self, monkeypatch):
        files = FakeFilesResource(list_exc=_http_error())
        monkeypatch.setattr(
            google_drive.googleapiclient.discovery,
            "build",
            lambda *a, **kw: FakeDriveService(files),
        )
        adapter = google_drive.GoogleDriveAdapter()

        with pytest.raises(ExternalServiceError):
            await adapter.find_or_create_folder("token", "HomeLibraryBackups")

    async def test_raises_external_service_error_when_create_missing_id(
        self, monkeypatch
    ):
        files = FakeFilesResource(existing_folders=[], create_result={})
        monkeypatch.setattr(
            google_drive.googleapiclient.discovery,
            "build",
            lambda *a, **kw: FakeDriveService(files),
        )
        adapter = google_drive.GoogleDriveAdapter()

        with pytest.raises(ExternalServiceError):
            await adapter.find_or_create_folder("token", "HomeLibraryBackups")


class TestUploadFile:
    async def test_returns_file_id(self, monkeypatch):
        files = FakeFilesResource(create_result={"id": "uploaded-id"})
        monkeypatch.setattr(
            google_drive.googleapiclient.discovery,
            "build",
            lambda *a, **kw: FakeDriveService(files),
        )
        adapter = google_drive.GoogleDriveAdapter()

        file_id = await adapter.upload_file(
            "token", "folder-id", "homelibrary-backup-x.json", b"{}"
        )

        assert file_id == "uploaded-id"
        assert files.create_calls[0]["body"] == {
            "name": "homelibrary-backup-x.json",
            "parents": ["folder-id"],
        }

    async def test_raises_external_service_error_on_upload_failure(self, monkeypatch):
        files = FakeFilesResource(create_exc=_http_error())
        monkeypatch.setattr(
            google_drive.googleapiclient.discovery,
            "build",
            lambda *a, **kw: FakeDriveService(files),
        )
        adapter = google_drive.GoogleDriveAdapter()

        with pytest.raises(ExternalServiceError):
            await adapter.upload_file("token", "folder-id", "backup.json", b"{}")

    async def test_raises_external_service_error_when_missing_id(self, monkeypatch):
        files = FakeFilesResource(create_result={})
        monkeypatch.setattr(
            google_drive.googleapiclient.discovery,
            "build",
            lambda *a, **kw: FakeDriveService(files),
        )
        adapter = google_drive.GoogleDriveAdapter()

        with pytest.raises(ExternalServiceError):
            await adapter.upload_file("token", "folder-id", "backup.json", b"{}")


class TestDownloadFile:
    async def test_returns_file_bytes(self, monkeypatch):
        files = FakeFilesResource(media_content=b'{"export_version": 1}')
        monkeypatch.setattr(
            google_drive.googleapiclient.discovery,
            "build",
            lambda *a, **kw: FakeDriveService(files),
        )
        adapter = google_drive.GoogleDriveAdapter()

        content = await adapter.download_file("token", "file-id")

        assert content == b'{"export_version": 1}'
        assert files.get_media_calls == [{"fileId": "file-id"}]

    async def test_raises_external_service_error_on_download_failure(self, monkeypatch):
        files = FakeFilesResource(get_media_exc=_http_error())
        monkeypatch.setattr(
            google_drive.googleapiclient.discovery,
            "build",
            lambda *a, **kw: FakeDriveService(files),
        )
        adapter = google_drive.GoogleDriveAdapter()

        with pytest.raises(ExternalServiceError):
            await adapter.download_file("token", "file-id")
