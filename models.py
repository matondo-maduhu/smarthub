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


class ProfileError(Exception):
    pass


def _one_line(text, limit, what):
    text = " ".join((text or "").split())
    if len(text) > limit:
        raise ProfileError(f"{what} lisizidi herufi {limit}.")
    return text


def update_profile(uid, display_name, bio, location, avatar_url=None, drop_avatar=False):
    name = _one_line(display_name, 40, "Jina")
    if len(name) < 2:
        raise ProfileError("Jina liwe na herufi 2 hadi 40.")
    bio = _one_line(bio, 160, "Maelezo yako")
    location = _one_line(location, 40, "Mahali")
    if avatar_url:
        db.execute("UPDATE users SET display_name = %s, bio = %s, location = %s, avatar_url = %s WHERE id = %s",
                   (name, bio, location, avatar_url, uid))
    elif drop_avatar:
        db.execute("UPDATE users SET display_name = %s, bio = %s, location = %s, avatar_url = NULL WHERE id = %s",
                   (name, bio, location, uid))
    else:
        db.execute("UPDATE users SET display_name = %s, bio = %s, location = %s WHERE id = %s",
                   (name, bio, location, uid))


def set_allow_messages(uid, allow):
    db.execute("UPDATE users SET allow_messages = %s WHERE id = %s", (bool(allow), uid))


def list_blocked(uid):
    return db.query("SELECT u.id, u.username, u.display_name, u.avatar_url FROM blocks b "
                    "JOIN users u ON u.id = b.blocked_id WHERE b.blocker_id = %s ORDER BY b.created_at DESC", (uid,))


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
    col = {"tips": "user_id", "comments": "user_id", "products": "seller_id",
           "messages": "sender_id"}[table]
    rows = db.query(
        f"SELECT created_at FROM {table} WHERE {col} = %s ORDER BY created_at DESC, id DESC LIMIT %s",
        (uid, n),
    )
    return [to_dt(r["created_at"]) for r in rows]


def notify(cur, user_id, kind, text, url=None):
    """Huandika arifa ndani ya transaction iliyopo (rollback ikitokea, arifa pia inaondoka)."""
    cur.execute("INSERT INTO notifications (user_id, kind, text, url) VALUES (%s, %s, %s, %s)",
                (user_id, kind, text[:200], url))


def notify_safe(user_id, kind, text, url=None):
    """Arifa nje ya transaction: hitilafu ya arifa isivuruge kitendo kikuu."""
    try:
        with db.get_conn() as conn, conn.cursor() as cur:
            notify(cur, user_id, kind, text, url)
    except Exception:
        pass


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
    now = datetime.now(timezone.utc)
    t["started"] = bool(start and start <= now)
    # Mkeka unafungwa kiotomatiki dakika chache kabla ya mechi ya kwanza ili usinunuliwe ukiwa umepitwa na wakati
    lock_at = start - timedelta(minutes=Config.LOCK_MINUTES_BEFORE) if start else None
    t["locked"] = bool(lock_at and lock_at <= now)
    # Hatua ya mkeka: wazi (bado unaweza kununuliwa), imefungwa (inasubiri matokeo), au imekwisha
    t["phase"] = ("pending" if t["locked"] else "open") if t["status"] == "open" else t["status"]
    t["closes_in"] = int((lock_at - now).total_seconds()) if lock_at and not t["locked"] else None
    t["counting"] = t["closes_in"] is not None and t["closes_in"] <= Config.COUNTDOWN_MINUTES * 60
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


def create_tip(uid, *, title, league, pick, body, odds, price, starts_at,
               fixture_id=None, market=None, selection=None, bookmaker=None, legs=None):
    """legs: orodha ya mechi (>= 2) kwa mkeka wa mechi nyingi; mkeka na mechi zake vinaandikwa pamoja."""
    n = len(legs) if legs else 1
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO tips (user_id, title, league, pick, body, odds, price, starts_at, "
            "fixture_id, market, selection, bookmaker, legs) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (uid, title, league, pick, body or None, odds, price, starts_at, fixture_id, market, selection,
             bookmaker, n))
        tip_id = cur.fetchone()["id"]
        for lg in (legs or []):
            cur.execute(
                "INSERT INTO tip_legs (tip_id, fixture_id, title, league, market, selection, pick, odds, kickoff) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (tip_id, lg["fixture_id"], lg["title"], lg["league"][:40], lg["market"], lg["selection"],
                 lg["pick"], lg["odds"], lg["kickoff"]))
        return tip_id


def get_legs(tip_id):
    return db.query("SELECT l.*, f.status AS fx_status, f.home_goals, f.away_goals FROM tip_legs l "
                    "LEFT JOIN fixtures f ON f.id = l.fixture_id WHERE l.tip_id = %s ORDER BY l.kickoff, l.id",
                    (tip_id,))


_TIP_RESULT = {"won": "umeshinda", "lost": "umepoteza", "void": "umebatilishwa"}


def set_tip_status(tip_id, status):
    """Hubadilisha matokeo na kuwaarifu wote walionunua mkeka (kwa mkupuo mmoja)."""
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE tips SET status = %s WHERE id = %s AND status <> %s RETURNING title",
                    (status, tip_id, status))
        row = cur.fetchone()
        if row and status in _TIP_RESULT:
            cur.execute(
                "INSERT INTO notifications (user_id, kind, text, url) "
                "SELECT user_id, 'tip', %s, %s FROM tip_purchases WHERE tip_id = %s",
                (f"Mkeka ulionunua {_TIP_RESULT[status]}: {row['title']}"[:200], f"/jamvi/{tip_id}", tip_id),
            )


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
        if start and start - timedelta(minutes=Config.LOCK_MINUTES_BEFORE) <= datetime.now(timezone.utc):
            raise TipError(f"Mkeka umefungwa: unafungwa dakika {Config.LOCK_MINUTES_BEFORE} kabla ya mechi ya kwanza kuanza.")

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
        notify(cur, tip["user_id"], "sale", f"Mkeka wako umenunuliwa: {tip['title']} (+{net} coin)",
               f"/jamvi/{tip_id}")
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


# ===================== Market =====================
class MarketError(Exception):
    """Kosa la sheria za market; ujumbe unaonyeshwa kwa mtumiaji."""


_PRODUCT_SELECT = (
    "SELECT p.*, u.username, u.display_name, "
    "(SELECT url FROM product_images i WHERE i.product_id = p.id ORDER BY i.position, i.id LIMIT 1) AS image "
    "FROM products p JOIN users u ON u.id = p.seller_id"
)


def list_products(*, q=None, category=None, seller_id=None, statuses=("active",), limit=20, offset=0):
    where = ["p.status IN (" + ", ".join(["%s"] * len(statuses)) + ")"]
    params = list(statuses)
    if category:
        where.append("p.category = %s")
        params.append(category)
    if seller_id:
        where.append("p.seller_id = %s")
        params.append(seller_id)
    if q:
        like = "%" + q.lower() + "%"
        where.append("(LOWER(p.title) LIKE %s OR LOWER(COALESCE(p.description, '')) LIKE %s)")
        params += [like, like]
    sql = _PRODUCT_SELECT + " WHERE " + " AND ".join(where) + " ORDER BY p.created_at DESC, p.id DESC LIMIT %s OFFSET %s"
    return db.query(sql, tuple(params) + (limit, offset))


def get_product(product_id):
    p = db.query(_PRODUCT_SELECT + " WHERE p.id = %s", (product_id,), one=True)
    if p:
        p["images"] = [r["url"] for r in db.query(
            "SELECT url FROM product_images WHERE product_id = %s ORDER BY position, id", (product_id,))]
    return p


def create_product(seller_id, *, title, description, category, price, location, contact, image_urls):
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO products (seller_id, title, description, category, price, location, contact) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (seller_id, title, description or None, category, price, location or None, contact or None),
        )
        pid = cur.fetchone()["id"]
        for pos, url in enumerate(image_urls):
            cur.execute("INSERT INTO product_images (product_id, url, position) VALUES (%s, %s, %s)", (pid, url, pos))
    return pid


def set_product_hidden(product_id, seller_id, hide):
    """Inaficha (active -> hidden) au kuonyesha (hidden -> active). Bidhaa iliyoagizwa au kuuzwa haiguswi."""
    src, dst = ("active", "hidden") if hide else ("hidden", "active")
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE products SET status = %s WHERE id = %s AND seller_id = %s AND status = %s",
                    (dst, product_id, seller_id, src))
        return cur.rowcount > 0


def delete_product(product_id, seller_id):
    """Inafuta bidhaa isiyo na agizo lolote. Inarudisha orodha ya URL za picha zilizofutwa, au None."""
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT url FROM product_images WHERE product_id = %s", (product_id,))
        urls = [r["url"] for r in cur.fetchall()]
        cur.execute(
            "DELETE FROM products WHERE id = %s AND seller_id = %s "
            "AND NOT EXISTS (SELECT 1 FROM orders WHERE product_id = %s)",
            (product_id, seller_id, product_id),
        )
        return urls if cur.rowcount > 0 else None


def open_order_for_product(product_id):
    return db.query(
        "SELECT id, buyer_id, seller_id, status FROM orders "
        "WHERE product_id = %s AND status IN ('paid', 'delivered', 'disputed')",
        (product_id,), one=True)


_OPEN = ("paid", "delivered", "disputed")


def create_order(product_id, buyer_id, note, fee_pct):
    """Mnunuzi analipa; coin zinashikiliwa (hazijaenda kwa muuzaji) hadi agizo likamilike au lighairiwe.
    Yote kwa mkupuo mmoja: kosa lolote linarudisha kila kitu nyuma."""
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, seller_id, title, price, status FROM products WHERE id = %s", (product_id,))
        p = cur.fetchone()
        if not p:
            raise MarketError("Bidhaa hii haipo.")
        if p["seller_id"] == buyer_id:
            raise MarketError("Huwezi kuagiza bidhaa yako mwenyewe.")
        if p["status"] != "active":
            raise MarketError("Bidhaa hii haipatikani tena.")
        cur.execute("UPDATE products SET status = 'reserved' WHERE id = %s AND status = 'active' RETURNING id", (product_id,))
        if cur.fetchone() is None:
            raise MarketError("Bidhaa hii imeshaagizwa na mtu mwingine.")
        price = p["price"]
        cur.execute(
            "UPDATE wallets SET balance = balance - %s, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = %s AND balance >= %s RETURNING balance",
            (price, buyer_id, price),
        )
        row = cur.fetchone()
        if row is None:
            raise InsufficientFunds()
        cur.execute(
            "INSERT INTO orders (product_id, buyer_id, seller_id, price, fee, note) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (product_id, buyer_id, p["seller_id"], price, price * fee_pct // 100, note or None),
        )
        oid = cur.fetchone()["id"]
        cur.execute(
            "INSERT INTO transactions (user_id, kind, amount, note) VALUES (%s, 'market', %s, %s)",
            (buyer_id, -price, f"Agizo #{oid}: {p['title']} (inashikiliwa hadi upokee)"),
        )
        notify(cur, p["seller_id"], "order", f"Agizo jipya #{oid}: {p['title']}", f"/market/maagizo/{oid}")
        return {"id": oid, "price": price, "balance": row["balance"]}


def _finish(cur, order_id, new_status, allowed, party_col=None, party_id=None):
    """Hubadilisha hali ya agizo mara moja tu (mshindi mmoja hata maombi mawili yakigongana).
    Inarudisha safu ya agizo, au None kama hali yake haikuruhusu."""
    assert party_col in (None, "buyer_id", "seller_id")
    sql = ("UPDATE orders SET status = %s, closed_at = CURRENT_TIMESTAMP WHERE id = %s AND status IN ("
           + ", ".join(["%s"] * len(allowed)) + ")")
    params = [new_status, order_id, *allowed]
    if party_col:
        sql += f" AND {party_col} = %s"
        params.append(party_id)
    cur.execute(sql + " RETURNING id, product_id, buyer_id, seller_id, price, fee", params)
    return cur.fetchone()


_PAY_TEXT = {
    "buyer": "Mnunuzi amethibitisha kupokea",
    "admin": "Msimamizi ameachilia malipo",
    "auto": "Malipo yameachiliwa kiotomatiki (siku zimepita)",
}
_REFUND_TEXT = {
    "buyer": ("Mnunuzi amefuta agizo", "Umerudishiwa coin zako"),
    "seller": ("", "Muuzaji amefuta agizo, umerudishiwa coin zako"),
    "admin": ("Msimamizi amefuta agizo", "Msimamizi amefuta agizo, umerudishiwa coin zako"),
}


def _pay_seller(cur, o, actor="buyer"):
    net = o["price"] - o["fee"]
    url = f"/market/maagizo/{o['id']}"
    notify(cur, o["seller_id"], "order", f"{_PAY_TEXT[actor]}: umelipwa {net} coin (agizo #{o['id']})", url)
    if actor != "buyer":
        notify(cur, o["buyer_id"], "order", f"Agizo #{o['id']} limekamilika, malipo yameenda kwa muuzaji", url)
    cur.execute("UPDATE wallets SET balance = balance + %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                (net, o["seller_id"]))
    cur.execute("UPDATE products SET status = 'sold' WHERE id = %s", (o["product_id"],))
    cur.execute("INSERT INTO transactions (user_id, kind, amount, note) VALUES (%s, 'market', %s, %s)",
                (o["seller_id"], net, f"Mauzo ya agizo #{o['id']}"))


def _refund_buyer(cur, o, actor="admin"):
    to_seller, to_buyer = _REFUND_TEXT[actor]
    url = f"/market/maagizo/{o['id']}"
    if to_seller:
        notify(cur, o["seller_id"], "order", f"{to_seller} #{o['id']}", url)
    notify(cur, o["buyer_id"], "order", f"{to_buyer} (agizo #{o['id']})" if actor != "buyer" else
           f"Agizo #{o['id']} limefutwa, umerudishiwa coin zako", url)
    cur.execute("UPDATE wallets SET balance = balance + %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                (o["price"], o["buyer_id"]))
    cur.execute("UPDATE products SET status = 'active' WHERE id = %s AND status = 'reserved'", (o["product_id"],))
    cur.execute("INSERT INTO transactions (user_id, kind, amount, note) VALUES (%s, 'market', %s, %s)",
                (o["buyer_id"], o["price"], f"Marejesho ya agizo #{o['id']}"))


_STALE = "Hali ya agizo imebadilika. Onyesha ukurasa upya."


def _complete(order_id, allowed, party_col=None, party_id=None, actor="buyer"):
    with db.get_conn() as conn, conn.cursor() as cur:
        o = _finish(cur, order_id, "completed", allowed, party_col, party_id)
        if o is None:
            raise MarketError(_STALE)
        _pay_seller(cur, o, actor)


def _cancel(order_id, allowed, party_col=None, party_id=None, actor="admin"):
    with db.get_conn() as conn, conn.cursor() as cur:
        o = _finish(cur, order_id, "cancelled", allowed, party_col, party_id)
        if o is None:
            raise MarketError(_STALE)
        _refund_buyer(cur, o, actor)


def confirm_received(order_id, buyer_id):
    _complete(order_id, _OPEN, "buyer_id", buyer_id)


def admin_release(order_id):
    _complete(order_id, _OPEN, actor="admin")


def cancel_by_buyer(order_id, buyer_id):
    _cancel(order_id, ("paid",), "buyer_id", buyer_id, "buyer")


def cancel_by_seller(order_id, seller_id):
    _cancel(order_id, _OPEN, "seller_id", seller_id, "seller")


def admin_refund(order_id):
    _cancel(order_id, _OPEN, actor="admin")


def _simple_transition(order_id, party_col, party_id, src, sql_set, notice=None):
    """notice: (nani, maandishi): nani = "buyer" | "seller" | "both" (wapokeaji + wasimamizi)."""
    assert party_col in ("buyer_id", "seller_id")
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"UPDATE orders SET {sql_set} WHERE id = %s AND {party_col} = %s AND status = %s "
                    "RETURNING id, buyer_id, seller_id",
                    (order_id, party_id, src))
        o = cur.fetchone()
        if o is None:
            raise MarketError(_STALE)
        if notice:
            who, text = notice
            url = f"/market/maagizo/{o['id']}"
            text = f"{text} (agizo #{o['id']})"
            if who == "buyer":
                notify(cur, o["buyer_id"], "order", text, url)
            else:
                notify(cur, o["seller_id"], "order", text, url)
                cur.execute("INSERT INTO notifications (user_id, kind, text, url) "
                            "SELECT id, 'order', %s, %s FROM users WHERE is_admin = TRUE",
                            (text[:200], url))


def mark_delivered(order_id, seller_id):
    _simple_transition(order_id, "seller_id", seller_id, "paid",
                       "status = 'delivered', delivered_at = CURRENT_TIMESTAMP",
                       ("buyer", "Muuzaji amekabidhi bidhaa, thibitisha ukipokea"))


def open_dispute(order_id, buyer_id):
    _simple_transition(order_id, "buyer_id", buyer_id, "delivered", "status = 'disputed'",
                       ("both", "Mnunuzi amefungua pingamizi"))


def release_overdue(days, user_id=None):
    """Huachilia coin kwa muuzaji kwa maagizo yaliyokabidhiwa na mnunuzi hajajibu kwa siku `days`.
    Haina cron: inaendeshwa mtumiaji anapofungua maagizo yake. Inarudisha idadi iliyoachiliwa."""
    sql, params = "SELECT id, delivered_at FROM orders WHERE status = 'delivered'", ()
    if user_id:
        sql += " AND (buyer_id = %s OR seller_id = %s)"
        params = (user_id, user_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    done = 0
    for r in db.query(sql, params):
        when = to_dt(r["delivered_at"])
        if when and when <= cutoff:
            try:
                _complete(r["id"], ("delivered",), actor="auto")
                done += 1
            except MarketError:
                pass  # mwingine ameshalishughulikia
    return done


_ORDER_SELECT = (
    "SELECT o.*, p.title, p.location, p.contact AS product_contact, "
    "b.username AS buyer_username, b.display_name AS buyer_name, "
    "s.username AS seller_username, s.display_name AS seller_name "
    "FROM orders o JOIN products p ON p.id = o.product_id "
    "JOIN users b ON b.id = o.buyer_id JOIN users s ON s.id = o.seller_id"
)


def get_order(order_id):
    return db.query(_ORDER_SELECT + " WHERE o.id = %s", (order_id,), one=True)


def list_orders(uid, role, limit=100):
    col = {"buyer": "o.buyer_id", "seller": "o.seller_id"}[role]
    return db.query(_ORDER_SELECT + f" WHERE {col} = %s ORDER BY o.created_at DESC, o.id DESC LIMIT %s", (uid, limit))


# ===================== Ujumbe na arifa =====================
class ChatError(Exception):
    """Kosa la ujumbe; maandishi yanaonyeshwa kwa mtumiaji."""


def block_state(a, b):
    """by_me: a amemzuia b. by_them: b amemzuia a."""
    rows = db.query(
        "SELECT blocker_id FROM blocks WHERE (blocker_id = %s AND blocked_id = %s) "
        "OR (blocker_id = %s AND blocked_id = %s)", (a, b, b, a))
    ids = {r["blocker_id"] for r in rows}
    return {"by_me": a in ids, "by_them": b in ids}


def block_user(blocker, blocked):
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 AS x FROM blocks WHERE blocker_id = %s AND blocked_id = %s", (blocker, blocked))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO blocks (blocker_id, blocked_id) VALUES (%s, %s)", (blocker, blocked))


def unblock_user(blocker, blocked):
    db.execute("DELETE FROM blocks WHERE blocker_id = %s AND blocked_id = %s", (blocker, blocked))


def send_message(sender, recipient, body):
    """Inatuma ujumbe. Aliyezuiwa anapata kosa la jumla (hafichuliwi kuwa amezuiwa)."""
    st = block_state(sender, recipient)
    if st["by_me"]:
        raise ChatError("Umemzuia mtumiaji huyu. Muondolee kizuizi ili kumtumia ujumbe.")
    if st["by_them"]:
        raise ChatError("Ujumbe haukutumwa. Mtumiaji huyu hapokei ujumbe kwa sasa.")
    rec = db.query("SELECT allow_messages FROM users WHERE id = %s", (recipient,), one=True)
    if rec is not None and not rec["allow_messages"]:
        raise ChatError("Ujumbe haukutumwa. Mtumiaji huyu hapokei ujumbe kwa sasa.")
    row = db.query(
        "INSERT INTO messages (sender_id, recipient_id, body) VALUES (%s, %s, %s) RETURNING id",
        (sender, recipient, body), one=True)
    return row["id"]


def thread(uid, other_id, after_id=None, limit=100):
    """Ujumbe kati ya watu wawili tu. Bila after_id: ujumbe 100 wa mwisho; vinginevyo mpya zaidi ya after_id."""
    pair = ("((sender_id = %s AND recipient_id = %s) OR (sender_id = %s AND recipient_id = %s))")
    p = (uid, other_id, other_id, uid)
    if after_id:
        return db.query(
            f"SELECT id, sender_id, body, read_at, created_at FROM messages WHERE {pair} AND id > %s "
            "ORDER BY id ASC LIMIT %s", p + (after_id, limit))
    rows = db.query(
        f"SELECT id, sender_id, body, read_at, created_at FROM messages WHERE {pair} "
        "ORDER BY id DESC LIMIT %s", p + (limit,))
    return list(reversed(rows))


def mark_thread_read(uid, other_id):
    db.execute("UPDATE messages SET read_at = CURRENT_TIMESTAMP "
               "WHERE recipient_id = %s AND sender_id = %s AND read_at IS NULL", (uid, other_id))


def inbox(uid, limit=50):
    """Mazungumzo yote: mwenzi, ujumbe wa mwisho na idadi ya ambazo hazijasomwa."""
    groups = db.query(
        "SELECT CASE WHEN sender_id = %s THEN recipient_id ELSE sender_id END AS other_id, "
        "MAX(id) AS last_id, "
        "SUM(CASE WHEN recipient_id = %s AND read_at IS NULL THEN 1 ELSE 0 END) AS unread "
        "FROM messages WHERE sender_id = %s OR recipient_id = %s "
        "GROUP BY CASE WHEN sender_id = %s THEN recipient_id ELSE sender_id END "
        "ORDER BY last_id DESC LIMIT %s", (uid, uid, uid, uid, uid, limit))
    if not groups:
        return []
    last = {r["id"]: r for r in db.query(
        "SELECT id, sender_id, body, created_at FROM messages WHERE id IN ("
        + ", ".join(["%s"] * len(groups)) + ")", tuple(g["last_id"] for g in groups))}
    users = {r["id"]: r for r in db.query(
        "SELECT id, username, display_name, avatar_url FROM users WHERE id IN ("
        + ", ".join(["%s"] * len(groups)) + ")", tuple(g["other_id"] for g in groups))}
    out = []
    for g in groups:
        u, m = users.get(g["other_id"]), last.get(g["last_id"])
        if u and m:
            out.append({"user": u, "last": m, "unread": int(g["unread"] or 0), "mine": m["sender_id"] == uid})
    return out


def unread_counts(uid):
    m = db.query("SELECT COUNT(*) AS n FROM messages WHERE recipient_id = %s AND read_at IS NULL", (uid,), one=True)
    n = db.query("SELECT COUNT(*) AS n FROM notifications WHERE user_id = %s AND read_at IS NULL", (uid,), one=True)
    return int(m["n"]), int(n["n"])


def list_notifications(uid, limit=50):
    return db.query("SELECT id, kind, text, url, read_at, created_at FROM notifications "
                    "WHERE user_id = %s ORDER BY id DESC LIMIT %s", (uid, limit))


def mark_notifications_read(uid):
    db.execute("UPDATE notifications SET read_at = CURRENT_TIMESTAMP WHERE user_id = %s AND read_at IS NULL", (uid,))


# ===================== Usimamizi (admin) =====================
class AdminError(Exception):
    """Kosa la hatua ya msimamizi; maandishi yanaonyeshwa."""


def log_admin(cur, admin_id, action, detail=""):
    cur.execute("INSERT INTO admin_log (admin_id, action, detail) VALUES (%s, %s, %s)",
                (admin_id, action, detail[:300]))


def admin_stats():
    def n(sql):
        return int(db.query(sql, one=True)["n"])
    return {
        "users": n("SELECT COUNT(*) AS n FROM users"),
        "banned": n("SELECT COUNT(*) AS n FROM users WHERE is_banned = TRUE"),
        "tips": n("SELECT COUNT(*) AS n FROM tips"),
        "products": n("SELECT COUNT(*) AS n FROM products"),
        "orders_open": n("SELECT COUNT(*) AS n FROM orders WHERE status IN ('paid','delivered','disputed')"),
        "disputed": n("SELECT COUNT(*) AS n FROM orders WHERE status = 'disputed'"),
        "reports_open": n("SELECT COUNT(*) AS n FROM reports WHERE status = 'open'"),
        "coins": int(db.query("SELECT COALESCE(SUM(balance), 0) AS n FROM wallets", one=True)["n"]),
        "held": int(db.query("SELECT COALESCE(SUM(price), 0) AS n FROM orders "
                             "WHERE status IN ('paid','delivered','disputed')", one=True)["n"]),
    }


def admin_users(q=None, limit=50, offset=0):
    sql = ("SELECT u.id, u.username, u.display_name, u.email, u.phone, u.is_admin, u.is_banned, "
           "u.is_verified, u.created_at, COALESCE(w.balance, 0) AS balance "
           "FROM users u LEFT JOIN wallets w ON w.user_id = u.id")
    params = []
    if q:
        like = f"%{q.lower()}%"
        sql += (" WHERE LOWER(u.username) LIKE %s OR LOWER(u.display_name) LIKE %s "
                "OR LOWER(COALESCE(u.email, '')) LIKE %s OR COALESCE(u.phone, '') LIKE %s")
        params += [like, like, like, f"%{q}%"]
    sql += " ORDER BY u.id DESC LIMIT %s OFFSET %s"
    return db.query(sql, tuple(params + [limit, offset]))


def admin_set_banned(admin_id, target_id, banned):
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT username, is_admin FROM users WHERE id = %s", (target_id,))
        u = cur.fetchone()
        if not u:
            raise AdminError("Mtumiaji hayupo.")
        if target_id == admin_id:
            raise AdminError("Huwezi kujisimamisha mwenyewe.")
        if u["is_admin"]:
            raise AdminError("Huwezi kumsimamisha msimamizi mwingine.")
        cur.execute("UPDATE users SET is_banned = %s WHERE id = %s", (bool(banned), target_id))
        log_admin(cur, admin_id, "ban" if banned else "unban", f"@{u['username']}")
        return u["username"]


def admin_set_verified(admin_id, target_id, verified):
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET is_verified = %s WHERE id = %s RETURNING username", (bool(verified), target_id))
        u = cur.fetchone()
        if not u:
            raise AdminError("Mtumiaji hayupo.")
        log_admin(cur, admin_id, "verify" if verified else "unverify", f"@{u['username']}")


def admin_tips(limit=100):
    return db.query(
        "SELECT t.id, t.title, t.status, t.price, t.created_at, u.username, "
        "(SELECT COUNT(*) FROM tip_purchases p WHERE p.tip_id = t.id) AS buyers "
        "FROM tips t JOIN users u ON u.id = t.user_id ORDER BY t.id DESC LIMIT %s", (limit,))


def _void_tip(cur, tip_id):
    """Hubatilisha mkeka na kurudisha bei kamili kwa kila aliyenunua (ndani ya muamala uliopo).
    Muuzaji anakatwa alichopokea (bei toa ada) kadiri salio lake linavyoruhusu; upungufu unabebwa na jukwaa.
    Inafanya kazi mara moja tu kwa kila mkeka. Inarudisha idadi ya wanunuzi."""
    fee_pct = Config.TIP_FEE_PCT
    cur.execute("UPDATE tips SET status = 'void' WHERE id = %s AND status <> 'void' "
                "RETURNING user_id, title, price", (tip_id,))
    t = cur.fetchone()
    if not t:
        raise AdminError("Mkeka haupo au umeshabatilishwa.")
    cur.execute("SELECT user_id FROM tip_purchases WHERE tip_id = %s", (tip_id,))
    buyers = [r["user_id"] for r in cur.fetchall()]
    price, seller = t["price"], t["user_id"]
    net = price - price * fee_pct // 100
    for b in buyers:
        cur.execute("UPDATE wallets SET balance = balance + %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                    (price, b))
        cur.execute("INSERT INTO transactions (user_id, kind, amount, note) VALUES (%s, 'tip_purchase', %s, %s)",
                    (b, price, f"Marejesho ya mkeka uliobatilishwa: {t['title']}"))
        notify(cur, b, "tip", f"Mkeka ulionunua umebatilishwa, umerudishiwa coin {price}: {t['title']}", f"/jamvi/{tip_id}")
        cur.execute("SELECT balance FROM wallets WHERE user_id = %s", (seller,))
        bal = cur.fetchone()["balance"]
        take = min(net, bal)
        if take > 0:
            cur.execute("UPDATE wallets SET balance = balance - %s, updated_at = CURRENT_TIMESTAMP "
                        "WHERE user_id = %s", (take, seller))
            cur.execute("INSERT INTO transactions (user_id, kind, amount, note) VALUES (%s, 'tip_sale', %s, %s)",
                        (seller, -take, f"Mauzo ya mkeka uliobatilishwa yamerudishwa: {t['title']}"))
    if buyers:
        notify(cur, seller, "tip", f"Mkeka wako umebatilishwa: {t['title']}", f"/jamvi/{tip_id}")
    return len(buyers)


def admin_void_tip(admin_id, tip_id):
    with db.get_conn() as conn, conn.cursor() as cur:
        n = _void_tip(cur, tip_id)
        log_admin(cur, admin_id, "void_tip", f"#{tip_id} wanunuzi {n}")
        return n


def void_tip_system(tip_id):
    """Mchezo umeahirishwa au kufutwa: mfumo unabatilisha na kurudisha coin."""
    with db.get_conn() as conn, conn.cursor() as cur:
        return _void_tip(cur, tip_id)


def admin_delete_tip(admin_id, tip_id):
    """Kufuta mkeka kabisa kunaruhusiwa kama hakuna aliyeununua (vinginevyo tumia 'batilisha')."""
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM tips WHERE id = %s AND NOT EXISTS "
                    "(SELECT 1 FROM tip_purchases WHERE tip_id = %s)", (tip_id, tip_id))
        if cur.rowcount == 0:
            raise AdminError("Mkeka una wanunuzi au haupo. Tumia 'Batilisha na rudisha coin'.")
        log_admin(cur, admin_id, "delete_tip", f"#{tip_id}")


def admin_products(limit=100):
    return db.query(
        "SELECT p.id, p.title, p.status, p.price, u.username FROM products p "
        "JOIN users u ON u.id = p.seller_id ORDER BY p.id DESC LIMIT %s", (limit,))


def admin_hide_product(admin_id, product_id, hide=True):
    with db.get_conn() as conn, conn.cursor() as cur:
        if hide:
            cur.execute("UPDATE products SET status = 'hidden' WHERE id = %s AND status = 'active' RETURNING id", (product_id,))
        else:
            cur.execute("UPDATE products SET status = 'active' WHERE id = %s AND status = 'hidden' RETURNING id", (product_id,))
        if cur.fetchone() is None:
            raise AdminError("Hali ya bidhaa hairuhusu hatua hii (bidhaa yenye agizo haiguswi hapa).")
        log_admin(cur, admin_id, "hide_product" if hide else "show_product", f"#{product_id}")


def admin_orders(status=None, limit=100):
    sql = _ORDER_SELECT
    params = []
    if status:
        sql += " WHERE o.status = %s"
        params.append(status)
    return db.query(sql + " ORDER BY o.id DESC LIMIT %s", tuple(params + [limit]))


def log_order_action(admin_id, action, order_id):
    with db.get_conn() as conn, conn.cursor() as cur:
        log_admin(cur, admin_id, action, f"#{order_id}")


def create_report(reporter_id, target_type, target_id, reason):
    """Inarudisha True ikiwa ripoti mpya imewekwa, False ikiwa ya awali bado iko wazi."""
    if target_type not in ("user", "tip", "product"):
        raise AdminError("Aina ya ripoti si sahihi.")
    table = {"user": "users", "tip": "tips", "product": "products"}[target_type]
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT id FROM {table} WHERE id = %s", (target_id,))
        if cur.fetchone() is None:
            raise AdminError("Unachoripoti hakipo.")
        if target_type == "user" and target_id == reporter_id:
            raise AdminError("Huwezi kujiripoti mwenyewe.")
        cur.execute("SELECT 1 AS x FROM reports WHERE reporter_id = %s AND target_type = %s "
                    "AND target_id = %s AND status = 'open'", (reporter_id, target_type, target_id))
        if cur.fetchone():
            return False
        cur.execute("INSERT INTO reports (reporter_id, target_type, target_id, reason) VALUES (%s, %s, %s, %s)",
                    (reporter_id, target_type, target_id, reason))
        cur.execute("INSERT INTO notifications (user_id, kind, text, url) "
                    "SELECT id, 'report', %s, %s FROM users WHERE is_admin = TRUE",
                    ("Ripoti mpya imewekwa", "/admin/ripoti"))
        return True


def admin_reports(status="open", limit=100):
    return db.query(
        "SELECT r.*, u.username AS reporter FROM reports r JOIN users u ON u.id = r.reporter_id "
        "WHERE r.status = %s ORDER BY r.id DESC LIMIT %s", (status, limit))


def admin_resolve_report(admin_id, report_id, status):
    assert status in ("resolved", "dismissed")
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE reports SET status = %s, handled_by = %s, handled_at = CURRENT_TIMESTAMP "
                    "WHERE id = %s AND status = 'open' RETURNING id", (status, admin_id, report_id))
        if cur.fetchone() is None:
            raise AdminError("Ripoti imeshashughulikiwa.")
        log_admin(cur, admin_id, f"report_{status}", f"#{report_id}")


def admin_log_list(limit=100):
    return db.query("SELECT l.*, u.username FROM admin_log l JOIN users u ON u.id = l.admin_id "
                    "ORDER BY l.id DESC LIMIT %s", (limit,))


def make_admin(user_id):
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET is_admin = TRUE WHERE id = %s AND is_admin = FALSE", (user_id,))
        if cur.rowcount:
            log_admin(cur, user_id, "env_admin", "alipandishwa kupitia environment")


def set_password(user_id, password_hash):
    db.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))


def admin_waiting_tips(limit=30):
    """Mikeka ya mechi halisi iliyoanza lakini bado haijahukumiwa."""
    return db.query(
        "SELECT t.id, t.title, t.market, t.selection, f.status, f.kickoff FROM tips t "
        "JOIN fixtures f ON f.id = t.fixture_id WHERE t.status = 'open' AND t.fixture_id IS NOT NULL "
        "ORDER BY f.kickoff ASC LIMIT %s", (limit,))


# ---------- Matangazo (banners) ----------
BANNER_THEMES = ("green", "blue", "amber", "purple", "dark")
BANNER_LINKS = [  # chaguo za haraka kwa admin
    ("/jamvi", "Jamvi la mikeka"), ("/market", "Market"), ("/pochi", "Pochi"),
    ("/jamvi/weka", "Weka mkeka"), ("/market/weka", "Weka bidhaa"),
    ("/jamvi/viwango", "Viwango vya watabiri"), ("/jisajili", "Usajili"),
]
MAX_BANNERS = 10


def clean_banner_link(raw):
    """Kiungo cha ndani (/...) au https://... tu. Vingine vinakataliwa."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("/") and not raw.startswith("//") and "\\" not in raw:
        return raw[:300]
    if raw.lower().startswith("https://") and len(raw) > 10 and " " not in raw:
        return raw[:300]
    raise AdminError("Kiungo lazima kianze na / (ndani ya app) au https:// (nje).")


def _banner_alive(b):
    e = b.get("ends_at")
    if not e:
        return True
    if isinstance(e, str):
        try:
            e = datetime.fromisoformat(e)
        except ValueError:
            return True
    if e.tzinfo is None:
        e = e.replace(tzinfo=timezone.utc)
    return e > datetime.now(timezone.utc)


def banners_active():
    rows = db.query("SELECT * FROM banners WHERE active = TRUE ORDER BY position, id DESC")
    return [b for b in rows if _banner_alive(b)][:MAX_BANNERS]


def admin_banners():
    return db.query("SELECT * FROM banners ORDER BY active DESC, position, id DESC")


def get_banner(bid):
    return db.query("SELECT * FROM banners WHERE id = %s", (bid,), one=True)


def banner_save(admin_id, bid, title, subtitle, theme, link, cta, position, ends_at, image_url=None, drop_image=False):
    title, subtitle, cta = (title or "").strip(), (subtitle or "").strip(), (cta or "").strip()
    if not 2 <= len(title) <= 60:
        raise AdminError("Kichwa cha tangazo kiwe herufi 2 hadi 60.")
    if len(subtitle) > 120:
        raise AdminError("Maelezo mafupi yasizidi herufi 120.")
    if len(cta) > 20:
        raise AdminError("Maandishi ya kitufe yasizidi herufi 20.")
    if theme not in BANNER_THEMES:
        theme = "green"
    link = clean_banner_link(link)
    try:
        position = max(0, min(99, int(position or 0)))
    except (TypeError, ValueError):
        position = 0
    with db.get_conn() as conn, conn.cursor() as cur:
        if bid is None:
            cur.execute("SELECT COUNT(*) AS n FROM banners")
            if int(cur.fetchone()["n"]) >= 30:
                raise AdminError("Matangazo ni mengi mno. Futa ya zamani kwanza.")
            cur.execute("INSERT INTO banners (title, subtitle, image_url, theme, link, cta, position, ends_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (title, subtitle, image_url, theme, link, cta, position, ends_at))
            log_admin(cur, admin_id, "banner_add", title)
        else:
            cur.execute("SELECT image_url FROM banners WHERE id = %s", (bid,))
            old = cur.fetchone()
            if old is None:
                raise AdminError("Tangazo halipo.")
            img = image_url or (None if drop_image else old["image_url"])
            cur.execute("UPDATE banners SET title=%s, subtitle=%s, image_url=%s, theme=%s, link=%s, cta=%s, "
                        "position=%s, ends_at=%s WHERE id=%s",
                        (title, subtitle, img, theme, link, cta, position, ends_at, bid))
            log_admin(cur, admin_id, "banner_edit", f"#{bid} {title}")


def banner_toggle(admin_id, bid):
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT active FROM banners WHERE id = %s", (bid,))
        b = cur.fetchone()
        if b is None:
            raise AdminError("Tangazo halipo.")
        cur.execute("UPDATE banners SET active = %s WHERE id = %s", (not b["active"], bid))
        log_admin(cur, admin_id, "banner_on" if not b["active"] else "banner_off", f"#{bid}")


def banner_delete(admin_id, bid):
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT image_url FROM banners WHERE id = %s", (bid,))
        b = cur.fetchone()
        if b is None:
            raise AdminError("Tangazo halipo.")
        cur.execute("DELETE FROM banners WHERE id = %s", (bid,))
        log_admin(cur, admin_id, "banner_delete", f"#{bid}")
        return b["image_url"]


def banner_click(bid):
    """Huongeza hesabu na kurudisha kiungo (au None)."""
    b = get_banner(bid)
    if b is None or not b["active"] or not b["link"]:
        return None
    db.execute("UPDATE banners SET clicks = clicks + 1 WHERE id = %s", (bid,))
    return b["link"]
