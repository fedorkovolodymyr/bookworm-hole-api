from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogImportQuery:
    text: str
    sources: list[str] | None = None


@dataclass(frozen=True)
class CatalogImportProfile:
    name: str
    target_count: int
    queries: list[CatalogImportQuery]


# Subject terms understood by Google Books' `subject:` search operator.
# Kept broad and diverse so the "books" profile isn't skewed to one genre.
_BOOK_SUBJECTS = [
    "Fiction",
    "Science Fiction",
    "Fantasy",
    "Mystery",
    "Romance",
    "Thriller",
    "Historical Fiction",
    "Horror",
    "Classics",
    "Young Adult Fiction",
    "Biography & Autobiography",
    "History",
    "Philosophy",
    "Psychology",
    "Self-Help",
    "Business & Economics",
    "Science",
    "Poetry",
    "Travel",
    "Cooking",
    "Art",
    "Religion",
    "True Crime",
    "Adventure",
    "Drama",
    "Music",
    "Nature",
    "Sports & Recreation",
    "Computers",
    "Education",
]

CATALOG_IMPORT_PROFILES: dict[str, CatalogImportProfile] = {
    "books": CatalogImportProfile(
        name="books",
        target_count=1000,
        queries=[
            CatalogImportQuery(text=f"subject:{subject}") for subject in _BOOK_SUBJECTS
        ],
    ),
    "comics": CatalogImportProfile(
        name="comics",
        target_count=100,
        queries=[
            CatalogImportQuery(text="subject:Comics & Graphic Novels"),
            CatalogImportQuery(text="subject:Comics"),
            CatalogImportQuery(text="subject:Graphic Novels"),
            CatalogImportQuery(text="subject:Superheroes"),
        ],
    ),
    "manga": CatalogImportProfile(
        name="manga",
        target_count=100,
        queries=[
            CatalogImportQuery(text="subject:Manga"),
            CatalogImportQuery(text="subject:Comics & Graphic Novels Manga"),
            CatalogImportQuery(text="subject:Manga Fiction"),
        ],
    ),
}
