from app import get_movie_title

def test_missing_title_fallback():
    # Should safely return a fallback string or None instead of throwing KeyError
    result = get_movie_title({})
    assert result == "Untitled" or result is None