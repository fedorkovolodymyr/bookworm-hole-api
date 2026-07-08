from dataclasses import dataclass
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.account_deletion_repository import AccountDeletionRepository
from app.repositories.user_repository import UserRepository


@dataclass
class PurgeSummary:
    purged: int = 0


class AccountDeletionService:
    def __init__(
        self,
        user_repository: UserRepository,
        account_deletion_repository: AccountDeletionRepository,
    ) -> None:
        self.user_repository = user_repository
        self.account_deletion_repository = account_deletion_repository

    async def purge_deleted_users(self) -> PurgeSummary:
        """Hard-delete every account past its `deletion_scheduled_at` grace period.

        Data retention model applied per purged user:
        - Anonymized, not deleted: `Review` rows — `user_id` is set to NULL so
          the review body/rating stay visible on the book/release page as a
          "deleted user" review, preserving thread integrity.
        - Detached, not deleted: `BookStatus.lent_to_user_id` and
          `Contribution.reviewer_id` on *other* users' rows are nulled so
          those records survive without a dangling reference.
        - Hard-deleted: the user's own `ReadingSession`, `BookStatus`,
          `Collection` (and its `CollectionItem`s, via DB cascade),
          `Friendship`, and `Contribution` rows, plus the `User` row itself
          and its `RefreshToken`s (DB `ondelete=CASCADE`) — none of this has
          value once its owner is gone.
        - TODO: anonymize `ChatMessage.sender_id` once the chat feature lands.
        """
        cutoff = datetime.now(UTC)
        pending = await self.user_repository.get_users_pending_purge(cutoff)
        purged = 0
        for user in pending:
            # Isolate failures per user: one bad row shouldn't abort the whole
            # run, and rolling back keeps the session usable for the next one.
            try:
                await self.account_deletion_repository.purge_user_data(user.id)
                await self.account_deletion_repository.delete_user(user.id)
                purged += 1
            except SQLAlchemyError:
                await self.account_deletion_repository.session.rollback()
                logger.exception(f"Failed to purge user {user.id}")
        return PurgeSummary(purged=purged)
