from models import SessionLocal, Movie

def get_movies_by_genre(genre_name: str):
    session = SessionLocal()
    try:
        movies = session.query(Movie).filter(Movie.genre == genre_name).all()
        return movies
    finally:
        session.close()
