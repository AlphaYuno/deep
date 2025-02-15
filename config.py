import os

class Config:
    # Use an environment variable for the database URL, default to SQLite if not set.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///mydatabase.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "your_default_secret_key")
