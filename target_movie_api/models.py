from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
engine = create_engine('sqlite:///:memory:')
SessionLocal = sessionmaker(bind=engine)

class Movie(Base):
    __tablename__ = 'movies'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    genre = Column(String, nullable=False)

Base.metadata.create_all(engine)