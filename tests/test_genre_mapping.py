from app.models.catalog import Genre, genre_flags_to_names, genre_names_to_flags
from app.services.genre_mapping import genres_from_categories


class TestGenresFromCategories:
    def test_matches_known_keyword(self):
        assert genres_from_categories(["Fantasy"]) == ["fantasy"]

    def test_matches_multiple_genres_from_one_category(self):
        assert set(genres_from_categories(["Comics & Graphic Novels / Manga"])) == {
            "comics_graphic_novels",
            "manga",
        }

    def test_is_case_insensitive(self):
        assert genres_from_categories(["MANGA"]) == ["manga"]

    def test_unknown_category_yields_no_genres(self):
        assert genres_from_categories(["Some Unrelated Nonsense"]) == []

    def test_empty_input_yields_no_genres(self):
        assert genres_from_categories([]) == []

    def test_deduplicates_across_categories(self):
        result = genres_from_categories(["Manga", "Manga Fiction"])
        assert result.count("manga") == 1


class TestGenreFlagRoundtrip:
    def test_names_to_flags_and_back(self):
        flags = genre_names_to_flags(["manga", "comics_graphic_novels"])

        assert flags == int(Genre.manga | Genre.comics_graphic_novels)
        assert set(genre_flags_to_names(flags)) == {"manga", "comics_graphic_novels"}

    def test_unknown_name_is_ignored(self):
        flags = genre_names_to_flags(["manga", "not_a_real_genre"])

        assert genre_flags_to_names(flags) == ["manga"]

    def test_zero_flags_yields_no_names(self):
        assert genre_flags_to_names(0) == []
