import os

class Config:
    # Use DATABASE_URL from environment if set, otherwise fallback to SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///mydatabase.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SECRET_KEY is used for session security
    SECRET_KEY = os.environ.get("SECRET_KEY", "your_default_secret_key")
