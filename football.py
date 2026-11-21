"""Mechi halisi, odds za kampuni za kubashiri na matokeo, kutoka API-Football (v3).

Maombi ni machache kwa makusudi (mpango wa bure ni maombi 100 kwa siku):
- mechi za siku chache zijazo: ombi moja kwa siku, kila saa FIXTURE_SYNC_HOURS
- odds: ombi moja kwa mechi, zinahifadhiwa dakika ODDS_CACHE_MINUTES
- matokeo: ombi moja kwa mechi hadi 20, mara moja kila dakika 10 kwa kiwango cha juu
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import db
from config import Config

BASE = "https://v3.football.api-sports.io"
FINISHED = {"FT", "AET", "PEN"}
VOID = {"CANC", "ABD", "AWD", "WO"}
MIN_LEFT = 3  # maombi yakibaki chini ya haya, tunaacha kupiga simu (isipokuwa kwa hukumu)


class FootballError(Exception):
    """Kosa la huduma ya mechi; maandishi yanaweza kuonyeshwa kwa mtumiaji."""


def configured():
    return bool(Config.APIFOOTBALL_KEY)


# ---------------- thamani ndogo za mfumo ----------------
def kv_get(key):
    row = db.query("SELECT value, updated_at FROM kv WHERE key = %s", (key,), one=True)
    return row


def kv_set(key, value):
    db.execute(
        "INSERT INTO kv (key, value, updated_at) VALUES (%s, %s, CURRENT_TIMESTAMP) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP",
        (key, str(value)))


def _age_minutes(key):
    """Dakika zilizopita tangu thamani iwekwe; None kama haipo."""
    import models
    row = kv_get(key)
    if not row:
        return None
    return (datetime.now(timezone.utc) - models.to_dt(row["updated_at"])).total_seconds() / 60


def requests_left():
    row = kv_get("fb_remaining")
    return int(row["value"]) if row and str(row["value"]).lstrip("-").isdigit() else None


# ---------------- mawasiliano ----------------
def _http_get(path, params):
    """Ombi moja la GET. Inarudisha (json, maombi_yaliyobaki). Inabadilishwa kwenye majaribio."""
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"x-apisports-key": Config.APIFOOTBALL_KEY,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            remaining = r.headers.get("x-ratelimit-requests-remaining")
            return json.loads(r.read().decode("utf-8")), remaining
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise FootballError("Kikomo cha maombi cha leo kimeisha. Jaribu tena kesho.")
        raise FootballError(f"Huduma ya mechi imejibu kwa hitilafu ({e.code}).")
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise FootballError("Huduma ya mechi haipatikani kwa sasa. Jaribu tena baadaye.")


def _get(path, params=None, force=False):
    if not configured():
        raise FootballError("Huduma ya mechi haijawashwa (APIFOOTBALL_KEY haijawekwa).")
    left = requests_left()
    if not force and left is not None and left <= MIN_LEFT:
        raise FootballError("Maombi ya leo yamekaribia kuisha. Jaribu tena kesho.")
    body, remaining = _http_get(path, params or {})
    if remaining is not None and str(remaining).isdigit():
        kv_set("fb_remaining", remaining)
    errors = body.get("errors") if isinstance(body, dict) else None
    if errors:
        text = "; ".join(f"{k}: {v}" for k, v in errors.items()) if isinstance(errors, dict) else str(errors)
        raise FootballError(f"Huduma ya mechi imekataa ombi ({text[:120]}).")
    return body.get("response", []) if isinstance(body, dict) else []


# ---------------- mechi ----------------
def _upsert_fixture(item):
    fx, lg, tm, sc = item["fixture"], item["league"], item["teams"], item.get("score") or {}
    ft = sc.get("fulltime") or {}
    goals = item.get("goals") or {}
    hg = ft.get("home") if ft.get("home") is not None else goals.get("home")
    ag = ft.get("away") if ft.get("away") is not None else goals.get("away")
    kickoff = datetime.fromtimestamp(int(fx["timestamp"]), timezone.utc).isoformat()
    status = (fx.get("status") or {}).get("short") or "NS"
    db.execute(
        "INSERT INTO fixtures (id, league_id, league_name, country, home, away, home_logo, away_logo, "
        "kickoff, status, home_goals, away_goals, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP) "
        "ON CONFLICT (id) DO UPDATE SET league_name = EXCLUDED.league_name, home = EXCLUDED.home, "
        "away = EXCLUDED.away, kickoff = EXCLUDED.kickoff, status = EXCLUDED.status, "
        "home_goals = EXCLUDED.home_goals, away_goals = EXCLUDED.away_goals, updated_at = CURRENT_TIMESTAMP",
        (fx["id"], lg["id"], lg.get("name") or "", lg.get("country") or "", tm["home"]["name"], tm["away"]["name"],
         tm["home"].get("logo"), tm["away"].get("logo"), kickoff, status, hg, ag))


def sync_fixtures(days=None, force=False):
    """Inachukua mechi za siku chache zijazo (ligi zilizochaguliwa tu). Inarudisha idadi ya mechi."""
    days = days or Config.FIXTURE_DAYS_AHEAD
    n = 0
    today = datetime.now(timezone.utc).date()
    note = ""
    for i in range(days):
        day = (today + timedelta(days=i)).isoformat()
        try:
            items = _get("/fixtures", {"date": day, "timezone": "Africa/Dar_es_Salaam"}, force=force)
        except FootballError as e:
            if i == 0:
                raise  # siku ya kwanza imeshindwa: ni kosa halisi
            # Siku za mbele zimekataliwa (mfano mpango wa bure unaruhusu jana hadi kesho tu): tunaendelea na tulizopata
            note = str(e)
            break
        for item in items:
            if item["league"]["id"] in Config.FOOTBALL_LEAGUES:
                _upsert_fixture(item)
                n += 1
    kv_set("fixtures_synced", n)
    kv_set("fixtures_note", note or "-")
    return n


def ensure_fixtures():
    """Husasisha mechi ikiwa za zamani. Inarudisha ujumbe wa kosa au None."""
    if not configured():
        return None
    age = _age_minutes("fixtures_synced")
    if age is not None and age < Config.FIXTURE_SYNC_HOURS * 60:
        return None
    try:
        sync_fixtures()
    except FootballError as e:
        kv_set("fixtures_synced", 0)  # usijaribu tena kila ombi; jaribu tena baada ya muda
        return str(e)
    return None


def list_fixtures(q=None, limit=80):
    """Mechi ambazo hazijaanza (angalau dakika 5 mbele), zilizo karibu zaidi kwanza."""
    import models
    cutoff = datetime.now(timezone.utc) + timedelta(minutes=5)
    rows = db.query("SELECT * FROM fixtures WHERE status = 'NS' ORDER BY kickoff ASC LIMIT 600")
    out = []
    needle = (q or "").strip().lower()
    for r in rows:
        k = models.to_dt(r["kickoff"])
        if k <= cutoff:
            continue
        if needle and needle not in f"{r['home']} {r['away']} {r['league_name']} {r['country']}".lower():
            continue
        r = dict(r)
        r["kickoff"] = k
        out.append(r)
        if len(out) >= limit:
            break
    return out


def get_fixture(fixture_id):
    import models
    r = db.query("SELECT * FROM fixtures WHERE id = %s", (fixture_id,), one=True)
    if not r:
        return None
    r = dict(r)
    r["kickoff"] = models.to_dt(r["kickoff"])
    return r


# ---------------- odds ----------------
MARKET_TITLES = {
    "h2h": "Matokeo ya mchezo (dakika 90)",
    "dc": "Nafasi mbili",
    "btts": "Timu zote kufunga",
    "ou": "Jumla ya magoli",
}
_OU_LINES = {"0.5", "1.5", "2.5", "3.5", "4.5"}


def _map(bet_name, value):
    """(jina la soko la API, thamani) -> (market, selection) yetu, au None kama hatuitumii."""
    v = (value or "").strip()
    if bet_name == "Match Winner":
        return ("h2h", {"Home": "home", "Draw": "draw", "Away": "away"}[v]) if v in ("Home", "Draw", "Away") else None
    if bet_name == "Double Chance":
        m = {"Home/Draw": "1x", "Home/Away": "12", "Draw/Away": "x2"}
        return ("dc", m[v]) if v in m else None
    if bet_name == "Both Teams Score":
        return ("btts", v.lower()) if v in ("Yes", "No") else None
    if bet_name == "Goals Over/Under":
        parts = v.split(" ")
        if len(parts) == 2 and parts[0] in ("Over", "Under") and parts[1] in _OU_LINES:
            return ("ou", f"{parts[0].lower()}_{parts[1]}")
    return None


def _normalize_odds(response):
    """Orodha ya [market, selection, bookmaker_id, bookmaker_name, odd]."""
    rows = []
    for item in response:
        for bk in item.get("bookmakers", []):
            for bet in bk.get("bets", []):
                for val in bet.get("values", []):
                    key = _map(bet.get("name"), val.get("value"))
                    if not key:
                        continue
                    try:
                        odd = float(val.get("odd"))
                    except (TypeError, ValueError):
                        continue
                    if 1.01 <= odd <= 1000:
                        rows.append([key[0], key[1], int(bk["id"]), bk["name"], odd])
    return rows


def get_odds(fixture_id, force=False):
    """Odds za mechi moja (zimehifadhiwa dakika chache). Inarudisha orodha ya safu."""
    import models
    row = db.query("SELECT data, fetched_at FROM odds_cache WHERE fixture_id = %s", (fixture_id,), one=True)
    if row and not force:
        age = (datetime.now(timezone.utc) - models.to_dt(row["fetched_at"])).total_seconds() / 60
        if age < Config.ODDS_CACHE_MINUTES:
            return json.loads(row["data"])
    try:
        rows = _normalize_odds(_get("/odds", {"fixture": fixture_id}))
    except FootballError:
        if row:  # bora odds za zamani kidogo kuliko kutokuwa nazo; lakini si za zaidi ya saa 3
            age = (datetime.now(timezone.utc) - models.to_dt(row["fetched_at"])).total_seconds() / 60
            if age < 180:
                return json.loads(row["data"])
        raise
    db.execute(
        "INSERT INTO odds_cache (fixture_id, data, fetched_at) VALUES (%s, %s, CURRENT_TIMESTAMP) "
        "ON CONFLICT (fixture_id) DO UPDATE SET data = EXCLUDED.data, fetched_at = CURRENT_TIMESTAMP",
        (fixture_id, json.dumps(rows)))
    return rows


def label(market, selection, home, away):
    """Maelezo ya mkeka kwa Kiswahili."""
    if market == "h2h":
        return {"home": f"{home} kushinda", "draw": "Sare", "away": f"{away} kushinda"}.get(selection)
    if market == "dc":
        return {"1x": f"{home} kushinda au sare", "12": "Hakuna sare (mmoja ashinde)",
                "x2": f"{away} kushinda au sare"}.get(selection)
    if market == "btts":
        return {"yes": "Timu zote zifunge", "no": "Timu zote zisifunge (angalau moja haifungi)"}.get(selection)
    if market == "ou":
        side, line = selection.split("_")
        return f"{'Zaidi' if side == 'over' else 'Chini'} ya magoli {line}"
    return None


def options(rows, home, away):
    """Chaguo kwa kila soko, kila moja na odds bora na idadi ya kampuni."""
    best, count = {}, {}
    for m, s, _bid, _bn, odd in rows:
        best[(m, s)] = max(best.get((m, s), 0), odd)
        count[(m, s)] = count.get((m, s), 0) + 1
    out = []
    for m in ("h2h", "dc", "btts", "ou"):
        opts = []
        order = {"h2h": ["home", "draw", "away"], "dc": ["1x", "12", "x2"], "btts": ["yes", "no"]}.get(m)
        for (mm, s), b in sorted(best.items(), key=lambda kv: (order.index(kv[0][1]) if order and kv[0][1] in order else 0, kv[0][1])):
            if mm == m:
                opts.append({"selection": s, "key": f"{m}:{s}", "label": label(m, s, home, away),
                             "best": b, "n": count[(m, s)]})
        if m == "ou":
            opts.sort(key=lambda o: (float(o["selection"].split("_")[1]), o["selection"]))
        if opts:
            out.append({"market": m, "title": MARKET_TITLES[m], "options": opts})
    return out


def bookmakers_for(rows, market, selection):
    """Kampuni zenye chaguo hili: zilizopendelezwa kwanza, kisha odds kubwa kwanza."""
    feat = Config.FEATURED_BOOKMAKERS

    def rank(name):
        n = name.lower()
        return next((i for i, f in enumerate(feat) if f in n), len(feat))

    items = [{"id": bid, "name": bn, "odd": odd} for m, s, bid, bn, odd in rows if m == market and s == selection]
    return sorted(items, key=lambda x: (rank(x["name"]), -x["odd"], x["name"]))


# ---------------- matokeo ----------------
def evaluate(market, selection, hg, ag):
    """'won' au 'lost' kwa mkeka kulingana na magoli ya dakika 90."""
    if market == "h2h":
        res = "home" if hg > ag else ("away" if ag > hg else "draw")
        return "won" if selection == res else "lost"
    if market == "dc":
        ok = {"1x": hg >= ag, "12": hg != ag, "x2": ag >= hg}[selection]
        return "won" if ok else "lost"
    if market == "btts":
        both = hg > 0 and ag > 0
        return "won" if (selection == "yes") == both else "lost"
    if market == "ou":
        side, line = selection.split("_")
        over = (hg + ag) > float(line)
        return "won" if (side == "over") == over else "lost"
    raise ValueError(f"soko lisilojulikana: {market}")


def settle_due(force=False):
    """Inahukumu mikeka ya mechi zilizokwisha. Inarudisha idadi iliyohukumiwa."""
    import models
    if not configured():
        return 0
    if not force:
        age = _age_minutes("settle_ran")
        if age is not None and age < 10:
            return 0
    kv_set("settle_ran", 1)
    now = datetime.now(timezone.utc)
    return _settle_singles(now) + _settle_slips(now)


def _settle_singles(now):
    import models
    tips = db.query(
        "SELECT t.id, t.user_id, t.title, t.fixture_id, t.market, t.selection, f.kickoff, f.status, "
        "f.home_goals, f.away_goals FROM tips t JOIN fixtures f ON f.id = t.fixture_id "
        "WHERE t.status = 'open' AND t.fixture_id IS NOT NULL")
    due = [t for t in tips if models.to_dt(t["kickoff"]) <= now - timedelta(minutes=105)]
    if not due:
        return 0
    ids = sorted({t["fixture_id"] for t in due if t["status"] not in FINISHED | VOID})[:20]
    if ids:
        try:
            for item in _get("/fixtures", {"ids": "-".join(str(i) for i in ids)}, force=True):
                _upsert_fixture(item)
        except FootballError:
            pass  # tutatumia tulichonacho; jaribu tena baadaye
        tips = db.query(
            "SELECT t.id, t.user_id, t.title, t.fixture_id, t.market, t.selection, f.kickoff, f.status, "
            "f.home_goals, f.away_goals FROM tips t JOIN fixtures f ON f.id = t.fixture_id "
            "WHERE t.status = 'open' AND t.fixture_id IS NOT NULL")
        due = [t for t in tips if models.to_dt(t["kickoff"]) <= now - timedelta(minutes=105)]
    done = 0
    for t in due:
        age_days = (now - models.to_dt(t["kickoff"])).total_seconds() / 86400
        st = t["status"]
        result = None
        if st in FINISHED and t["home_goals"] is not None and t["away_goals"] is not None:
            result = evaluate(t["market"], t["selection"], int(t["home_goals"]), int(t["away_goals"]))
        elif st in VOID or (st == "PST" and age_days > 5) or age_days > 7:
            result = "void"
        if not result:
            continue
        try:
            if result == "void":
                models.void_tip_system(t["id"])
            else:
                models.set_tip_status(t["id"], result)
                models.notify_safe(t["user_id"], "tip",
                                   f"Mkeka wako umehukumiwa ({'umeshinda' if result == 'won' else 'umepoteza'}): {t['title']}",
                                   f"/jamvi/{t['id']}")
            done += 1
        except Exception:
            continue
    return done


def maybe_settle():
    """Inaitwa kurasa za mikeka zinapofunguliwa; haivurugi ukurasa ikishindwa."""
    try:
        return settle_due()
    except Exception:
        return 0


def run_cron():
    """Kazi ya kila siku: mechi mpya na hukumu."""
    if not configured():
        return {"fixtures": 0, "settled": 0}
    try:
        n = sync_fixtures(force=True)
    except FootballError:
        n = 0
    return {"fixtures": n, "settled": settle_due(force=True)}


# ---------------- zana za msimamizi ----------------
def search_leagues(q):
    out = []
    for item in _get("/leagues", {"search": q}):
        lg, c = item.get("league", {}), item.get("country", {})
        out.append({"id": lg.get("id"), "name": lg.get("name"), "type": lg.get("type"), "country": c.get("name")})
    return out[:40]


def _leg_result(status, hg, ag, market, selection, kickoff, now):
    """'won' | 'lost' | 'void' au None (bado). Sheria ileile kwa mkeka wa mechi moja na wa mechi nyingi."""
    import models
    age_days = (now - models.to_dt(kickoff)).total_seconds() / 86400
    if status in FINISHED and hg is not None and ag is not None:
        return evaluate(market, selection, int(hg), int(ag))
    if status in VOID or (status == "PST" and age_days > 5) or age_days > 7:
        return "void"
    return None


_SLIP_SQL = ("SELECT l.id AS leg_id, l.tip_id, l.fixture_id, l.market, l.selection, l.odds, l.kickoff, l.result, "
             "f.status, f.home_goals, f.away_goals, t.user_id, t.title AS tip_title "
             "FROM tip_legs l JOIN tips t ON t.id = l.tip_id LEFT JOIN fixtures f ON f.id = l.fixture_id "
             "WHERE t.status = 'open' AND t.legs > 1")


def _settle_slips(now):
    """Mkeka wa mechi nyingi: ukipoteza mechi moja umepoteza; zote zikishinda umeshinda.
    Mechi iliyobatilishwa huhesabiwa kama odds 1 (haiathiri); zote zikibatilishwa mkeka unabatilishwa."""
    import models
    rows = db.query(_SLIP_SQL)
    if not rows:
        return 0
    cutoff = now - timedelta(minutes=105)
    need = sorted({r["fixture_id"] for r in rows if r["result"] is None and (r["status"] or "NS") not in FINISHED | VOID
                   and models.to_dt(r["kickoff"]) <= cutoff})[:20]
    if need:
        try:
            for item in _get("/fixtures", {"ids": "-".join(str(i) for i in need)}, force=True):
                _upsert_fixture(item)
        except FootballError:
            pass
        rows = db.query(_SLIP_SQL)
    for r in rows:
        if r["result"] is not None or models.to_dt(r["kickoff"]) > cutoff:
            continue
        res = _leg_result(r["status"], r["home_goals"], r["away_goals"], r["market"], r["selection"], r["kickoff"], now)
        if res:
            db.execute("UPDATE tip_legs SET result = %s WHERE id = %s AND result IS NULL", (res, r["leg_id"]))
            r["result"] = res
    done = 0
    by_tip = {}
    for r in rows:
        by_tip.setdefault(r["tip_id"], []).append(r)
    for tip_id, legs in by_tip.items():
        results = [l["result"] for l in legs]
        try:
            if "lost" in results:
                models.set_tip_status(tip_id, "lost")
                final = "lost"
            elif None in results:
                continue
            elif all(x == "void" for x in results):
                models.void_tip_system(tip_id)
                done += 1
                continue
            else:
                odds = 1.0
                for l in legs:
                    if l["result"] == "won":
                        odds *= float(l["odds"])
                db.execute("UPDATE tips SET odds = %s WHERE id = %s", (round(min(odds, 1000), 2), tip_id))
                models.set_tip_status(tip_id, "won")
                final = "won"
            models.notify_safe(legs[0]["user_id"], "tip",
                               f"Mkeka wako umehukumiwa ({'umeshinda' if final == 'won' else 'umepoteza'}): {legs[0]['tip_title']}",
                               f"/jamvi/{tip_id}")
            done += 1
        except Exception:
            continue
    return done
