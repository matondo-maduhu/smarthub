import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    APP_NAME = os.getenv("APP_NAME", "Jamvi")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")

    # Neon (Postgres)
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    # Cloudflare R2
    R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET = os.getenv("R2_BUCKET", "")
    R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "").rstrip("/")

    # demo = coin bandia. Malipo halisi yanaongezwa hatua ya 8, baada ya leseni.
    COIN_MODE = os.getenv("COIN_MODE", "demo")

    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB kwa kila upakiaji
