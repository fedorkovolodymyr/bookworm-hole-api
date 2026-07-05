class AppError(Exception):
    """Base for domain errors translated to HTTP responses by app.main's exception handler."""

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


class ErrorMessages:
    SOURCE_BOOK_NOT_FOUND = "Source book not found"
    EXTERNAL_LOOKUP_FAILED = "External source lookup failed"
    COLLECTION_NOT_FOUND = "Collection not found"
    COLLECTION_ITEM_NOT_FOUND = "Collection item not found"
    REORDER_INVALID_ITEM_IDS = (
        "item_ids must match the collection's existing items exactly"
    )
