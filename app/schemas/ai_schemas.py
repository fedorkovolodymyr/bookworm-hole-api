from pydantic import BaseModel, Field


class SummaryRequest(BaseModel):
    text: str = Field(..., description="Text to summarize")


class SummaryResponse(BaseModel):
    summary: str = Field(..., description="Generated summary")


class TagSuggestRequest(BaseModel):
    book_id: str = Field(..., description="Book ID to suggest tags for")


class TagSuggestResponse(BaseModel):
    tags: list[str] = Field(..., description="Suggested tags")


class RecommendRequest(BaseModel):
    user_id: str = Field(..., description="User ID to generate recommendations for")
    n: int = Field(default=10, description="Number of recommendations", ge=1, le=100)


class RecommendResponse(BaseModel):
    book_ids: list[str] = Field(..., description="Recommended book IDs")
