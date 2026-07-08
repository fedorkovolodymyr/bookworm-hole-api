from uuid import UUID

from app.models.catalog import Book
from app.services.ai.base import AIProvider


class NoOpAIProvider(AIProvider):
    """No-op AI provider. All methods return empty/default values."""

    def generate_summary(self, text: str) -> str:
        """Return empty string."""
        return ""

    def suggest_tags(self, book: Book) -> list[str]:
        """Return empty list."""
        return []

    def recommend(self, user_id: UUID, n: int) -> list[UUID]:
        """Return empty list."""
        return []
