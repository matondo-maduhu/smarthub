"""Maswali ya database yanayohusu akaunti na pochi."""
import db
from config import Config


def get_user(uid):
    return db.query(
        "SELECT u.*, COALESCE(w.balance, 0) AS balance "
        "FROM users u LEFT JOIN wallets w ON w.user_id = u.id "
        "WHERE u.id = %s",
        (uid,),
        one=True,
    )


def find_user_by_email(email):
    return db.query("SELECT * FROM users WHERE email = %s", (email,), one=True)


def find_user_by_phone(phone):
    return db.query("SELECT * FROM users WHERE phone = %s", (phone,), one=True)


def find_user_by_google(google_id):
    return db.query("SELECT * FROM users WHERE google_id = %s", (google_id,), one=True)


def username_exists(username):
    return db.query("SELECT 1 AS x FROM users WHERE username = %s", (username,), one=True) is not None


def create_user(*, username, display_name, birth_date, email=None, phone=None,
                google_id=None, password_hash=None, avatar_url=None, is_verified=False):
    """Hutengeneza mtumiaji, pochi yake na zawadi ya kujiunga kwa mkupuo mmoja.
    Inatupa db.IntegrityError kama barua pepe, simu au jina la mtumiaji limetumika."""
    bonus = Config.SIGNUP_BONUS
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, display_name, email, phone, google_id, "
            "password_hash, avatar_url, birth_date, is_verified, age_confirmed_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP) RETURNING id",
            (username, display_name, email, phone, google_id, password_hash,
             avatar_url, birth_date, is_verified),
        )
        uid = cur.fetchone()["id"]
        cur.execute("INSERT INTO wallets (user_id, balance) VALUES (%s, %s)", (uid, bonus))
        if bonus > 0:
            cur.execute(
                "INSERT INTO transactions (user_id, kind, amount, note) VALUES (%s, 'bonus', %s, %s)",
                (uid, bonus, "Zawadi ya kujiunga"),
            )
    return uid


class InsufficientFunds(Exception):
    pass


def wallet_change(uid, delta, kind, note, status="done", idem_key=None):
    """Hubadilisha salio na kuandika muamala kwa mkupuo mmoja (yote au hakuna).

    - Salio haliwezi kushuka chini ya sifuri: InsufficientFunds.
    - idem_key ikirudiwa, db.IntegrityError inatupwa na mabadiliko yote yanarudishwa nyuma.
    Inarudisha salio jipya."""
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE wallets SET balance = balance + %s, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = %s AND balance + %s >= 0 RETURNING balance",
            (delta, uid, delta),
        )
        row = cur.fetchone()
        if row is None:
            raise InsufficientFunds()
        cur.execute(
            "INSERT INTO transactions (user_id, kind, amount, note, status, idem_key) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (uid, kind, delta, note, status, idem_key),
        )
        return row["balance"]


def update_display_name(uid, name):
    db.execute("UPDATE users SET display_name = %s WHERE id = %s", (name, uid))


def update_avatar(uid, url):
    db.execute("UPDATE users SET avatar_url = %s WHERE id = %s", (url, uid))


def get_transactions(uid, limit=50):
    return db.query(
        "SELECT kind, amount, note, status, created_at FROM transactions "
        "WHERE user_id = %s ORDER BY created_at DESC, id DESC LIMIT %s",
        (uid, limit),
    )
