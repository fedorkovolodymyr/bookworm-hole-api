class AppError(Exception):
    """Base for domain errors.

    Translated to HTTP responses by app.main's exception handler.
    """

    status_code: int = 500

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class UnauthorizedError(AppError):
    status_code = 401


class ExternalServiceError(AppError):
    status_code = 502


class BadRequestError(AppError):
    status_code = 400


class ServiceUnavailableError(AppError):
    status_code = 503


class ErrorMessages:
    SOURCE_BOOK_NOT_FOUND = "Source book not found"
    EXTERNAL_LOOKUP_FAILED = "External source lookup failed"
    COLLECTION_NOT_FOUND = "Collection not found"
    COLLECTION_ITEM_NOT_FOUND = "Collection item not found"
    REORDER_INVALID_ITEM_IDS = (
        "item_ids must match the collection's existing items exactly"
    )
    REVIEW_NOT_FOUND = "Review not found"
    REVIEW_ALREADY_EXISTS = "You already reviewed this book or release"
    USER_NOT_FOUND = "User not found"
    SELF_FRIEND_REQUEST_NOT_ALLOWED = "You cannot send a friend request to yourself"
    FRIEND_REQUEST_ALREADY_EXISTS = (
        "A friend request already exists between these users"
    )
    ALREADY_FRIENDS = "You are already friends with this user"
    FRIENDSHIP_NOT_FOUND = "Friendship not found"
    FRIEND_REQUEST_NOT_FOUND = "Friend request not found"
    USER_BLOCKED = "This action is not allowed"
    CANNOT_BLOCK_SELF = "You cannot block yourself"
    CONTRIBUTOR_NOT_FOUND = "Contributor not found"
    INVALID_CURRENT_PASSWORD = "Current password is incorrect"
    BOOK_NOT_FOUND = "Book not found"
    RELEASE_NOT_FOUND = "Release not found"
    CANNOT_MERGE_BOOK_INTO_ITSELF = "Cannot merge a book into itself"
    CONTRIBUTION_NOT_FOUND = "Contribution not found"
    CONTRIBUTION_NOT_DRAFT = "Contribution must be in draft state to edit"
    CONTRIBUTION_CANNOT_DELETE = (
        "Contribution can only be deleted while in draft or submitted state"
    )
    CONTRIBUTION_NOT_SUBMITTED = "Contribution must be in submitted state"
    CONTRIBUTION_NOT_UNDER_REVIEW = "Contribution must be under review"
    READING_SESSION_NOT_FOUND = "Reading session not found"
    READING_SESSION_ALREADY_ACTIVE = "Reading session already active for this release"
    READING_SESSION_NOT_ACTIVE = "No active reading session for this release"
