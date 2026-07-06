from typing import Any

NOT_FOUND_RESPONSE: dict[int | str, dict[str, Any]] = {
    404: {"description": "Resource not found"},
}

ADMIN_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Missing or invalid credentials"},
    403: {"description": "Admin privileges required"},
}

CONFLICT_RESPONSE: dict[int | str, dict[str, Any]] = {
    409: {"description": "Request conflicts with the current state of the resource"},
}
