import os
from pathlib import Path

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "static" / "images"


# Determine environment
FLASK_ENV = os.environ.get("FLASK_ENV", "")
IS_PRODUCTION = FLASK_ENV.lower() == "production"


class Config:
    # No default secret key allowed — must be provided via environment
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DATABASE = os.environ.get(
        "DATABASE", str(BASE_DIR / "database" / "database.db")
    )
    UPLOAD_FOLDER = str(UPLOAD_FOLDER)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ENV = "production" if IS_PRODUCTION else "development"
    DEBUG = not IS_PRODUCTION
    PREFERRED_URL_SCHEME = "https" if IS_PRODUCTION else "http"
    WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "212622135964")
    FACEBOOK_URL = os.environ.get("FACEBOOK_URL", "https://www.facebook.com/")
    INSTAGRAM_URL = os.environ.get("INSTAGRAM_URL", "https://www.instagram.com/")
    SHOP_NAME = os.environ.get("SHOP_NAME", "MERCA FRUIT SEC")
    SHOP_ADDRESS = os.environ.get(
        "SHOP_ADDRESS",
        "Doha Avenue Moulay Youssef, Salé, face École Nassiri",
    )
    SESSION_COOKIE_HTTPONLY = True
    # Only mark cookies as secure when running in production (HTTPS)
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    SESSION_COOKIE_SAMESITE = "Lax"
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    # No default admin password hash allowed — must be provided via environment
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")


# Enforce presence of critical secrets without defaults
if not Config.SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is required and must not be empty."
    )

if not Config.ADMIN_PASSWORD_HASH:
    raise RuntimeError(
        "ADMIN_PASSWORD_HASH environment variable is required and must not be empty."
    )
