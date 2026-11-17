"""Maswali ya database yanayohusu akaunti na pochi."""
from datetime import datetime, timedelta, timezone

import db
from config import Config

EAT = timezone(timedelta(hours=3))  # saa za Afrika Mashariki


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


# ===================== Jamvi la mikeka =====================
class TipError(Exception):
    """Kosa la sheria za mkeka; ujumbe unaonyeshwa kwa mtumiaji."""


def to_dt(value):
    """Tarehe kutoka database (datetime au maandishi) -> datetime yenye saa za UTC."""
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def recent_times(table, uid, n):
    """Nyakati za vitu n vya mwisho vya mtumiaji (kwa kuzuia kutuma kupita kiasi)."""
    assert table in ("tips", "comments")
    rows = db.query(
        f"SELECT created_at FROM {table} WHERE user_id = %s ORDER BY created_at DESC, id DESC LIMIT %s",
        (uid, n),
    )
    return [to_dt(r["created_at"]) for r in rows]


_TIP_SELECT = (
    "SELECT t.*, u.username, u.display_name, u.avatar_url, "
    "(SELECT COUNT(*) FROM tip_likes l WHERE l.tip_id = t.id) AS likes, "
    "(SELECT COUNT(*) FROM comments c WHERE c.tip_id = t.id) AS comments, "
    "(SELECT COUNT(*) FROM tip_purchases p WHERE p.tip_id = t.id) AS buyers, "
    "(SELECT COUNT(*) FROM tip_purchases p WHERE p.tip_id = t.id AND p.user_id = %s) AS bought, "
    "(SELECT COUNT(*) FROM tip_likes l WHERE l.tip_id = t.id AND l.user_id = %s) AS liked, "
    "(SELECT COUNT(*) FROM tips x WHERE x.user_id = t.user_id AND x.status = 'won') AS won, "
    "(SELECT COUNT(*) FROM tips x WHERE x.user_id = t.user_id AND x.status = 'lost') AS lost "
    "FROM tips t JOIN users u ON u.id = t.user_id"
)


def _decorate(t, viewer_id):
    """Huongeza sehemu zinazokokotolewa na kuficha mkeka kama mtazamaji hana haki ya kuuona.
    Kila njia inayosoma mikeka inapita hapa, ili mkeka uliofungwa usivuje popote."""
    settled = t["won"] + t["lost"]
    t["win_rate"] = round(100 * t["won"] / settled) if settled else None
    t["is_owner"] = bool(viewer_id) and t["user_id"] == viewer_id
    t["bought"] = bool(t["bought"])
    t["liked"] = bool(t["liked"])
    t["pick_visible"] = (
        t["price"] == 0 or t["status"] in ("won", "lost") or t["bought"] or t["is_owner"]
    )
    if not t["pick_visible"]:
        t["pick"] = None
        t["body"] = None
    start = to_dt(t["starts_at"])
    t["started"] = bool(start and start <= datetime.now(timezone.utc))
    return t


def _tips(where, params, viewer_id, limit, offset=0):
    sql = _TIP_SELECT + (" WHERE " + where if where else "")
    sql += " ORDER BY t.created_at DESC, t.id DESC LIMIT %s OFFSET %s"
    rows = db.query(sql, (viewer_id or 0, viewer_id or 0) + tuple(params) + (limit, offset))
    return [_decorate(r, viewer_id) for r in rows]


def list_tips(viewer_id, status=None, user_id=None, limit=20, offset=0):
    where, params = [], []
    if status:
        where.append("t.status = %s")
        params.append(status)
    if user_id:
        where.append("t.user_id = %s")
        params.append(user_id)
    return _tips(" AND ".join(where), params, viewer_id, limit, offset)


def get_tip(tip_id, viewer_id):
    rows = _tips("t.id = %s", (tip_id,), viewer_id, 1)
    return rows[0] if rows else None


def create_tip(uid, *, title, league, pick, body, odds, price, starts_at):
    row = db.query(
        "INSERT INTO tips (user_id, title, league, pick, body, odds, price, starts_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (uid, title, league, pick, body or None, odds, price, starts_at),
        one=True,
    )
    return row["id"]


def set_tip_status(tip_id, status):
    db.execute("UPDATE tips SET status = %s WHERE id = %s", (status, tip_id))


def delete_tip(tip_id, uid):
    """Mwenye mkeka anaweza kuufuta kama hakuna aliyeununua. Inarudisha True ikifutwa."""
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM tips WHERE id = %s AND user_id = %s "
            "AND NOT EXISTS (SELECT 1 FROM tip_purchases WHERE tip_id = %s)",
            (tip_id, uid, tip_id),
        )
        return cur.rowcount > 0


def toggle_like(tip_id, uid):
    """Inarudisha True kama sasa umependwa, False kama umeondolewa."""
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM tip_likes WHERE tip_id = %s AND user_id = %s", (tip_id, uid))
        if cur.rowcount > 0:
            return False
        cur.execute("INSERT INTO tip_likes (tip_id, user_id) VALUES (%s, %s)", (tip_id, uid))
        return True


def add_comment(tip_id, uid, body):
    db.execute("INSERT INTO comments (tip_id, user_id, body) VALUES (%s, %s, %s)", (tip_id, uid, body))


def list_comments(tip_id, limit=200):
    return db.query(
        "SELECT c.id, c.body, c.created_at, c.user_id, u.username, u.display_name "
        "FROM comments c JOIN users u ON u.id = c.user_id "
        "WHERE c.tip_id = %s ORDER BY c.created_at ASC, c.id ASC LIMIT %s",
        (tip_id, limit),
    )


def get_comment(comment_id):
    return db.query("SELECT * FROM comments WHERE id = %s", (comment_id,), one=True)


def delete_comment(comment_id):
    db.execute("DELETE FROM comments WHERE id = %s", (comment_id,))


def purchase_tip(tip_id, buyer_id, fee_pct):
    """Mnunuzi analipa, muuzaji anapokea (bei toa ada ya jukwaa), yote kwa mkupuo mmoja.
    Inatupa TipError (sheria), InsufficientFunds (salio) au db.IntegrityError (amenunua tayari).
    Hitilafu yoyote inarudisha kila kitu nyuma, hakuna coin zinazopotea."""
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, user_id, title, price, status, starts_at FROM tips WHERE id = %s", (tip_id,))
        tip = cur.fetchone()
        if not tip:
            raise TipError("Mkeka huu haupo.")
        if tip["user_id"] == buyer_id:
            raise TipError("Huwezi kununua mkeka wako mwenyewe.")
        if tip["price"] <= 0:
            raise TipError("Mkeka huu ni wa bure.")
        if tip["status"] != "open":
            raise TipError("Mkeka huu umeshakwisha.")
        start = to_dt(tip["starts_at"])
        if start and start <= datetime.now(timezone.utc):
            raise TipError("Mchezo umeshaanza, huwezi kununua tena.")

        price = tip["price"]
        fee = price * fee_pct // 100
        net = price - fee

        cur.execute("INSERT INTO tip_purchases (tip_id, user_id) VALUES (%s, %s)", (tip_id, buyer_id))
        cur.execute(
            "UPDATE wallets SET balance = balance - %s, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = %s AND balance >= %s RETURNING balance",
            (price, buyer_id, price),
        )
        row = cur.fetchone()
        if row is None:
            raise InsufficientFunds()
        cur.execute(
            "UPDATE wallets SET balance = balance + %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
            (net, tip["user_id"]),
        )
        cur.execute(
            "INSERT INTO transactions (user_id, kind, amount, note) VALUES (%s, 'tip_purchase', %s, %s)",
            (buyer_id, -price, f"Mkeka: {tip['title']}"),
        )
        cur.execute(
            "INSERT INTO transactions (user_id, kind, amount, note) VALUES (%s, 'tip_sale', %s, %s)",
            (tip["user_id"], net, f"Mauzo ya mkeka: {tip['title']}"),
        )
        return {"price": price, "fee": fee, "net": net, "balance": row["balance"]}


def get_user_by_username(username):
    return db.query("SELECT * FROM users WHERE username = %s", (username,), one=True)


def tipster_stats(uid):
    row = db.query(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) AS won, "
        "SUM(CASE WHEN status = 'lost' THEN 1 ELSE 0 END) AS lost "
        "FROM tips WHERE user_id = %s",
        (uid,),
        one=True,
    )
    won, lost = int(row["won"] or 0), int(row["lost"] or 0)
    return {
        "total": int(row["total"] or 0), "won": won, "lost": lost,
        "win_rate": round(100 * won / (won + lost)) if (won + lost) else None,
    }


def leaderboard(min_settled, limit=20):
    rows = db.query(
        "SELECT u.id, u.username, u.display_name, u.avatar_url, "
        "SUM(CASE WHEN t.status = 'won' THEN 1 ELSE 0 END) AS won, "
        "SUM(CASE WHEN t.status = 'lost' THEN 1 ELSE 0 END) AS lost "
        "FROM tips t JOIN users u ON u.id = t.user_id "
        "WHERE t.status IN ('won', 'lost') "
        "GROUP BY u.id, u.username, u.display_name, u.avatar_url "
        "HAVING COUNT(*) >= %s "
        "ORDER BY (SUM(CASE WHEN t.status = 'won' THEN 1 ELSE 0 END) * 1.0 / COUNT(*)) DESC, COUNT(*) DESC, u.id ASC "
        "LIMIT %s",
        (min_settled, limit),
    )
    out = []
    for r in rows:
        won, lost = int(r["won"]), int(r["lost"])
        out.append({**r, "won": won, "lost": lost, "win_rate": round(100 * won / (won + lost))})
    return out
