from typing import Literal

from pydantic import BaseModel

CatalogImportProfileName = Literal["books", "comics", "manga"]


class CatalogImportRequest(BaseModel):
    profile: CatalogImportProfileName


class CatalogImportJobResponse(BaseModel):
    job_id: str


class CatalogImportJobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict[str, int] | None = None
