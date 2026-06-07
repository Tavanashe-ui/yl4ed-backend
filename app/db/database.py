# app/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Create the SQLAlchemy engine
engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)

# SessionLocal class will be the factory for actual database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class we will use to create our database models
Base = declarative_base()

# Dependency to get a database session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()