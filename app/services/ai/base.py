from abc import ABC, abstractmethod
from uuid import UUID

from app.models.catalog import Book


class AIProvider(ABC):
    """Extension point for AI features.

    Implementations provide various AI-powered capabilities. Default
    implementation is NoOpAIProvider (all methods return empty/default values).
    """

    @abstractmethod
    def generate_summary(self, text: str) -> str:
        """Generate a summary of the given text.

        Args:
            text: Text to summarize.

        Returns:
            Summary text.
        """
        raise NotImplementedError

    @abstractmethod
    def suggest_tags(self, book: Book) -> list[str]:
        """Suggest tags for a book based on its metadata.

        Args:
            book: Book to suggest tags for.

        Returns:
            List of suggested tag strings.
        """
        raise NotImplementedError

    @abstractmethod
    def recommend(self, user_id: UUID, n: int) -> list[UUID]:
        """Recommend book IDs for a user.

        Args:
            user_id: User to generate recommendations for.
            n: Number of recommendations to return.

        Returns:
            List of recommended book IDs.
        """
        raise NotImplementedError
