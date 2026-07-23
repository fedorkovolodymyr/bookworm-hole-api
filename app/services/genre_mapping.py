from app.models.catalog import Genre

# Free-text category/subject strings from external sources (Google Books
# `volumeInfo.categories`, Open Library `subjects`) matched by substring —
# best-effort, since neither source has a controlled vocabulary.
_GENRE_KEYWORDS: dict[Genre, tuple[str, ...]] = {
    Genre.manga: ("manga",),
    Genre.comics_graphic_novels: ("comic", "graphic novel"),
    Genre.science_fiction: ("science fiction", "sci-fi"),
    Genre.fantasy: ("fantasy",),
    Genre.mystery_thriller: ("mystery", "thriller", "detective"),
    Genre.romance: ("romance",),
    Genre.horror: ("horror",),
    Genre.historical_fiction: ("historical fiction",),
    Genre.classics: ("classics",),
    Genre.young_adult: ("young adult", "juvenile fiction", "juvenile nonfiction"),
    Genre.biography_memoir: ("biography", "autobiography", "memoir"),
    Genre.history: ("history",),
    Genre.philosophy: ("philosophy",),
    Genre.psychology: ("psychology",),
    Genre.self_help: ("self-help", "self help"),
    Genre.business_economics: ("business", "economics"),
    Genre.science: ("science",),
    Genre.poetry: ("poetry",),
    Genre.true_crime: ("true crime",),
    Genre.religion: ("religion",),
    Genre.travel: ("travel",),
    Genre.cooking: ("cooking", "cookery"),
    Genre.art: ("art",),
    Genre.fiction: ("fiction",),
}


def genres_from_categories(categories: list[str]) -> list[str]:
    found: set[Genre] = set()
    for category in categories:
        lowered = category.lower()
        for genre, keywords in _GENRE_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                found.add(genre)
    return [genre.name for genre in found if genre.name]
