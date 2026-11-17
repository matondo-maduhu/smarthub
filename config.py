import os
from datetime import timedelta

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

    # Kuingia kwa Google (hiari). Acha wazi kama hujaiweka.
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

    # Thamani ya coin 1 kwa shilingi ya Tanzania, na kiwango cha chini cha kutoa
    COIN_RATE_TZS = int(os.getenv("COIN_RATE_TZS", "100"))
    MIN_WITHDRAW = int(os.getenv("MIN_WITHDRAW", "50"))

    # Jamvi la mikeka
    TIP_FEE_PCT = int(os.getenv("TIP_FEE_PCT", "10"))              # ada ya jukwaa kwa kila mauzo (%)
    TIP_MAX_PRICE = int(os.getenv("TIP_MAX_PRICE", "1000"))        # bei ya juu ya mkeka (coin)
    MAX_TIPS_PER_DAY = int(os.getenv("MAX_TIPS_PER_DAY", "10"))    # mikeka kwa mtumiaji kwa siku
    MIN_SETTLED_FOR_RANK = int(os.getenv("MIN_SETTLED_FOR_RANK", "5"))  # mikeka iliyokwisha ili aingie viwango
    TIPS_PER_PAGE = 20

    # Zawadi ya kujiunga (coin bandia) hutolewa hali ya demo tu
    SIGNUP_BONUS = int(os.getenv("SIGNUP_BONUS", "100")) if COIN_MODE == "demo" else 0

    # Vidakuzi vya kikao
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "1") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    # 1 = app iko nyuma ya proxy ya hosting (Render, Railway, Nginx...)
    TRUST_PROXY = os.getenv("TRUST_PROXY", "1") == "1"
