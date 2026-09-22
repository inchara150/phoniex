from models import SessionLocal, Movie

def get_movies_by_genre(genre_name: str):
    session = SessionLocal()
    try:
        # Re-introduce the bug so the agent has something to fix
        movies = session.query(Movie).filter(Movie.genre.is_(genre_name)).all()
        return movies
    finally:
        session.close()