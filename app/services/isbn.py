from stdnum import isbn as stdnum_isbn
from stdnum.exceptions import ValidationError


def is_valid_isbn(raw: str) -> bool:
    return stdnum_isbn.is_valid(raw)


def normalize_isbn(raw: str) -> str:
    """Normalize ISBN-10/13 to a hyphen-free ISBN-13 string.

    Raises ValueError for non-ISBN input (e.g. ASIN) — callers must route
    those to ISBN.kind=other and store code_original/code_normalized as-is.
    """
    try:
        stdnum_isbn.validate(raw)
        return stdnum_isbn.compact(stdnum_isbn.to_isbn13(raw))
    except ValidationError as exc:
        raise ValueError(f"Invalid ISBN: {raw!r}") from exc
