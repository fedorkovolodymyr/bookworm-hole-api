from collections.abc import Callable

from app.core.errors import NotFoundError
from app.services.external.base import BookSourceAdapter

_registry: dict[str, type[BookSourceAdapter]] = {}


class AdapterNotFoundError(NotFoundError):
    def __init__(self, name: str) -> None:
        super().__init__(f"No adapter registered for '{name}'")
        self.name = name


def register_adapter(
    name: str,
) -> Callable[[type[BookSourceAdapter]], type[BookSourceAdapter]]:
    def decorator(cls: type[BookSourceAdapter]) -> type[BookSourceAdapter]:
        _registry[name] = cls
        return cls

    return decorator


def get_adapter(name: str) -> BookSourceAdapter:
    try:
        adapter_cls = _registry[name]
    except KeyError:
        raise AdapterNotFoundError(name) from None
    return adapter_cls()
