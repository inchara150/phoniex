from models import SessionLocal, Movie
from app import get_movies_by_genre

def test_genre_filter():
    session = SessionLocal()
    session.add(Movie(title="Inception", genre="Sci-Fi"))
    session.commit()
    
    results = get_movies_by_genre("Sci-Fi")
    assert len(results) == 1
    assert results[0].title == "Inception"