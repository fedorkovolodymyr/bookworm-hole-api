from pydantic import BaseModel


class ExternalSearchHit(BaseModel):
    source: str
    source_id: str
    title: str
    isbns: list[str]
    authors: list[str]
    cover_image_url: str | None


class ExternalSearchResponse(BaseModel):
    query: str
    hits: list[ExternalSearchHit]
    partial_failures: dict[str, str]
