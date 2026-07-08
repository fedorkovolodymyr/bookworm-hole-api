from fastapi import APIRouter, HTTPException, status

from app.schemas.ai_schemas import (
    RecommendRequest,
    RecommendResponse,
    SummaryRequest,
    SummaryResponse,
    TagSuggestRequest,
    TagSuggestResponse,
)

ai_router = APIRouter(prefix="/ai", tags=["ai"])


@ai_router.post(
    "/summary",
    response_model=SummaryResponse,
    summary="Coming soon",
)
async def generate_summary(body: SummaryRequest) -> SummaryResponse:
    """Generate a summary of the given text.

    Coming soon.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="AI summary feature is not implemented yet",
    )


@ai_router.post(
    "/tag-suggest",
    response_model=TagSuggestResponse,
    summary="Coming soon",
)
async def suggest_tags(body: TagSuggestRequest) -> TagSuggestResponse:
    """Suggest tags for a book.

    Coming soon.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="AI tag suggestion feature is not implemented yet",
    )


@ai_router.post(
    "/recommend",
    response_model=RecommendResponse,
    summary="Coming soon",
)
async def recommend_books(body: RecommendRequest) -> RecommendResponse:
    """Recommend books for a user.

    Coming soon.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="AI recommendation feature is not implemented yet",
    )
